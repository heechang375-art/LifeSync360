import os
import functools

import boto3
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-dev-secret-32bytes-lifesync!!')  # TODO: 운영 배포 시 env var로 교체

USE_MOCK        = os.environ.get('USE_MOCK', 'true').lower() == 'true'
ADMIN_USER      = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS      = os.environ.get('ADMIN_PASSWORD', 'admin1234')  # TODO: 운영 배포 시 env var로 교체
DYNAMO_TABLE    = os.environ.get('DYNAMO_TABLE', 'lifesync-scores')
AWS_REGION      = os.environ.get('AWS_REGION', 'ap-northeast-2')
PRIVATE_API_URL = os.environ.get('PRIVATE_API_URL', '')

GRADES = ['PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'BASIC']
CONSENT_LABELS = {
    'bank': '은행', 'card': '카드', 'insurance': '보험',
    'internet_insurance': '인터넷보험', 'securities': '증권',
    'healthcare': '헬스케어', 'hospital': '병원',
}

if USE_MOCK:
    from mock_data import (
        MOCK_USERS, MOCK_SCORES,
        MOCK_CONSENTS, MOCK_RECOMMEND_HISTORY, MOCK_IDENTITIES,
        MOCK_CAMPAIGNS, MOCK_RECENT_RECOMMENDS,
        MOCK_PRODUCT_FUNNEL, MOCK_TOP_VIEWED, MOCK_TAB_CLICKS,
    )


# ── DB / DynamoDB 헬퍼 ────────────────────────────────
def get_db():
    import pymysql
    return pymysql.connect(
        host=os.environ['AURORA_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        database=os.environ.get('DB_NAME', 'lifesync'),
        cursorclass=pymysql.cursors.DictCursor,
    )


_dynamo = None

def get_dynamo_table():
    global _dynamo
    if _dynamo is None:
        _dynamo = boto3.resource('dynamodb', region_name=AWS_REGION)
    return _dynamo.Table(DYNAMO_TABLE)


def _add_rates(funnel_rows):
    for row in funnel_rows:
        rec = row['recommended'] or 1
        row['click_rate']    = round(row['clicked']   / rec * 100)
        row['purchase_rate'] = round(row['purchased'] / rec * 100)
    return funnel_rows


def _get_identities(global_id):
    if not PRIVATE_API_URL:
        return []
    try:
        resp = requests.get(f'{PRIVATE_API_URL}/internal/customer/{global_id}', timeout=3)
        if resp.ok:
            return resp.json().get('identities', [])
    except Exception:
        pass
    return []


# ── Auth ──────────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/health')
def health():
    return {'status': 'ok'}


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if (request.form.get('username') == ADMIN_USER and
                request.form.get('password') == ADMIN_PASS):
            session['logged_in'] = True
            return redirect(url_for('overview'))
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return redirect(url_for('overview'))


# ── Overview ──────────────────────────────────────────
@app.route('/overview')
@login_required
def overview():
    if USE_MOCK:
        total_users = len(MOCK_USERS)
        grade_dist  = {g: 0 for g in GRADES}
        for u in MOCK_USERS:
            grade_dist[u['grade']] = grade_dist.get(u['grade'], 0) + 1

        scored_items = list(MOCK_SCORES.values())
        analyzed     = len(scored_items)
        avg_score    = round(sum(float(s['dynamic_score']) for s in scored_items) / analyzed, 1)
        recent       = sorted(
            [{'global_id': gid, **s} for gid, s in MOCK_SCORES.items()],
            key=lambda x: x['update_time'], reverse=True
        )[:5]
        recent_users = {u['global_id']: u for u in MOCK_USERS}

        all_consents = [c for v in MOCK_CONSENTS.values() for c in v]
        consent_rate = round(
            sum(1 for c in all_consents if c['consent_yn'] == 'Y') / len(all_consents) * 100, 1
        ) if all_consents else 0
        active_campaigns = MOCK_CAMPAIGNS
        user_map = {u['global_id']: u for u in MOCK_USERS}
        recent_recommends = [
            {**r, 'name': user_map.get(r['global_id'], {}).get('name', '-')}
            for r in MOCK_RECENT_RECOMMENDS
        ]
        product_funnel = _add_rates([{**r} for r in MOCK_PRODUCT_FUNNEL])
        top_viewed     = MOCK_TOP_VIEWED
        tab_clicks     = MOCK_TAB_CLICKS
    else:
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute('SELECT COUNT(*) as cnt FROM users')
                total_users = cur.fetchone()['cnt']
                cur.execute('SELECT grade, COUNT(*) as cnt FROM users GROUP BY grade')
                grade_dist = {g: 0 for g in GRADES}
                for row in cur.fetchall():
                    grade_dist[row['grade']] = row['cnt']
                cur.execute(
                    'SELECT COUNT(*) as total, SUM(consent_yn = "Y") as agreed FROM consent'
                )
                crow = cur.fetchone()
                consent_rate = round(crow['agreed'] / crow['total'] * 100, 1) if crow['total'] else 0
                cur.execute(
                    'SELECT campaign_id, campaign_name, target_grade, start_dt, end_dt '
                    'FROM campaign_master WHERE end_dt >= CURDATE() ORDER BY start_dt DESC LIMIT 10'
                )
                active_campaigns = cur.fetchall()
                cur.execute(
                    'SELECT r.global_id, r.product_name, r.recommended_at, r.clicked_at, r.purchased_at, u.name '
                    'FROM customer_recommend_history r JOIN users u ON r.global_id = u.global_id '
                    'ORDER BY r.recommended_at DESC LIMIT 5'
                )
                recent_recommends = cur.fetchall()
                cur.execute(
                    'SELECT product_name, affiliate_id as affiliate, COUNT(*) as recommended, '
                    'SUM(clicked_at IS NOT NULL) as clicked, '
                    'SUM(purchased_at IS NOT NULL) as purchased '
                    'FROM customer_recommend_history '
                    'GROUP BY product_name, affiliate_id ORDER BY purchased DESC LIMIT 10'
                )
                product_funnel = _add_rates(list(cur.fetchall()))
                cur.execute(
                    'SELECT event_target, COUNT(*) as count '
                    'FROM customer_event_log WHERE event_type = %s '
                    'GROUP BY event_target ORDER BY count DESC LIMIT 5',
                    ('product_view',)
                )
                top_viewed = cur.fetchall()
                cur.execute(
                    'SELECT event_target, COUNT(*) as count '
                    'FROM customer_event_log WHERE event_type = %s '
                    'GROUP BY event_target ORDER BY count DESC',
                    ('tab_click',)
                )
                tab_clicks = cur.fetchall()
        finally:
            db.close()

        result    = get_dynamo_table().scan(ProjectionExpression='global_id, dynamic_score, dynamic_grade, update_time')
        items     = result.get('Items', [])
        analyzed  = len(items)
        avg_score = round(sum(float(i.get('dynamic_score', 0)) for i in items) / analyzed, 1) if analyzed else 0
        recent    = sorted(items, key=lambda x: x.get('update_time', ''), reverse=True)[:5]

        recent_global_ids = [i['global_id'] for i in recent]
        db2 = get_db()
        try:
            with db2.cursor() as cur:
                placeholders = ','.join(['%s'] * len(recent_global_ids))
                cur.execute(
                    f'SELECT ls_user_id, global_id, name FROM users WHERE global_id IN ({placeholders})',
                    recent_global_ids
                )
                recent_users = {row['global_id']: row for row in cur.fetchall()}
        finally:
            db2.close()

    return render_template('overview.html',
        total_users=total_users,
        grade_dist=grade_dist,
        analyzed=analyzed,
        no_data=total_users - analyzed,
        avg_score=avg_score,
        recent=recent,
        recent_users=recent_users,
        grades=GRADES,
        consent_rate=consent_rate,
        active_campaigns=active_campaigns,
        recent_recommends=recent_recommends,
        product_funnel=product_funnel,
        top_viewed=top_viewed,
        tab_clicks=tab_clicks,
    )


# ── Users ─────────────────────────────────────────────
@app.route('/users')
@login_required
def users():
    q            = request.args.get('q', '').strip()
    grade_filter = request.args.get('grade', '')
    page         = max(1, int(request.args.get('page', 1)))
    per_page     = 20
    offset       = (page - 1) * per_page

    if USE_MOCK:
        filtered = MOCK_USERS
        if q:
            filtered = [u for u in filtered if q in u['name'] or q in u['email']]
        if grade_filter:
            filtered = [u for u in filtered if u['grade'] == grade_filter]
        total     = len(filtered)
        user_list = filtered[offset:offset + per_page]
    else:
        db = get_db()
        try:
            with db.cursor() as cur:
                wheres, params = [], []
                if q:
                    wheres.append('(name LIKE %s OR email LIKE %s)')
                    params += [f'%{q}%', f'%{q}%']
                if grade_filter:
                    wheres.append('grade = %s')
                    params.append(grade_filter)
                where = ('WHERE ' + ' AND '.join(wheres)) if wheres else ''
                cur.execute(f'SELECT COUNT(*) as cnt FROM users {where}', params)
                total = cur.fetchone()['cnt']
                cur.execute(
                    f'SELECT ls_user_id, global_id, name, email, grade FROM users {where} ORDER BY ls_user_id DESC LIMIT %s OFFSET %s',
                    params + [per_page, offset]
                )
                user_list = cur.fetchall()
        finally:
            db.close()

    return render_template('users.html',
        users=user_list,
        q=q,
        grade_filter=grade_filter,
        grades=GRADES,
        page=page,
        total_pages=max(1, (total + per_page - 1) // per_page),
        total=total,
    )


# ── User Detail ───────────────────────────────────────
@app.route('/users/<ls_user_id>')
@login_required
def user_detail(ls_user_id):
    if USE_MOCK:
        user = next((u for u in MOCK_USERS if u['ls_user_id'] == ls_user_id), None)
        if not user:
            return redirect(url_for('users'))
        scores            = MOCK_SCORES.get(user['global_id'])
        consents          = MOCK_CONSENTS.get(user['global_id'], [])
        recommend_history = MOCK_RECOMMEND_HISTORY.get(user['global_id'], [])
        identities        = MOCK_IDENTITIES.get(user['global_id'], [])
    else:
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    'SELECT ls_user_id, global_id, name, email, grade FROM users WHERE ls_user_id = %s',
                    (ls_user_id,)
                )
                user = cur.fetchone()
                if not user:
                    return redirect(url_for('users'))
                cur.execute(
                    'SELECT consent_key, consent_yn, updated_at FROM consent WHERE global_id = %s',
                    (user['global_id'],)
                )
                consents = cur.fetchall()
                cur.execute(
                    'SELECT product_name, recommended_at, clicked_at, purchased_at '
                    'FROM customer_recommend_history WHERE global_id = %s ORDER BY recommended_at DESC',
                    (user['global_id'],)
                )
                recommend_history = cur.fetchall()
        finally:
            db.close()
        result     = get_dynamo_table().get_item(Key={'global_id': user['global_id']})
        scores     = result.get('Item')
        identities = _get_identities(user['global_id'])

    return render_template('user_detail.html',
        user=user,
        scores=scores,
        consents=consents,
        recommend_history=recommend_history,
        identities=identities,
    )


@app.context_processor
def inject_config():
    return {
        'config': {'USE_MOCK': USE_MOCK, 'ADMIN_USER': ADMIN_USER},
        'consent_labels': CONSENT_LABELS,
    }


if __name__ == '__main__':
    app.run(debug=True, port=5001)

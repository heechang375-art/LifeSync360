import os
import functools

import boto3
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-dev-secret-32bytes-lifesync!!')  # TODO: 운영 배포 시 env var로 교체

USE_MOCK             = os.environ.get('USE_MOCK', 'true').lower() == 'true'
ADMIN_USER           = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS           = os.environ.get('ADMIN_PASSWORD', 'admin1234')  # TODO: 운영 배포 시 env var로 교체
DYNAMO_TABLE         = os.environ.get('DYNAMO_TABLE', 'lifesync-scores')
AWS_REGION           = os.environ.get('AWS_REGION', 'ap-northeast-2')
PRIVATE_API_URL      = os.environ.get('PRIVATE_API_URL', '')
ONPREM_QUERY_LAMBDA  = os.environ.get('ONPREM_QUERY_LAMBDA', '')

GRADES = ['VIP', 'GOLD', 'SILVER', 'BASIC', 'CARE']
CONSENT_LABELS = {
    'BANK':       '은행',
    'CARD':       '카드',
    'INSURANCE':  '보험',
    'SECURITIES': '증권',
    'HEALTHCARE': '헬스케어',
    'HOSPITAL':   '병원',
    'WEARABLE':   '웨어러블',
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
        database=os.environ.get('DB_NAME', 'lifesync360'),
        cursorclass=pymysql.cursors.DictCursor,
    )


_dynamo        = None
_lambda_client = None


def get_dynamo_table():
    global _dynamo
    if _dynamo is None:
        _dynamo = boto3.resource('dynamodb', region_name=AWS_REGION)
    return _dynamo.Table(DYNAMO_TABLE)


def _get_lambda():
    global _lambda_client
    if _lambda_client is None:
        import json as _j
        _lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    return _lambda_client


def _call_onprem(action, **kwargs):
    if not ONPREM_QUERY_LAMBDA:
        return {}
    import json as _j
    resp   = _get_lambda().invoke(
        FunctionName=ONPREM_QUERY_LAMBDA,
        InvocationType='RequestResponse',
        Payload=_j.dumps({'action': action, **kwargs}),
    )
    result = _j.loads(resp['Payload'].read())
    if result.get('statusCode') != 200:
        return {}
    body = result.get('body', '{}')
    return _j.loads(body) if isinstance(body, str) else body


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
            sum(1 for c in all_consents if c['consent_flag'] == 'Y') / len(all_consents) * 100, 1
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
        # ① Aurora — 캠페인·추천이력·퍼널·대시보드 로그
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    'SELECT campaign_id, campaign_name, target_grade, start_date, end_date '
                    'FROM campaign_master WHERE end_date >= CURDATE() ORDER BY start_date DESC LIMIT 10'
                )
                active_campaigns = cur.fetchall()

                cur.execute(
                    'SELECT r.global_id, p.product_name, r.recommended_at, '
                    '       r.clicked_flag, r.purchased_flag '
                    'FROM customer_recommend_history r '
                    'JOIN product_master p ON r.product_id = p.product_id '
                    'ORDER BY r.recommended_at DESC LIMIT 5'
                )
                recent_recommends = cur.fetchall()

                cur.execute(
                    'SELECT p.product_name, c.company_name as affiliate, '
                    '       COUNT(*) as recommended, '
                    '       SUM(r.clicked_flag = "Y") as clicked, '
                    '       SUM(r.purchased_flag = "Y") as purchased '
                    'FROM customer_recommend_history r '
                    'JOIN product_master p ON r.product_id = p.product_id '
                    'JOIN company_master c ON p.company_id = c.company_id '
                    'GROUP BY p.product_id, p.product_name, c.company_name '
                    'ORDER BY purchased DESC LIMIT 10'
                )
                product_funnel = _add_rates(list(cur.fetchall()))

                cur.execute(
                    'SELECT p.product_name as event_target, COUNT(*) as count '
                    'FROM customer_dashboard_log d '
                    'JOIN product_master p ON d.click_product_id = p.product_id '
                    'WHERE d.product_click = "Y" '
                    'GROUP BY p.product_id, p.product_name ORDER BY count DESC LIMIT 5'
                )
                top_viewed = cur.fetchall()

                cur.execute(
                    'SELECT page_type as event_target, COUNT(*) as count '
                    'FROM customer_dashboard_log GROUP BY page_type ORDER BY count DESC'
                )
                tab_clicks = cur.fetchall()
        finally:
            db.close()

        # ② DynamoDB — 등급 분포·점수 통계 (온프레미스 users 불필요)
        result    = get_dynamo_table().scan(
            ProjectionExpression='global_id, dynamic_score, dynamic_grade, update_time'
        )
        items     = result.get('Items', [])
        analyzed  = len(items)
        avg_score = round(sum(float(i.get('dynamic_score', 0)) for i in items) / analyzed, 1) if analyzed else 0
        recent    = sorted(items, key=lambda x: x.get('update_time', ''), reverse=True)[:5]

        grade_dist = {g: 0 for g in GRADES}
        for item in items:
            g = item.get('dynamic_grade', 'BASIC')
            if g in grade_dist:
                grade_dist[g] += 1

        # total_users: Aurora users_ref 동기화 전까지 DynamoDB 분석 건수로 대체
        total_users  = analyzed
        consent_rate = 0  # Aurora users_ref 동기화 후 구현
        recent_users = {i['global_id']: {'global_id': i['global_id'], 'ls_user_id': i['global_id']} for i in recent}

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
        # DynamoDB 기반 목록 — Aurora users_ref 동기화 전 임시
        result = get_dynamo_table().scan(
            ProjectionExpression='global_id, dynamic_score, dynamic_grade, update_time'
        )
        items = result.get('Items', [])

        if grade_filter:
            items = [i for i in items if i.get('dynamic_grade') == grade_filter]
        if q:
            items = [i for i in items if q.lower() in i.get('global_id', '').lower()]

        total = len(items)
        items.sort(key=lambda x: x.get('update_time', ''), reverse=True)
        user_list = [
            {
                'global_id':  i['global_id'],
                'ls_user_id': '-',
                'name':       '-',
                'email':      '-',
                'grade':      i.get('dynamic_grade', '-'),
            }
            for i in items[offset:offset + per_page]
        ]

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
@app.route('/users/<global_id>')
@login_required
def user_detail(global_id):
    if USE_MOCK:
        user = next((u for u in MOCK_USERS if u['global_id'] == global_id), None)
        if not user:
            return redirect(url_for('users'))
        scores            = MOCK_SCORES.get(global_id)
        consents          = MOCK_CONSENTS.get(global_id, [])
        recommend_history = MOCK_RECOMMEND_HISTORY.get(global_id, [])
        identities        = MOCK_IDENTITIES.get(global_id, [])
    else:
        # ① DynamoDB — 등급·점수
        result = get_dynamo_table().get_item(Key={'global_id': global_id})
        scores = result.get('Item')

        # ② 온프레미스 Lambda — 동의 현황 (개별 조회는 Lambda 경유 허용)
        consent_data = _call_onprem('get_consent', global_id=global_id)
        consents     = consent_data.get('consents', [])

        # ③ Aurora — 추천 이력
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    'SELECT p.product_name, r.recommended_at, r.clicked_flag, r.purchased_flag '
                    'FROM customer_recommend_history r '
                    'JOIN product_master p ON r.product_id = p.product_id '
                    'WHERE r.global_id = %s ORDER BY r.recommended_at DESC',
                    (global_id,)
                )
                recommend_history = cur.fetchall()
        finally:
            db.close()

        # ④ Private API — 제휴사 매핑
        identities = _get_identities(global_id)

        # 기본 유저 정보: Aurora users_ref 동기화 전까지 available 필드만 표시
        user = {
            'global_id':  global_id,
            'ls_user_id': '-',
            'name':       '-',
            'email':      '-',
            'grade':      scores.get('dynamic_grade', '-') if scores else '-',
        }

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

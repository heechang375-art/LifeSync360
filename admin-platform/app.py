import os
import functools

import boto3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']

USE_MOCK     = os.environ.get('USE_MOCK', 'true').lower() == 'true'
ADMIN_USER   = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS   = os.environ['ADMIN_PASSWORD']
DYNAMO_TABLE = os.environ.get('DYNAMO_TABLE', 'lifesync-scores')
AWS_REGION   = os.environ.get('AWS_REGION', 'ap-northeast-2')

GRADES = ['PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'BASIC']

if USE_MOCK:
    from mock_data import MOCK_USERS, MOCK_SCORES


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
        scores = MOCK_SCORES.get(user['global_id'])
    else:
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    'SELECT ls_user_id, global_id, name, email, grade FROM users WHERE ls_user_id = %s',
                    (ls_user_id,)
                )
                user = cur.fetchone()
        finally:
            db.close()
        if not user:
            return redirect(url_for('users'))
        result = get_dynamo_table().get_item(Key={'global_id': user['global_id']})
        scores = result.get('Item')

    return render_template('user_detail.html', user=user, scores=scores)


@app.context_processor
def inject_config():
    return {'config': {'USE_MOCK': USE_MOCK, 'ADMIN_USER': ADMIN_USER}}


if __name__ == '__main__':
    app.run(debug=True, port=5001)

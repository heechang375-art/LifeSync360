import os
import datetime
import uuid
import json as _json
from datetime import timezone
import jwt
import redis
import boto3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
JWT_SECRET          = os.environ['JWT_SECRET']
USE_MOCK            = os.environ.get('USE_MOCK', 'true').lower() == 'true'
PROFILE_SYNC_LAMBDA = os.environ.get('PROFILE_SYNC_LAMBDA', 'customer-profile-sync')
AWS_REGION          = os.environ.get('AWS_REGION', 'ap-northeast-2')

if USE_MOCK:
    from mock_data import (
        MOCK_USERS, MOCK_POINTS, MOCK_POINT_HISTORY,
        MOCK_RECOMMENDATIONS, PRODUCTS_MAP, get_mock_health,
        get_mock_upgrade_actions, MOCK_MY_PRODUCTS, MOCK_CONSENTED_KEYS,
    )

# 로컬/클라우드 공통 정적 설정
COMPANIES = [
    {'key': 'bank',       'name': 'LS 은행'},
    {'key': 'card',       'name': 'LS 카드'},
    {'key': 'insurance',  'name': 'LS 보험'},
    {'key': 'inet_ins',   'name': 'LS 온라인보험'},
    {'key': 'securities', 'name': 'LS 증권'},
    {'key': 'healthcare', 'name': 'LS 헬스케어'},
    {'key': 'hospital',   'name': 'LS 병원'},
]

CONSENTS = [
    {'key': 'bank',       'label': '은행 데이터 활용 동의'},
    {'key': 'card',       'label': '카드 데이터 활용 동의'},
    {'key': 'insurance',  'label': '보험 데이터 활용 동의'},
    {'key': 'inet_ins',   'label': '온라인 보험 데이터 활용 동의'},
    {'key': 'securities', 'label': '증권 데이터 활용 동의'},
    {'key': 'healthcare', 'label': '헬스케어 데이터 활용 동의'},
    {'key': 'hospital',   'label': '병원 데이터 활용 동의'},
    {'key': 'wearable',   'label': '웨어러블 동의'},
]

GRADE_BENEFITS = {
    'PLATINUM': {'color': 'platinum', 'desc': '최상위 고객 전용 혜택', 'benefits': [
        '보험료 최대 15% 할인', '포인트 3배 적립', 'PB 전담 매니저 배정',
        '공항 라운지 무제한', 'VIP 종합 건강검진 무료',
    ]},
    'GOLD': {'color': 'gold', 'desc': '우수 고객 혜택', 'benefits': [
        '보험료 10% 할인', '포인트 2배 적립', '건강검진 30% 할인',
        '전용 상담 채널 이용', '금융상품 우대금리 0.3%p',
    ]},
    'SILVER': {'color': 'silver', 'desc': '일반 우대 혜택', 'benefits': [
        '보험료 5% 할인', '포인트 1.5배 적립', '건강검진 15% 할인',
        '금융상품 우대금리 0.1%p',
    ]},
    'BRONZE': {'color': 'bronze', 'desc': '기본 우대 혜택', 'benefits': [
        '보험료 3% 할인', '포인트 1.2배 적립', '건강검진 10% 할인',
    ]},
    'BASIC': {'color': 'basic', 'desc': '기본 혜택', 'benefits': [
        '포인트 기본 적립', '제휴 서비스 이용',
    ]},
}


# ── DB / 인프라 헬퍼 ──────────────────────────────────
_redis  = None
_dynamo = None

def get_redis():
    global _redis
    if _redis is None:
        host = os.environ.get('REDIS_HOST')
        if not host:
            raise RuntimeError('REDIS_HOST 환경변수가 설정되지 않았습니다.')
        _redis = redis.Redis(host=host, port=int(os.environ.get('REDIS_PORT', '6379')), decode_responses=True)
    return _redis

def get_dynamo_table():
    global _dynamo
    if _dynamo is None:
        _dynamo = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))
    return _dynamo.Table(os.environ.get('DYNAMO_TABLE', 'lifesync-scores'))

def get_db():
    import pymysql
    return pymysql.connect(
        host=os.environ['AURORA_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        database=os.environ.get('DB_NAME', 'lifesync'),
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── Lambda 호출 ───────────────────────────────────────
_lambda_client = None

def _get_lambda():
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    return _lambda_client

def _resolve_global_id(ls_user_id, email):
    """global_id 미설정 유저의 계열사 ID 매핑 조회 (Lambda invoke)"""
    try:
        resp = _get_lambda().invoke(
            FunctionName=PROFILE_SYNC_LAMBDA,
            InvocationType='RequestResponse',
            Payload=_json.dumps({'ls_user_id': ls_user_id, 'email': email}),
        )
        result = _json.loads(resp['Payload'].read())
        if result.get('statusCode') == 200:
            return _json.loads(result['body'])['global_id']
    except Exception:
        pass
    return None


# ── JWT ───────────────────────────────────────────────
def make_jwt(ls_user_id, global_id):
    payload = {
        'sub': ls_user_id,
        'gid': global_id,
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_jwt(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])


# ── API ──────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if USE_MOCK:
        user = list(MOCK_USERS.values())[0]
        token = make_jwt(user['ls_user_id'], user['global_id'])
        return jsonify({'token': token, 'ls_user_id': user['ls_user_id']})

    db = get_db()
    try:
        with db.cursor() as cur:
            ls_user_id = f"LS-{datetime.datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            cur.execute(
                'INSERT INTO users (ls_user_id, email, name, password_hash) VALUES (%s, %s, %s, %s)',
                (ls_user_id, data['email'], data['name'], generate_password_hash(data['password']))
            )
            db.commit()
        token = make_jwt(ls_user_id, ls_user_id)
        return jsonify({'token': token, 'ls_user_id': ls_user_id})
    finally:
        db.close()


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email    = data.get('email', '')
    password = data.get('password', '')

    if USE_MOCK:
        user = MOCK_USERS.get(email)
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
        token = make_jwt(user['ls_user_id'], user['global_id'])
        return jsonify({'token': token, 'ls_user_id': user['ls_user_id']})

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
    finally:
        db.close()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401

    global_id = user.get('global_id')
    if not global_id:
        global_id = _resolve_global_id(user['ls_user_id'], email)

    token = make_jwt(user['ls_user_id'], global_id or user['ls_user_id'])
    return jsonify({'token': token, 'ls_user_id': user['ls_user_id']})


@app.route('/api/me')
def api_me():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)

        if USE_MOCK:
            user = next((u for u in MOCK_USERS.values() if u['ls_user_id'] == payload['sub']), None)
            if not user:
                return jsonify({'error': 'user not found'}), 404
            return jsonify({
                'ls_user_id': payload['sub'],
                'global_id':  payload['gid'],
                'name':       user['name'],
                'grade':      user['grade'],
                'email':      user['email'],
            })

        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    'SELECT name, email, grade, global_id FROM users WHERE ls_user_id = %s',
                    (payload['sub'],)
                )
                user = cur.fetchone()
        finally:
            db.close()
        if not user:
            return jsonify({'error': 'user not found'}), 404
        return jsonify({
            'ls_user_id': payload['sub'],
            'global_id':  user.get('global_id', payload['gid']),
            'name':       user['name'],
            'grade':      user['grade'],
            'email':      user['email'],
        })

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401


@app.route('/api/consent', methods=['POST'])
def api_consent():
    if USE_MOCK:
        return jsonify({'status': 'ok'})

    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    consents = request.get_json().get('consents', [])
    all_keys = [c['key'] for c in CONSENTS]
    db = get_db()
    try:
        with db.cursor() as cur:
            for key in all_keys:
                cur.execute(
                    '''INSERT INTO consent (global_id, consent_key, consent_yn)
                       VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE consent_yn = VALUES(consent_yn)''',
                    (payload['gid'], key, 'Y' if key in consents else 'N')
                )
            db.commit()
    finally:
        db.close()
    return jsonify({'status': 'ok'})


@app.route('/api/recommendations')
def api_recommendations():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    if USE_MOCK:
        return jsonify(MOCK_RECOMMENDATIONS)

    global_id = payload['gid']

    # ① Redis 캐시 조회
    product_ids = None
    try:
        cached = get_redis().get(f'rec:{global_id}')
        if cached:
            product_ids = _json.loads(cached)
    except Exception:
        pass  # Redis 장애 시 Aurora fallback

    db = get_db()
    try:
        with db.cursor() as cur:
            if product_ids is not None:
                # ② 캐시 히트
                placeholders = ', '.join(['%s'] * len(product_ids))
                cur.execute(f"""
                    SELECT product_id, company_id, product_type,
                           product_name, product_desc, product_tag
                    FROM product_master
                    WHERE product_id IN ({placeholders}) AND is_active = 1
                """, product_ids)
            else:
                # ③ 캐시 미스 — 등급 기준 직접 조회
                cur.execute('SELECT grade FROM users WHERE global_id = %s', (global_id,))
                row   = cur.fetchone()
                grade = row['grade'] if row else 'BASIC'
                grade_levels = ['BASIC', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM']
                idx   = grade_levels.index(grade) if grade in grade_levels else 0
                accessible   = grade_levels[:idx + 1]
                placeholders = ', '.join(['%s'] * len(accessible))
                cur.execute(f"""
                    SELECT pm.product_id, pm.company_id, pm.product_type,
                           pm.product_name, pm.product_desc, pm.product_tag
                    FROM product_master pm
                    WHERE pm.is_active = 1 AND pm.min_grade IN ({placeholders})
                    ORDER BY pm.product_id LIMIT 50
                """, accessible)
            products = cur.fetchall()
    finally:
        db.close()

    return jsonify(products)


@app.route('/api/upgrade-actions')
def api_upgrade_actions():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    if USE_MOCK:
        return jsonify(get_mock_upgrade_actions(payload['sub']))

    # TODO: 운영 전환 시 아래 블록 구현
    # from upgrade_actions_engine import get_personalized_actions
    # ctx = {
    #     'health_score':      _get_dynamo_score(payload['gid']),
    #     'wearable_linked':   _get_bq_wearable(payload['gid']),
    #     'checkup_this_year': _get_bq_checkup(payload['gid']),
    #     'insurance_months':  _get_aurora_insurance_months(payload['gid']),
    #     'consent_count':     _get_aurora_consent_count(payload['gid']),
    #     'avg_steps':         _get_bq_steps(payload['gid']),
    # }
    # return jsonify(get_personalized_actions(ctx))
    return jsonify([])


@app.route('/api/my-products')
def api_my_products():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    company_key = request.args.get('company', '')

    if USE_MOCK:
        consented = MOCK_CONSENTED_KEYS.get(payload['sub'], set())
        if company_key and company_key not in consented:
            return jsonify({'error': 'consent_required'}), 403
        user_prods = MOCK_MY_PRODUCTS.get(payload['sub'], {})
        return jsonify(user_prods.get(company_key, []))

    # TODO: 운영 전환 시 Aurora consent 테이블 확인 후 product_master + 계열사 API 조회
    # with db.cursor() as cur:
    #     cur.execute("SELECT consent_yn FROM consent WHERE global_id=%s AND consent_key=%s", (payload['gid'], company_key))
    #     row = cur.fetchone()
    #     if not row or row['consent_yn'] != 'Y':
    #         return jsonify({'error': 'consent_required'}), 403
    return jsonify([])


@app.route('/health')
def health():
    return {'status': 'ok'}


@app.route('/api/dashboard')
def api_dashboard():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    if USE_MOCK:
        h = get_mock_health(payload['sub'])
        return jsonify({**h, 'no_data': False})

    result = get_dynamo_table().get_item(Key={'global_id': payload['gid']})
    item   = result.get('Item')
    if not item:
        return jsonify({'no_data': True})

    def _f(key):
        v = item.get(key, '')
        return float(v) if v else None

    return jsonify({
        'no_data':          False,
        'dynamic_score':    _f('dynamic_score'),
        'health_score':     _f('health_score'),
        'fin_score':        _f('fin_score'),
        'behavior_score':   _f('behavior_score'),
        'next_best_action': item.get('next_best_action'),
        'update_time':      item.get('update_time'),
    })


# ── 페이지 ────────────────────────────────────────────
@app.route('/settings')
def settings():
    if USE_MOCK:
        points        = MOCK_POINTS
        point_history = MOCK_POINT_HISTORY
    else:
        points        = {'balance': 0, 'next_grade': '-', 'next_grade_points': 0, 'next_grade_percent': 0}
        point_history = []

    return render_template('settings.html',
        grade_benefits=GRADE_BENEFITS,
        consents=CONSENTS,
        points=points,
        point_history=point_history,
    )


@app.route('/product/<product_id>')
def product(product_id):
    if USE_MOCK:
        item = PRODUCTS_MAP.get(product_id)
        if not item:
            return redirect(url_for('dashboard'))
        return render_template('product.html', item=item)

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                '''SELECT product_id, company_id, product_type, product_name,
                          product_desc, product_tag
                   FROM product_master WHERE product_id = %s AND is_active = 1''',
                (product_id,)
            )
            row = cur.fetchone()
    finally:
        db.close()
    if not row:
        return redirect(url_for('dashboard'))
    item = {
        'id':       row['product_id'],
        'name':     row['product_name'],
        'type':     row['product_type'],
        'desc':     row['product_desc'],
        'tag':      row.get('product_tag', ''),
        'detail':   [],
        'category': row.get('company_id', ''),
    }
    return render_template('product.html', item=item)


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/consent')
def consent():
    return render_template('consent.html', consents=CONSENTS)


@app.route('/')
def dashboard():
    recs = MOCK_RECOMMENDATIONS if USE_MOCK else []
    return render_template('index.html', recommendations=recs, companies=COMPANIES)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

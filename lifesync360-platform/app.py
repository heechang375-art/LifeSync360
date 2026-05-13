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
# USE_MOCK            = os.environ.get('USE_MOCK', 'true').lower() == 'true'
USE_MOCK            = os.environ.get('USE_MOCK', 'false').lower() == 'false'  # 실제 배포에서는 MOCK 사용 안함
PROFILE_SYNC_LAMBDA = os.environ.get('PROFILE_SYNC_LAMBDA', '')
AWS_REGION          = os.environ.get('AWS_REGION', 'ap-northeast-2')

if USE_MOCK:
    from mock_data import (
        MOCK_USERS, MOCK_POINTS, MOCK_POINT_HISTORY,
        MOCK_RECOMMENDATIONS, PRODUCTS_MAP, get_mock_health,
        get_mock_upgrade_actions, MOCK_MY_PRODUCTS, MOCK_CONSENTED_KEYS,
    )

COMPANIES = [
    {'key': 'BANK',       'name': 'LS 은행'},
    {'key': 'CARD',       'name': 'LS 카드'},
    {'key': 'INSURANCE',  'name': 'LS 보험'},
    {'key': 'SECURITIES', 'name': 'LS 증권'},
    {'key': 'HEALTHCARE', 'name': 'LS 헬스케어'},
    {'key': 'HOSPITAL',   'name': 'LS 병원'},
]

CONSENTS = [
    {'key': 'BANK',       'label': '은행 데이터 활용 동의'},
    {'key': 'CARD',       'label': '카드 데이터 활용 동의'},
    {'key': 'INSURANCE',  'label': '보험 데이터 활용 동의'},
    {'key': 'SECURITIES', 'label': '증권 데이터 활용 동의'},
    {'key': 'HEALTHCARE', 'label': '헬스케어 데이터 활용 동의'},
    {'key': 'HOSPITAL',   'label': '병원 데이터 활용 동의'},
    {'key': 'WEARABLE',   'label': '웨어러블 동의'},
]

# Service-DB 등급 체계: VIP > GOLD > SILVER > BASIC, CARE는 건강 특화
GRADE_SCORE_MAP = {
    'VIP':    90,
    'GOLD':   80,
    'SILVER': 70,
    'BASIC':  60,
    'CARE':    0,
}

GRADE_BENEFITS = {
    'VIP': {'color': 'platinum', 'desc': '최상위 고객 전용 혜택', 'benefits': [
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
    'BASIC': {'color': 'basic', 'desc': '기본 혜택', 'benefits': [
        '포인트 기본 적립', '제휴 서비스 이용',
    ]},
    'CARE': {'color': 'care', 'desc': '건강관리 특화 혜택', 'benefits': [
        'AI 건강 리포트 제공', '운동/식단 코칭', '건강검진 우선 예약',
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
        _dynamo = boto3.resource('dynamodb', region_name=AWS_REGION)
    return _dynamo.Table(os.environ['DYNAMO_TABLE'])

def get_db():
    """Service-DB (lifesync360) 연결"""
    import pymysql
    return pymysql.connect(
        host=os.environ['AURORA_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        database=os.environ['DB_NAME'],
        cursorclass=pymysql.cursors.DictCursor,
    )

def get_auth_db():
    """인증 DB (users / consent) 연결 — 온프레미스 또는 별도 Aurora DB"""
    import pymysql
    return pymysql.connect(
        host=os.environ['AUTH_DB_HOST'],
        user=os.environ['AUTH_DB_USER'],
        password=os.environ['AUTH_DB_PASS'],
        database=os.environ['AUTH_DB_NAME'],
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
    if not PROFILE_SYNC_LAMBDA:
        return None
    try:
        resp = _get_lambda().invoke(
            FunctionName=PROFILE_SYNC_LAMBDA,
            InvocationType='RequestResponse',
            Payload=_json.dumps({'ls_user_id': ls_user_id, 'email': email}),
        )
        result = _json.loads(resp['Payload'].read())
        if result.get('statusCode') == 200:
            return _json.loads(result['body'])['global_customer_id']
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

    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip()
    password = data.get('password') or ''
    if not name or not email or not password:
        return jsonify({'error': '이름, 이메일, 비밀번호는 필수 입력 항목입니다.'}), 400
    if len(password) < 8:
        return jsonify({'error': '비밀번호는 8자 이상이어야 합니다.'}), 400

    db = get_auth_db()
    try:
        with db.cursor() as cur:
            ls_user_id = f"LS-{datetime.datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            global_id  = f"G-{uuid.uuid4().hex[:12].upper()}"

            cur.execute(
                'INSERT INTO master_customer (global_customer_id) VALUES (%s)',
                (global_id,)
            )
            cur.execute(
                'INSERT INTO users (ls_user_id, global_customer_id, login_email, password_hash) VALUES (%s, %s, %s, %s)',
                (ls_user_id, global_id, data['email'], generate_password_hash(data['password']))
            )
            db.commit()
        token = make_jwt(ls_user_id, global_id)
        return jsonify({'token': token, 'ls_user_id': ls_user_id})
    finally:
        db.close()


@app.route('/api/login', methods=['POST'])
def api_login():
    data     = request.get_json()
    email    = data.get('email', '')
    password = data.get('password', '')

    if USE_MOCK:
        user = MOCK_USERS.get(email)
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
        token = make_jwt(user['ls_user_id'], user['global_id'])
        return jsonify({'token': token, 'ls_user_id': user['ls_user_id']})

    db = get_auth_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE login_email = %s', (email,))
            user = cur.fetchone()
    finally:
        db.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401

    global_customer_id = user.get('global_customer_id') or _resolve_global_id(user['ls_user_id'], email)
    token = make_jwt(user['ls_user_id'], global_customer_id or user['ls_user_id'])
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

        db = get_auth_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    'SELECT login_email, global_customer_id FROM users WHERE ls_user_id = %s',
                    (payload['sub'],)
                )
                user = cur.fetchone()
        finally:
            db.close()

        if not user:
            return jsonify({'error': 'user not found'}), 404
        return jsonify({
            'ls_user_id': payload['sub'],
            'global_id':  user.get('global_customer_id', payload['gid']),
            'name':       None,
            'grade':      None,
            'email':      user['login_email'],
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
    db = get_auth_db()
    try:
        with db.cursor() as cur:
            for key in all_keys:
                cur.execute(
                    '''INSERT INTO consent (global_customer_id, domain, consent_flag)
                       VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE consent_flag = VALUES(consent_flag)''',
                    (payload['gid'], key, 'Y' if key in consents else 'N')
                )
            db.commit()
    finally:
        db.close()
    return jsonify({'status': 'ok'})


@app.route('/api/event', methods=['POST'])
def api_event():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    if USE_MOCK:
        return jsonify({'status': 'ok'})

    data         = request.get_json() or {}
    event_type   = data.get('event_type', '')
    product_id   = data.get('product_id')      # Service-DB BIGINT product_id
    global_id    = payload['gid']

    db = get_db()
    try:
        with db.cursor() as cur:
            if event_type == 'recommendation_click' and product_id:
                cur.execute(
                    'UPDATE customer_recommend_history SET clicked_flag = %s '
                    'WHERE global_id = %s AND product_id = %s AND clicked_flag = %s LIMIT 1',
                    ('Y', global_id, product_id, 'N')
                )
            elif event_type == 'purchased' and product_id:
                cur.execute(
                    'UPDATE customer_recommend_history SET purchased_flag = %s '
                    'WHERE global_id = %s AND product_id = %s AND purchased_flag = %s LIMIT 1',
                    ('Y', global_id, product_id, 'N')
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

    # ① DynamoDB에서 동적 등급/점수 조회
    grade         = 'BASIC'
    dynamic_score = None
    try:
        item = get_dynamo_table().get_item(Key={'global_id': global_id}).get('Item', {})
        grade         = item.get('dynamic_grade', 'BASIC')
        dynamic_score = float(item['dynamic_score']) if item.get('dynamic_score') else None
    except Exception:
        pass

    # ② Redis 캐시 조회
    product_ids = None
    try:
        cached = get_redis().get(f'rec:{global_id}')
        if cached:
            product_ids = _json.loads(cached)
    except Exception:
        pass

    db = get_db()
    try:
        with db.cursor() as cur:
            if product_ids:
                placeholders = ', '.join(['%s'] * len(product_ids))
                cur.execute(f"""
                    SELECT p.product_id, p.product_code, p.product_name, p.description,
                           p.target_grade, p.risk_level, p.priority_rank,
                           c.company_code, c.company_name, cat.category_code
                    FROM product_master p
                    JOIN company_master   c   ON p.company_id  = c.company_id
                    JOIN category_master  cat ON p.category_id = cat.category_id
                    WHERE p.product_id IN ({placeholders}) AND p.active_flag = 'Y'
                    ORDER BY p.priority_rank
                """, product_ids)
            else:
                min_score = GRADE_SCORE_MAP.get(grade, 60)
                cur.execute("""
                    SELECT p.product_id, p.product_code, p.product_name, p.description,
                           p.target_grade, p.risk_level, p.priority_rank,
                           c.company_code, c.company_name, cat.category_code
                    FROM product_master p
                    JOIN company_master   c   ON p.company_id  = c.company_id
                    JOIN category_master  cat ON p.category_id = cat.category_id
                    WHERE p.active_flag = 'Y'
                      AND p.min_score <= %s
                    ORDER BY p.priority_rank
                    LIMIT 20
                """, (min_score,))

            products = cur.fetchall()
            now = datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            for p in products:
                cur.execute(
                    '''INSERT INTO customer_recommend_history
                       (global_id, product_id, dynamic_score, dynamic_grade, action_code, recommended_at)
                       VALUES (%s, %s, %s, %s, %s, %s)''',
                    (global_id, p['product_id'], dynamic_score, grade, 'RECOMMEND_DASHBOARD', now)
                )
        db.commit()
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

    return jsonify([])


@app.route('/api/my-products')
def api_my_products():
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    if USE_MOCK:
        company_key = request.args.get('company', '')
        consented   = MOCK_CONSENTED_KEYS.get(payload['sub'], set())
        if company_key and company_key not in consented:
            return jsonify({'error': 'consent_required'}), 403
        user_prods = MOCK_MY_PRODUCTS.get(payload['sub'], {})
        return jsonify(user_prods.get(company_key, []))

    global_id   = payload['gid']
    company_key = request.args.get('company', '')

    db = get_db()
    try:
        with db.cursor() as cur:
            query = """
                SELECT p.product_code, p.product_name, p.description,
                       p.target_grade, p.risk_level,
                       c.company_code, c.company_name, cat.category_code,
                       h.recommended_at
                FROM customer_recommend_history h
                JOIN product_master  p   ON h.product_id  = p.product_id
                JOIN company_master  c   ON p.company_id  = c.company_id
                JOIN category_master cat ON p.category_id = cat.category_id
                WHERE h.global_id = %s
                  AND h.purchased_flag = 'Y'
                  AND p.active_flag = 'Y'
            """
            params = [global_id]
            if company_key:
                query += ' AND c.company_code = %s'
                params.append(company_key)
            query += ' ORDER BY h.recommended_at DESC'
            cur.execute(query, params)
            products = cur.fetchall()
    finally:
        db.close()

    return jsonify(products)


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


@app.route('/product/<product_code>')
def product(product_code):
    if USE_MOCK:
        item = PRODUCTS_MAP.get(product_code)
        if not item:
            return redirect(url_for('dashboard'))
        return render_template('product.html', item=item)

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT p.product_id, p.product_code, p.product_name, p.description,
                       p.target_grade, p.risk_level, p.min_score, p.max_score,
                       c.company_code, c.company_name, cat.category_code, cat.category_name
                FROM product_master p
                JOIN company_master   c   ON p.company_id  = c.company_id
                JOIN category_master  cat ON p.category_id = cat.category_id
                WHERE p.product_code = %s AND p.active_flag = 'Y'
            """, (product_code,))
            row = cur.fetchone()
            if not row:
                return redirect(url_for('dashboard'))

            cur.execute(
                'SELECT option_name, option_value FROM product_option WHERE product_id = %s ORDER BY option_id',
                (row['product_id'],)
            )
            options = cur.fetchall()
    finally:
        db.close()

    item = {
        'id':       row['product_code'],
        'name':     row['product_name'],
        'type':     row['target_grade'],
        'desc':     row['description'],
        'tag':      row['risk_level'],
        'detail':   [{'key': o['option_name'], 'value': o['option_value']} for o in options],
        'category': row['company_code'],
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

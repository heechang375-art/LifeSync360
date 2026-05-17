import os
import datetime
import hashlib
import uuid
import json as _json
from datetime import timezone
import jwt
import redis
import boto3
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
JWT_SECRET          = os.environ.get('JWT_SECRET', 'dev-jwt-secret-lifesync360-32bytes!!')
USE_MOCK            = os.environ.get('USE_MOCK', 'true').lower() != 'false'
PROFILE_SYNC_LAMBDA  = os.environ.get('PROFILE_SYNC_LAMBDA', '')
ONPREM_QUERY_LAMBDA  = os.environ.get('ONPREM_QUERY_LAMBDA', '')
AWS_REGION           = os.environ.get('AWS_REGION', 'ap-northeast-2')

# mock_data는 항상 import (인증 + USE_MOCK 분기 둘 다에서 사용)
from mock_data import (
    MOCK_USERS, MOCK_RECOMMENDATIONS, PRODUCTS_MAP, get_mock_health,
    get_mock_upgrade_actions, MOCK_MY_PRODUCTS, MOCK_CONSENTED_KEYS,
    get_mock_campaigns,
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
    {
        'key':   'BANK',
        'label': 'LS 은행 데이터 활용 동의',
        'icon':  '🏦',
        'desc':  '예금·적금·대출·연금 거래 내역을 분석해 자산 흐름에 맞는 금융 상품을 추천드립니다.',
        'scope': '계좌 잔액 · 거래 패턴 · 신용 등급',
    },
    {
        'key':   'CARD',
        'label': 'LS 카드 데이터 활용 동의',
        'icon':  '💳',
        'desc':  '카드 사용 카테고리와 포인트 적립 패턴을 분석해 라이프스타일 맞춤 혜택을 제안드립니다.',
        'scope': '결제 카테고리 · 사용 금액 · 포인트 적립/사용',
    },
    {
        'key':   'INSURANCE',
        'label': 'LS 보험 데이터 활용 동의',
        'icon':  '🛡️',
        'desc':  '보유 보험과 보장 공백을 분석해 필요한 보장을 보완할 보험 상품을 추천드립니다.',
        'scope': '보험 종목 · 보장 한도 · 만기 정보',
    },
    {
        'key':   'SECURITIES',
        'label': 'LS 증권 데이터 활용 동의',
        'icon':  '📈',
        'desc':  '투자 성향과 보유 종목을 기반으로 ETF·펀드·연금 등 투자 상품을 추천드립니다.',
        'scope': '포트폴리오 · 거래 패턴 · 위험 성향',
    },
    {
        'key':   'ONLINE_INS',
        'label': 'LS 다이렉트보험 데이터 활용 동의',
        'icon':  '📱',
        'desc':  '비대면 가입 이력 기반으로 모바일 간편 보험 상품을 우선 추천드립니다.',
        'scope': '온라인 가입 이력 · 견적 조회 · 클릭 패턴',
    },
    {
        'key':   'HEALTHCARE',
        'label': 'LS 헬스케어 데이터 활용 동의',
        'icon':  '💪',
        'desc':  '건강검진 결과와 측정 데이터로 건강 점수 산출 및 맞춤 헬스·웰니스 프로그램을 제공합니다.',
        'scope': '검진 결과 · 건강 지표 · 운동/식단 기록',
    },
    {
        'key':   'HOSPITAL',
        'label': 'LS 협력병원 데이터 활용 동의',
        'icon':  '🏥',
        'desc':  '진료 기록을 기반으로 화상진료·맞춤 보험·건강관리 서비스를 연결해 드립니다.',
        'scope': '진료/처방 이력 · 예약 정보',
    },
    {
        'key':   'WEARABLE',
        'label': '웨어러블 기기 데이터 활용 동의',
        'icon':  '⌚',
        'desc':  '심박수·걸음수·수면 데이터를 실시간 분석해 동적 건강 점수와 알림을 제공합니다.',
        'scope': '심박/혈압/SpO2 · 걸음수 · 수면 패턴',
    },
]

GRADE_SCORE_MAP = {
    'VIP':    90,
    'GOLD':   80,
    'SILVER': 70,
    'BASIC':  60,
    'CARE':    0,
}

# Service-DB 등급 체계: VIP > GOLD > SILVER > BASIC, CARE는 건강 특화
GRADE_BENEFITS = {
    'VIP': {'color': 'vip', 'desc': '최상위 고객 전용 혜택', 'benefits': [
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

def _call_onprem(action, **kwargs):
    """온프레미스 조회 Lambda 호출 — Control Node 경유"""
    if not ONPREM_QUERY_LAMBDA:
        raise RuntimeError('ONPREM_QUERY_LAMBDA 환경변수 미설정')
    resp   = _get_lambda().invoke(
        FunctionName=ONPREM_QUERY_LAMBDA,
        InvocationType='RequestResponse',
        Payload=_json.dumps({'action': action, **kwargs}),
    )
    result = _json.loads(resp['Payload'].read())
    status = result.get('statusCode', 200)
    body   = _json.loads(result['body']) if isinstance(result.get('body'), str) else result
    if status not in (200,):
        raise ValueError(body.get('error') or body.get('detail') or '온프레미스 오류')
    return body


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
    # 임시: Lambda 미배포 검증용 — 인증만 Mock 강제
    user = list(MOCK_USERS.values())[0]
    token = make_jwt(user['ls_user_id'], user['global_id'])
    return jsonify({'token': token, 'ls_user_id': user['ls_user_id']})


@app.route('/api/login', methods=['POST'])
def api_login():
    # 임시: Lambda 미배포 검증용 — 인증만 Mock 강제
    data     = request.get_json() or {}
    email    = data.get('email', '')
    password = data.get('password', '')

    user = MOCK_USERS.get(email)
    if not user or hashlib.sha256(password.encode('utf-8')).hexdigest() != user['password_hash']:
        return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
    token = make_jwt(user['ls_user_id'], user['global_id'])
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
                # 인구통계 (customer_360_profile)
                'gender':        user.get('gender'),
                'age_band':      user.get('age_band'),
                'region':        user.get('region'),
                'income_grade':  user.get('income_grade'),
                'asset_grade':   user.get('asset_grade'),
                'wearable_flag': user.get('wearable_flag'),
                # 마스터 (master_customer)
                'customer_status':  user.get('customer_status'),
                'vip_grade':        user.get('vip_grade'),
                'customer_type':    user.get('customer_type'),
                'first_created_dt': user.get('first_created_dt'),
                'last_login_dt':    user.get('last_login_dt'),
            })

        # Mock 유저 fallback 준비 (Lambda 미배포 검증용)
        _mock_user = next((u for u in MOCK_USERS.values() if u['ls_user_id'] == payload['sub']), None)

        login_email = None
        global_id   = payload['gid']
        try:
            user = _call_onprem('get_user', ls_user_id=payload['sub'])
            login_email = user.get('login_email')
            global_id   = user.get('global_id', global_id)
        except Exception:
            if _mock_user:
                login_email = _mock_user.get('email')

        grade = None
        try:
            item  = get_dynamo_table().get_item(Key={'global_id': global_id}).get('Item', {})
            grade = item.get('dynamic_grade')
        except Exception:
            pass

        onprem = None
        try:
            onprem = _call_onprem('get_all', global_id=global_id)
        except Exception:
            pass

        consents = onprem.get('consents', []) if onprem else []
        profile  = ((onprem or {}).get('customer') or {}).get('profile') or {}

        name = None
        try:
            pii  = _call_onprem('get_pii', global_id=global_id)
            name = pii.get('name')
        except Exception:
            if _mock_user:
                name = _mock_user.get('name')

        return jsonify({
            'ls_user_id': payload['sub'],
            'global_id':  global_id,
            'name':       name,
            'grade':      grade,
            'email':      login_email,
            'consents':   consents,
            'profile':    profile,
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
    try:
        _call_onprem('save_consent', global_id=payload['gid'], consents=consents)
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
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

    # product_id 없는 이벤트(tab_click 등) 또는 Aurora 미설정 환경 안전 처리
    if not product_id:
        return jsonify({'status': 'ok'})

    try:
        db = get_db()
        try:
            with db.cursor() as cur:
                if event_type == 'recommendation_click':
                    cur.execute(
                        'UPDATE customer_recommend_history SET clicked_flag = %s '
                        'WHERE global_id = %s AND product_id = %s AND clicked_flag = %s LIMIT 1',
                        ('Y', global_id, product_id, 'N')
                    )
                elif event_type == 'purchased':
                    cur.execute(
                        'UPDATE customer_recommend_history SET purchased_flag = %s '
                        'WHERE global_id = %s AND product_id = %s AND purchased_flag = %s LIMIT 1',
                        ('Y', global_id, product_id, 'N')
                    )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return jsonify({'status': 'ok'})


@app.route('/api/recommendations')
def api_recommendations():
    """
    추천 흐름 (Service-DB recommend_rule + cross_sell_rule + results.csv NBA):
      ① DDB lifesync_customer_result → dynamic_grade / score / health / vip_prob / NBA
      ② Redis 캐시 hit → 즉시 반환 (TTL 6h, miss/fail 시 Aurora fallback)
      ③ recommend_rule 매칭 (target_grade + score 범위 + vip_required + health_min_score)
         + NBA(next_best_action) 매칭된 action_code 우선 정렬
      ④ cross_sell_rule 보강 (첫 base_category → target_category 3개 추가)
      ⑤ category별 product_master 매칭 (각 카테고리당 top 2, 합쳐서 LIMIT 20)
      ⑥ customer_recommend_history INSERT + Redis 캐시 갱신
    """
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    if USE_MOCK:
        # 구 그룹 형식 (MOCK_RECOMMENDATIONS = [{id,name,products:[{id,name,...}]}, ...]) →
        # 신규 형식 {meta, products[flat]} 변환 (프론트 호환)
        flat = []
        for rec in MOCK_RECOMMENDATIONS:
            for p in rec.get('products', []):
                flat.append({
                    'product_id'   : p.get('id'),
                    'product_code' : p.get('id'),
                    'product_name' : p.get('name'),
                    'description'  : p.get('desc', ''),
                    'category_code': (rec.get('key') or '').upper(),
                    'category_name': rec.get('name', ''),
                    'company_code' : (rec.get('key') or '').upper(),
                    'company_name' : rec.get('name', ''),
                    'risk_level'   : p.get('tag', ''),
                    'target_grade' : p.get('type', ''),
                    'priority_rank': 0,
                })
        return jsonify({
            'meta'    : {'grade': 'VIP', 'score': 90.0, 'health': 88.0,
                         'vip_prob': 0.85, 'next_best_action': 'PB'},
            'products': flat[:20],
        })

    global_id = payload['gid']

    # ① DDB
    grade, dynamic_score, health_score, vip_prob, nba = 'BASIC', 0.0, 0.0, 0.0, None
    try:
        item = get_dynamo_table().get_item(Key={'global_id': global_id}).get('Item', {})
        grade         = item.get('dynamic_grade', 'BASIC')
        dynamic_score = float(item.get('dynamic_score') or 0)
        health_score  = float(item.get('health_score')  or 0)
        vip_prob      = float(item.get('vip_prob')      or 0)
        nba           = item.get('next_best_action')
    except Exception:
        pass

    # ② Redis cache (hit → 즉시 반환)
    cached_ids = None
    try:
        c = get_redis().get(f'rec:{global_id}')
        if c:
            cached_ids = _json.loads(c)
    except Exception:
        pass

    # NBA → recommend_rule.action_code 매핑 (results.csv 의 next_best_action 컬럼 기준)
    nba_to_action = {
        'RETENTION':         'RECOMMEND_HEALTH',
        'INSURANCE_UPSELL':  'RECOMMEND_INSURANCE',
        'HEALTH_SERVICE':    'RECOMMEND_HEALTH_INS',
        'HEALTH_INS':        'RECOMMEND_HEALTH_INS',
        'PB':                'RECOMMEND_PB',
        'WM':                'RECOMMEND_WM',
        'INVEST':            'RECOMMEND_INVEST',
        'SAVING':            'RECOMMEND_SAVING',
        'CARD':              'RECOMMEND_CARD',
        'LOAN':              'RECOMMEND_LOAN',
        'PENSION':           'RECOMMEND_PENSION',
        'WELLNESS':          'RECOMMEND_WELLNESS',
        'TELEMED':           'RECOMMEND_TELEMED',
    }
    target_action = nba_to_action.get(str(nba or '').upper())
    # vip_required 임계 — 운영 데이터 분포에 따라 환경변수로 조정 (results.csv 보면 0.5~0.58 분기)
    _vip_th = float(os.environ.get('VIP_PROB_THRESHOLD', '0.5'))
    vip_required_flag = 'Y' if vip_prob >= _vip_th else 'N'

    db = get_db()
    try:
        with db.cursor() as cur:
            if cached_ids:
                placeholders = ', '.join(['%s'] * len(cached_ids))
                cur.execute(f"""
                    SELECT p.product_id, p.product_code, p.product_name, p.description,
                           p.target_grade, p.risk_level, p.priority_rank,
                           c.company_code, c.company_name, cat.category_code, cat.category_name
                    FROM product_master p
                    JOIN company_master   c   ON p.company_id  = c.company_id
                    JOIN category_master  cat ON p.category_id = cat.category_id
                    WHERE p.product_id IN ({placeholders}) AND p.active_flag = 'Y'
                    ORDER BY p.priority_rank
                """, cached_ids)
                products = cur.fetchall()
                rule_action_by_cat = {}
            else:
                # ③ recommend_rule 매칭 — NBA 매칭된 action_code 우선 정렬
                cur.execute("""
                    SELECT category_code, action_code, priority_rank
                    FROM recommend_rule
                    WHERE active_flag = 'Y'
                      AND target_grade = %s
                      AND %s BETWEEN min_score AND max_score
                      AND (vip_required = 'N' OR vip_required = %s)
                      AND (health_min_score IS NULL OR %s >= health_min_score)
                    ORDER BY
                      CASE WHEN action_code = %s THEN 0 ELSE 1 END,
                      priority_rank
                """, (grade, dynamic_score, vip_required_flag, health_score, target_action or ''))
                rule_rows = cur.fetchall()
                rule_action_by_cat = {r['category_code']: r['action_code'] for r in rule_rows}

                # ④ cross_sell_rule 보강 — 첫 category → target_category 3개
                cross_cats = []
                if rule_rows:
                    cur.execute("""
                        SELECT target_category FROM cross_sell_rule
                        WHERE base_category = %s AND active_flag = 'Y'
                        ORDER BY priority_rank LIMIT 3
                    """, (rule_rows[0]['category_code'],))
                    cross_cats = [r['target_category'] for r in cur.fetchall()]

                # 중복 제거 (순서 유지)
                seen = set()
                cat_list = []
                for c in [r['category_code'] for r in rule_rows] + cross_cats:
                    if c not in seen:
                        seen.add(c); cat_list.append(c)
                # cross_sell 로 추가된 카테고리 action_code 채움
                for c in cross_cats:
                    rule_action_by_cat.setdefault(c, 'RECOMMEND_CROSS_SELL')

                # ⑤ category별 product_master — 각 카테고리당 top 2, 전체 LIMIT 20
                products = []
                if cat_list:
                    cat_placeholders = ', '.join(['%s'] * len(cat_list))
                    cur.execute(f"""
                        SELECT p.product_id, p.product_code, p.product_name, p.description,
                               p.target_grade, p.risk_level, p.priority_rank,
                               c.company_code, c.company_name, cat.category_code, cat.category_name,
                               ROW_NUMBER() OVER (PARTITION BY cat.category_code ORDER BY p.priority_rank) AS rn
                        FROM product_master p
                        JOIN company_master   c   ON p.company_id  = c.company_id
                        JOIN category_master  cat ON p.category_id = cat.category_id
                        WHERE p.active_flag = 'Y'
                          AND cat.category_code IN ({cat_placeholders})
                          AND p.min_score <= %s
                        ORDER BY FIELD(cat.category_code, {cat_placeholders}), p.priority_rank
                    """, cat_list + [dynamic_score] + cat_list)
                    for r in cur.fetchall():
                        if r['rn'] <= 2:
                            r.pop('rn', None)
                            products.append(r)
                        if len(products) >= 20:
                            break

                # fallback: rule 매칭 0건 → score 기반 단순 매칭 (기존 로직 유지)
                if not products:
                    min_score = GRADE_SCORE_MAP.get(grade, 60)
                    cur.execute("""
                        SELECT p.product_id, p.product_code, p.product_name, p.description,
                               p.target_grade, p.risk_level, p.priority_rank,
                               c.company_code, c.company_name, cat.category_code, cat.category_name
                        FROM product_master p
                        JOIN company_master   c   ON p.company_id  = c.company_id
                        JOIN category_master  cat ON p.category_id = cat.category_id
                        WHERE p.active_flag = 'Y' AND p.min_score <= %s
                        ORDER BY p.priority_rank LIMIT 20
                    """, (min_score,))
                    products = cur.fetchall()

            # ⑥ history INSERT + Redis 캐시 갱신 (cache hit 시 INSERT만)
            now = datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            for p in products:
                action = rule_action_by_cat.get(p.get('category_code'), 'RECOMMEND_DASHBOARD')
                cur.execute(
                    '''INSERT INTO customer_recommend_history
                       (global_id, product_id, dynamic_score, dynamic_grade, action_code, recommended_at)
                       VALUES (%s, %s, %s, %s, %s, %s)''',
                    (global_id, p['product_id'], dynamic_score, grade, action, now)
                )
        db.commit()
    finally:
        db.close()

    if not cached_ids and products:
        try:
            r = get_redis()
            r.setex(f'rec:{global_id}', 21600, _json.dumps([p['product_id'] for p in products]))
        except Exception:
            pass

    # nba/grade/score 메타 같이 반환 (프론트 헤더 표기용)
    return jsonify({
        'meta'    : {'grade': grade, 'score': dynamic_score, 'health': health_score,
                     'vip_prob': vip_prob, 'next_best_action': nba},
        'products': products,
    })


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

    if company_key:
        try:
            consent_data = _call_onprem('get_consent', global_id=global_id)
        except ValueError:
            return jsonify({'error': 'consent_check_failed'}), 500
        consents = {c['domain']: c.get('consent_flag') for c in consent_data.get('consents', [])}
        if consents.get(company_key) != 'Y':
            return jsonify({'error': 'consent_required'}), 403

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


@app.route('/api/campaigns')
def api_campaigns():
    """등급별 활성 캠페인 배너"""
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    grade = 'BASIC'
    if USE_MOCK:
        user = next((u for u in MOCK_USERS.values() if u['ls_user_id'] == payload['sub']), None)
        if user:
            grade = user.get('grade', 'BASIC')
        return jsonify(get_mock_campaigns(grade))

    try:
        item  = get_dynamo_table().get_item(Key={'global_id': payload['gid']}).get('Item', {})
        grade = item.get('dynamic_grade', 'BASIC')
    except Exception:
        pass

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT campaign_name, banner_title, banner_desc, start_date, end_date
                FROM campaign_master
                WHERE target_grade = %s AND active_flag = 'Y'
                  AND end_date >= CURDATE()
                ORDER BY start_date DESC
                LIMIT 5
            """, (grade,))
            rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        db.close()
    return jsonify([
        {'icon': '🎯', 'title': r['campaign_name'], 'desc': r['banner_desc'],
         'period': f"{r['start_date']} ~ {r['end_date']}", 'cta': '자세히 보기'}
        for r in rows
    ])


@app.route('/health')
def health():
    return {
        'status': 'ok',
        'jwt_from_env': bool(os.environ.get('JWT_SECRET')),
        'jwt_len':      len(JWT_SECRET),
        'jwt_prefix':   JWT_SECRET[:8],
        'use_mock':     USE_MOCK,
        'dynamo_table': os.environ.get('DYNAMO_TABLE', 'NOT_SET'),
    }


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
        'next_best_action': item.get('next_best_action'),
        'update_time':      item.get('update_time'),
    })


# ── 페이지 ────────────────────────────────────────────
@app.route('/settings')
def settings():
    return render_template('settings.html',
        grade_benefits=GRADE_BENEFITS,
        consents=CONSENTS,
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


@app.route('/product/<product_code>/apply')
def product_apply(product_code):
    """상품 신청 페이지 — product.html '신청하기' 클릭 시 이동."""
    if USE_MOCK:
        m = PRODUCTS_MAP.get(product_code)
        if not m:
            return redirect(url_for('dashboard'))
        item = {'id': product_code, 'name': m['name'], 'desc': m.get('desc', ''),
                'category': m.get('category', ''), 'product_id': None}
        return render_template('apply.html', item=item)

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT p.product_id, p.product_code, p.product_name, p.description,
                       c.company_code, c.company_name, cat.category_name
                FROM product_master p
                JOIN company_master   c   ON p.company_id  = c.company_id
                JOIN category_master  cat ON p.category_id = cat.category_id
                WHERE p.product_code = %s AND p.active_flag = 'Y'
            """, (product_code,))
            row = cur.fetchone()
    finally:
        db.close()

    if not row:
        return redirect(url_for('dashboard'))
    item = {
        'id'        : row['product_code'],
        'product_id': row['product_id'],
        'name'      : row['product_name'],
        'desc'      : row['description'] or '',
        'category'  : row['category_name'],
    }
    return render_template('apply.html', item=item)


@app.route('/api/product/<product_code>/apply', methods=['POST'])
def api_product_apply(product_code):
    """상품 신청 처리 — customer_product_application 테이블 INSERT."""
    auth  = request.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    try:
        payload = decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid token'}), 401

    data = request.get_json() or {}
    applicant_name  = (data.get('applicant_name')  or '').strip()
    applicant_phone = (data.get('applicant_phone') or '').strip()
    if not applicant_name or not applicant_phone:
        return jsonify({'error': '이름과 휴대전화는 필수입니다.'}), 400

    application_id = f"APP-{datetime.datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{payload['sub'][-6:]}"

    if USE_MOCK:
        return jsonify({'status': 'ok', 'application_id': application_id})

    db = get_db()
    try:
        with db.cursor() as cur:
            # product_id 조회 (apply.html 이 보내준 product_id 가 null/모를 수도 있어 안전하게 재조회)
            cur.execute(
                "SELECT product_id FROM product_master WHERE product_code = %s AND active_flag = 'Y'",
                (product_code,),
            )
            row = cur.fetchone()
            product_id = row['product_id'] if row else None
            if not product_id:
                return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404

            # 신청 INSERT — 테이블이 없으면 CREATE TABLE IF NOT EXISTS 로 자동 생성
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_product_application (
                    application_id   VARCHAR(40) PRIMARY KEY,
                    global_id        VARCHAR(20) NOT NULL,
                    ls_user_id       VARCHAR(40),
                    product_id       BIGINT NOT NULL,
                    product_code     VARCHAR(50) NOT NULL,
                    applicant_name   VARCHAR(40) NOT NULL,
                    applicant_phone  VARCHAR(20) NOT NULL,
                    applicant_email  VARCHAR(100),
                    apply_amount     VARCHAR(100),
                    contact_time     VARCHAR(20),
                    memo             TEXT,
                    agree_marketing  CHAR(1) DEFAULT 'N',
                    status           VARCHAR(20) DEFAULT 'RECEIVED',
                    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_global_id (global_id),
                    INDEX idx_product_id (product_id)
                ) ENGINE=InnoDB CHARSET=utf8mb4
            """)
            cur.execute("""
                INSERT INTO customer_product_application
                  (application_id, global_id, ls_user_id, product_id, product_code,
                   applicant_name, applicant_phone, applicant_email, apply_amount,
                   contact_time, memo, agree_marketing)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                application_id, payload['gid'], payload['sub'], product_id, product_code,
                applicant_name, applicant_phone, data.get('applicant_email') or None,
                data.get('apply_amount') or None, data.get('contact_time') or 'any',
                data.get('memo') or None, 'Y' if data.get('agree_marketing') else 'N',
            ))
        db.commit()
    except Exception as e:
        return jsonify({'error': f'신청 처리 실패: {str(e)}'}), 500
    finally:
        db.close()

    return jsonify({'status': 'ok', 'application_id': application_id})


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

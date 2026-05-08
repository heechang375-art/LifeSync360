"""
GCP Vertex AI 분석 결과 수신 Lambda
트리거: API Gateway POST /ingest

역할:
  1. DynamoDB PUT  — 실시간 스코어 저장 (대시보드용)
  2. Aurora UPDATE — 등급 변경 시 users.grade 반영
  3. Redis SET     — 고객별 추천 product_id 목록 캐싱 (TTL 24h)
                     상품 상세 데이터는 Aurora가 source of truth
"""
import json
import os
import time

import boto3
import pymysql
import redis

DYNAMO_TABLE = os.environ['DYNAMO_TABLE']
AURORA_HOST  = os.environ['AURORA_HOST']
DB_USER      = os.environ['DB_USER']
DB_PASS      = os.environ['DB_PASS']
DB_NAME      = os.environ.get('DB_NAME', 'lifesync')
REDIS_HOST   = os.environ['REDIS_HOST']
REDIS_PORT   = int(os.environ.get('REDIS_PORT', '6379'))
TTL_DAYS     = int(os.environ.get('TTL_DAYS', '30'))
REC_TTL_SEC  = int(os.environ.get('REC_TTL_SEC', '86400'))  # 추천 캐시 TTL: 24h
AWS_REGION   = os.environ.get('AWS_REGION', 'ap-northeast-2')

REQUIRED_FIELDS = {'global_id', 'dynamic_score', 'dynamic_grade', 'health_score', 'next_best_action'}

GRADE_MAP = {
    'VIP':    'PLATINUM',
    'GOLD':   'GOLD',
    'SILVER': 'SILVER',
    'BRONZE': 'BRONZE',
    'BASIC':  'BASIC',
}

GRADE_LEVELS = ['BASIC', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM']

_dynamodb = None
_redis    = None


def _get_dynamo_table():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    return _dynamodb.Table(DYNAMO_TABLE)


def _get_redis():
    global _redis
    if _redis is None:
        _redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    return _redis


def _get_db():
    return pymysql.connect(
        host=AURORA_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def _fetch_recommended_ids(cur, aurora_grade):
    """등급 + 추천룰 기준으로 추천 product_id 목록만 조회"""
    idx = GRADE_LEVELS.index(aurora_grade)
    accessible = GRADE_LEVELS[:idx + 1]
    placeholders = ', '.join(['%s'] * len(accessible))
    cur.execute(f"""
        SELECT pm.product_id
        FROM product_master pm
        LEFT JOIN recommend_rule rr
            ON pm.product_id = rr.product_id AND rr.condition_key = 'ai_condition'
        WHERE pm.is_active = 1
          AND pm.min_grade IN ({placeholders})
        ORDER BY rr.priority DESC, pm.product_id
        LIMIT 50
    """, accessible)
    return [row['product_id'] for row in cur.fetchall()]


def _resp(status, body):
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False),
    }


def handler(event, context):
    # 1. 페이로드 파싱
    try:
        body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return _resp(400, {'error': '잘못된 JSON 형식'})

    missing = REQUIRED_FIELDS - body.keys()
    if missing:
        return _resp(400, {'error': f'필수 필드 누락: {sorted(missing)}'})

    dynamic_grade = body['dynamic_grade']
    if dynamic_grade not in GRADE_MAP:
        return _resp(400, {'error': f'알 수 없는 dynamic_grade: {dynamic_grade}', 'allowed': list(GRADE_MAP)})

    global_id    = body['global_id']
    aurora_grade = GRADE_MAP[dynamic_grade]

    # 2. DynamoDB PUT — 스코어 저장
    _get_dynamo_table().put_item(Item={
        'global_id':        global_id,
        'dynamic_score':    str(body['dynamic_score']),
        'dynamic_grade':    dynamic_grade,
        'health_score':     str(body['health_score']),
        'fin_score':        str(body.get('fin_score', '')),
        'behavior_score':   str(body.get('behavior_score', '')),
        'next_best_action': body['next_best_action'],
        'vip_prob':         str(body.get('vip_prob', '')),
        'signup_prob':      str(body.get('signup_prob', '')),
        'rec_prob':         str(body.get('rec_prob', '')),
        'update_time':      body.get('update_time', ''),
        'source':           'GCP',
        'ttl':              int(time.time()) + 86400 * TTL_DAYS,
    })

    # 3. Aurora: grade 업데이트 + 추천 product_id 조회
    db = _get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'UPDATE users SET grade = %s WHERE global_id = %s AND grade != %s',
                (aurora_grade, global_id, aurora_grade),
            )
            db.commit()
            product_ids = _fetch_recommended_ids(cur, aurora_grade)
    finally:
        db.close()

    # 4. Redis SETEX — product_id 목록만 캐싱 (상세 데이터는 Aurora에서 직접)
    _get_redis().setex(f'rec:{global_id}', REC_TTL_SEC, json.dumps(product_ids))

    return _resp(200, {'status': 'ok', 'global_id': global_id, 'cached_count': len(product_ids)})

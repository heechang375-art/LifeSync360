"""
고객 프로필 동기화 Lambda
트리거: 플랫폼 로그인 시 Flask app에서 boto3 invoke (RequestResponse)

역할:
  1. On-Prem Private API /internal/identity 호출 → global_id 조회
     (affiliate_customer_id = 플랫폼 가입 이메일, company_id = 기본 'bank')
  2. Aurora users.global_id 업데이트 (변경 시에만)
  3. global_id 반환
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pymysql

PRIVATE_API_URL = os.environ['PRIVATE_API_URL']
AURORA_HOST     = os.environ['AURORA_HOST']
DB_USER         = os.environ['DB_USER']
DB_PASS         = os.environ['DB_PASS']
DB_NAME         = os.environ.get('DB_NAME', 'lifesync')
DEFAULT_COMPANY = os.environ.get('DEFAULT_COMPANY_ID', 'bank')


def _get_db():
    return pymysql.connect(
        host=AURORA_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def _fetch_global_id(email, company_id):
    encoded = urllib.parse.quote(email, safe='')
    url = f'{PRIVATE_API_URL}/internal/identity/{encoded}?company_id={company_id}'
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read())['global_id']


def _resp(status, body):
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False),
    }


def handler(event, context):
    body = json.loads(event['body']) if 'body' in event else event

    ls_user_id = body.get('ls_user_id')
    email      = body.get('email')
    company_id = body.get('company_id', DEFAULT_COMPANY)

    if not ls_user_id or not email:
        return _resp(400, {'error': '필수 필드 누락: ls_user_id, email'})

    # 1. On-Prem Private API에서 global_id 조회
    try:
        global_id = _fetch_global_id(email, company_id)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return _resp(404, {'error': f'계열사 ID 매핑 없음: email={email}, company_id={company_id}'})
        return _resp(502, {'error': f'Private API 오류: HTTP {e.code}'})
    except Exception as e:
        return _resp(502, {'error': f'Private API 연결 실패: {str(e)}'})

    # 2. Aurora users.global_id 업데이트 (이미 같은 값이면 스킵)
    db = _get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'UPDATE users SET global_id = %s WHERE ls_user_id = %s AND (global_id IS NULL OR global_id != %s)',
                (global_id, ls_user_id, global_id),
            )
            db.commit()
    finally:
        db.close()

    return _resp(200, {'global_id': global_id, 'ls_user_id': ls_user_id})

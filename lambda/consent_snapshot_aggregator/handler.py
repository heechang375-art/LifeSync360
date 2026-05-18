"""
consent_snapshot_aggregator — 동의 스냅샷 일배치 적재 Lambda

매일 KST 03:00 (UTC 18:00) EventBridge cron 트리거.
온프레 consent 테이블 → S3 lifesync-raw/consent/dt=YYYY-MM-DD/{global_id}.json

흐름:
  1. onprem_customer_query Lambda invoke (action='list_consent_page', page=0~N)
     - 한 응답에 user 1만 명 (consents 묶음)
     - 1M 가입자 = 약 100 페이지
  2. global_id 별 {global_id, ls_user_id, user_status, consents: [...]} dict 생성
  3. boto3 s3.put_object — user 1명당 1 객체
     - ThreadPoolExecutor 동시 100 PUT
     - 총 1M 객체 ≈ 10~15분
  4. admin 은 `s3.get_object(Bucket=lifesync-raw, Key='consent/dt=YYYY-MM-DD/{gid}.json')` 으로 조회

환경변수:
  AWS_REGION                  (Lambda runtime 자동)
  ONPREM_QUERY_LAMBDA         — onprem_customer_query Lambda 함수명
  LIFESYNC_RAW_S3_BUCKET      — lifesync-raw 버킷 이름
  CONSENT_PAGE_SIZE           — 기본 10000
  CONSENT_MAX_PAGES           — 안전 상한 (기본 200, 약 2M 가입자)
  CONSENT_PUT_CONCURRENCY     — S3 PutObject 동시성 (기본 100)
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import boto3

REGION                  = os.environ.get('AWS_REGION', 'ap-northeast-2')
ONPREM_QUERY_LAMBDA     = os.environ.get('ONPREM_QUERY_LAMBDA', '')
S3_BUCKET               = os.environ['LIFESYNC_RAW_S3_BUCKET']
PAGE_SIZE               = int(os.environ.get('CONSENT_PAGE_SIZE',       '10000'))
MAX_PAGES               = int(os.environ.get('CONSENT_MAX_PAGES',         '200'))
PUT_CONCURRENCY         = int(os.environ.get('CONSENT_PUT_CONCURRENCY',   '100'))

KST = timezone(timedelta(hours=9))

_lambda = boto3.client('lambda', region_name=REGION)
_s3     = boto3.client('s3',     region_name=REGION)


def _fetch_consent_page(page):
    """onprem_customer_query Lambda 경유로 PrivateAPI /internal/consent/list-all 호출."""
    resp = _lambda.invoke(
        FunctionName  = ONPREM_QUERY_LAMBDA,
        InvocationType= 'RequestResponse',
        Payload       = json.dumps({'action': 'list_consent_page', 'page': page, 'size': PAGE_SIZE}).encode(),
    )
    envelope = json.loads(resp['Payload'].read())
    if envelope.get('statusCode') != 200:
        return []
    body = json.loads(envelope['body']) if isinstance(envelope.get('body'), str) else envelope.get('body', {})
    return body.get('items') or []


def _put_one(prefix, item, snapshot_dt):
    """user 1명 동의 정보를 S3 객체 1개로 적재."""
    payload = {
        'global_id':    item.get('global_id'),
        'ls_user_id':   item.get('ls_user_id'),
        'user_status':  item.get('user_status'),
        'consents':     item.get('consents') or [],
        'snapshot_dt':  snapshot_dt,
    }
    _s3.put_object(
        Bucket      = S3_BUCKET,
        Key         = f"{prefix}{item['global_id']}.json",
        Body        = json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        ContentType = 'application/json',
    )


def handler(event, context):
    today  = datetime.now(KST).date().isoformat()
    prefix = f'consent/dt={today}/'
    total  = 0

    with ThreadPoolExecutor(max_workers=PUT_CONCURRENCY) as pool:
        for page in range(MAX_PAGES):
            items = _fetch_consent_page(page)
            if not items:
                break
            # 한 페이지 안 모든 user 동시 PUT (max 100 concurrency)
            list(pool.map(lambda it: _put_one(prefix, it, today), items))
            total += len(items)
            if len(items) < PAGE_SIZE:
                break    # 마지막 페이지

    return {
        'statusCode': 200,
        'headers'   : {'Content-Type': 'application/json'},
        'body'      : json.dumps({
            'date':      today,
            's3_prefix': f's3://{S3_BUCKET}/{prefix}',
            'total':     total,
        }, ensure_ascii=False),
    }

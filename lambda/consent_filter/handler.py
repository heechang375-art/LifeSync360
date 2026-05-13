"""
동의 고객 필터링 Lambda
트리거: EventBridge Scheduler (Glue/EMR 실행 전) 또는 수동 invoke

역할:
  1. On-Prem MySQL(lifesync_onprem) consent 테이블 조회
     → consent_yn = 'Y' 고객을 consent_key별 피벗하여 추출
  2. S3에 gzip CSV 저장
     → s3://<OUTPUT_BUCKET>/<OUTPUT_PREFIX><YYYYMMDD>/consented_customers.csv.gz
  3. (선택) Glue Job 시작  — --consent_s3_path 인자로 S3 경로 전달
  4. (선택) EMR Step 추가  — emr_cluster_id + emr_step_args 이벤트 파라미터

네트워크 전제:
  이 Lambda는 TGW를 통해 온프레미스(192.168.56.x)에 접근 가능한 VPC Subnet에 배치되어야 함.
  Lambda SG: TCP 3306 아웃바운드 허용 (→ 온프레미스 MySQL)
"""
import csv
import gzip
import logging
import os
from datetime import datetime, timezone

import boto3
import pymysql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AUTH_DB_HOST  = os.environ['AUTH_DB_HOST']
AUTH_DB_USER  = os.environ['AUTH_DB_USER']
AUTH_DB_PASS  = os.environ['AUTH_DB_PASS']
AUTH_DB_NAME  = os.environ.get('AUTH_DB_NAME', 'lifesync_onprem')
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX', 'consent-filter/')
GLUE_JOB_NAME = os.environ.get('GLUE_JOB_NAME', '')
AWS_REGION    = os.environ.get('AWS_REGION', 'ap-northeast-2')
FETCH_BATCH   = int(os.environ.get('FETCH_BATCH', '5000'))

CONSENT_KEYS = ['BANK', 'CARD', 'SECURITIES', 'INSURANCE', 'HEALTHCARE', 'HOSPITAL', 'WEARABLE']

_s3   = None
_glue = None
_emr  = None


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client('s3', region_name=AWS_REGION)
    return _s3


def _get_glue():
    global _glue
    if _glue is None:
        _glue = boto3.client('glue', region_name=AWS_REGION)
    return _glue


def _get_emr():
    global _emr
    if _emr is None:
        _emr = boto3.client('emr', region_name=AWS_REGION)
    return _emr


def _get_db():
    return pymysql.connect(
        host=AUTH_DB_HOST,
        user=AUTH_DB_USER,
        password=AUTH_DB_PASS,
        database=AUTH_DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


def _build_pivot_sql(keys):
    """domain별 Y/N 피벗 쿼리 생성. 1개 이상 동의한 고객만 반환."""
    cases = ',\n    '.join(
        f"MAX(CASE WHEN domain = '{k}' AND consent_flag = 'Y' THEN 1 ELSE 0 END) AS `{k}`"
        for k in keys
    )
    return f"""
        SELECT
            global_customer_id AS global_id,
            {cases}
        FROM consent
        GROUP BY global_customer_id
        HAVING SUM(consent_flag = 'Y') > 0
        ORDER BY global_customer_id
    """


def _query_and_write_csv(keys, tmp_path):
    """DB 쿼리 결과를 gzip CSV로 /tmp에 기록. 추출된 행 수 반환.

    SSDictCursor(서버사이드 커서)로 결과를 스트리밍하여
    100만 건 이상 처리 시에도 Lambda 메모리 초과 방지.
    """
    row_count = 0
    db = _get_db()
    try:
        with db.cursor(pymysql.cursors.SSDictCursor) as cur:
            cur.execute(_build_pivot_sql(keys))
            fieldnames = ['global_id'] + keys

            with gzip.open(tmp_path, 'wt', encoding='utf-8', newline='') as gz:
                writer = csv.DictWriter(gz, fieldnames=fieldnames)
                writer.writeheader()

                while True:
                    rows = cur.fetchmany(FETCH_BATCH)
                    if not rows:
                        break
                    writer.writerows(rows)
                    row_count += len(rows)
                    logger.info("추출 중: 누적 %d건", row_count)
    finally:
        db.close()

    return row_count


def _start_glue(job_name, s3_uri, date_str, extra_args):
    args = {
        '--consent_s3_path': s3_uri,
        '--job_date':        date_str,
    }
    args.update(extra_args)
    resp = _get_glue().start_job_run(JobName=job_name, Arguments=args)
    run_id = resp['JobRunId']
    logger.info("Glue Job 시작: job=%s, run_id=%s", job_name, run_id)
    return run_id


def _add_emr_step(cluster_id, step_name, step_args, s3_uri):
    """EMR 클러스터에 Spark Step 추가. step_args 마지막에 --consent_s3_path 삽입."""
    full_args = list(step_args) + ['--consent_s3_path', s3_uri]
    resp = _get_emr().add_job_flow_steps(
        JobFlowId=cluster_id,
        Steps=[{
            'Name':            step_name,
            'ActionOnFailure': 'CONTINUE',
            'HadoopJarStep': {
                'Jar':  'command-runner.jar',
                'Args': full_args,
            },
        }],
    )
    step_id = resp['StepIds'][0]
    logger.info("EMR Step 추가: cluster=%s, step_id=%s", cluster_id, step_id)
    return step_id


def handler(event, context):
    """
    이벤트 파라미터 (모두 선택, 미지정 시 환경변수 사용):
      consent_keys  : list[str] — 추출할 동의 키 (기본: CONSENT_KEYS 전체)
      output_bucket : str       — S3 버킷
      output_prefix : str       — S3 키 프리픽스
      glue_job_name : str       — Glue Job 이름 (빈 문자열이면 미트리거)
      glue_extra_args : dict    — Glue Job 추가 인자 (예: {"--source": "daily"})
      emr_cluster_id  : str     — EMR 클러스터 ID (없으면 EMR 미사용)
      emr_step_name   : str     — EMR Step 이름 (기본: "LifeSync360 Analysis")
      emr_step_args   : list    — spark-submit 포함 전체 Step args
    """
    keys_to_export = event.get('consent_keys', CONSENT_KEYS)
    bucket         = event.get('output_bucket', OUTPUT_BUCKET)
    prefix         = event.get('output_prefix', OUTPUT_PREFIX)
    glue_job       = event.get('glue_job_name', GLUE_JOB_NAME)
    glue_extra     = event.get('glue_extra_args', {})
    emr_cluster_id = event.get('emr_cluster_id', '')
    emr_step_name  = event.get('emr_step_name', 'LifeSync360 Analysis')
    emr_step_args  = event.get('emr_step_args', [])

    # 알 수 없는 consent_key 방어
    unknown = set(keys_to_export) - set(CONSENT_KEYS)
    if unknown:
        raise ValueError(f"지원하지 않는 consent_key: {sorted(unknown)}")

    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    s3_key   = f"{prefix}{date_str}/consented_customers.csv.gz"
    s3_uri   = f"s3://{bucket}/{s3_key}"
    tmp_path = '/tmp/consented_customers.csv.gz'

    logger.info("동의 고객 필터링 시작 — keys=%s, 출력=%s", keys_to_export, s3_uri)

    # 1. DB 쿼리 → /tmp gzip CSV
    row_count = _query_and_write_csv(keys_to_export, tmp_path)
    logger.info("조회 완료: 동의 고객 %d명", row_count)

    if row_count == 0:
        logger.warning("동의 고객이 0명입니다. Glue/EMR 트리거를 건너뜁니다.")
        return {'statusCode': 200, 'consented_count': 0, 's3_uri': None,
                'glue_run_id': None, 'emr_step_id': None}

    # 2. S3 업로드
    _get_s3().upload_file(tmp_path, bucket, s3_key)
    logger.info("S3 업로드 완료: %s", s3_uri)

    # 3. Glue Job 트리거 (선택)
    glue_run_id = None
    if glue_job:
        glue_run_id = _start_glue(glue_job, s3_uri, date_str, glue_extra)

    # 4. EMR Step 추가 (선택)
    emr_step_id = None
    if emr_cluster_id and emr_step_args:
        emr_step_id = _add_emr_step(emr_cluster_id, emr_step_name, emr_step_args, s3_uri)

    return {
        'statusCode':     200,
        'consented_count': row_count,
        's3_uri':          s3_uri,
        'glue_run_id':     glue_run_id,
        'emr_step_id':     emr_step_id,
    }

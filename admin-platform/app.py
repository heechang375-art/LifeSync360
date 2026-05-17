import os
import functools

import boto3
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'admin-dev-secret-32bytes-lifesync!!')  # TODO: 운영 배포 시 env var로 교체

USE_MOCK             = os.environ.get('USE_MOCK', 'true').lower() != 'false'  # default true, 명시 'false'만 비Mock
ADMIN_USER           = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS           = os.environ.get('ADMIN_PASSWORD', 'admin1234')  # TODO: 운영 배포 시 env var로 교체
DYNAMO_TABLE         = os.environ.get('DYNAMO_TABLE', 'lifesync-scores')
DDB_SEGMENT_TABLE    = os.environ.get('DDB_SEGMENT_TABLE',    'analytics_segment_performance')
DDB_DEMOGRAPHIC_TABLE= os.environ.get('DDB_DEMOGRAPHIC_TABLE','analytics_demographic_summary')
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
        MOCK_PRODUCT_FUNNEL,
    )

# 신규 페이지에서 mock fallback 으로 사용 (USE_MOCK=true 일 때 항상 적재)
from mockup_data import (
    MOCKUP_KPI_TOP, MOCKUP_KPI_MID,
    MOCKUP_AWS_STATUS_DETAIL, MOCKUP_GCP_STATUS_DETAIL,
    MOCKUP_S3_INGESTION_BOX, MOCKUP_SIGNUP_BOX, MOCKUP_RECENT_UPLOADS,
    MOCKUP_DOMAIN_FLOW,
    MOCKUP_LAMBDA_METRICS, MOCKUP_GLUE_LAST_RUN, MOCKUP_NEXT_BATCH,
    MOCKUP_RECOMMEND_BY_CATEGORY, MOCKUP_RECOMMEND_BY_GRADE, MOCKUP_RECOMMEND_TOP10,
    MOCKUP_SCORE_DISTRIBUTION,
    MOCKUP_AGE_MODEL_RATIO, MOCKUP_RECOMMEND_TREND,
    MOCKUP_CLOUD_STATUS,
    MOCKUP_AI_KPI, MOCKUP_VERTEX_AI, MOCKUP_FEATURE_IMPORTANCE,
    MOCKUP_TGW, MOCKUP_VPN, MOCKUP_VPC_PEERING,
    MOCKUP_WEARABLE_REALTIME,
    MOCKUP_AFFILIATE_HEALTH, MOCKUP_BACKEND_SERVICES,
    MOCKUP_REDIS_PERSONALIZED, MOCKUP_CROSSSELL_LIST, MOCKUP_RECENT_ERRORS,
    MOCKUP_LOCAL_LAB,
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


# ── boto3 ping 헬퍼 (운영 모니터링·Cloud Status용) ──────────
_boto_clients = {}


def _boto(service):
    if service not in _boto_clients:
        _boto_clients[service] = boto3.client(service, region_name=AWS_REGION)
    return _boto_clients[service]


def _ping_cloud_status():
    """Cloud Status 카드 — AWS 리소스 6종 describe."""
    out = []
    try:
        clusters = _boto('rds').describe_db_clusters().get('DBClusters', [])
        ok = sum(1 for c in clusters if c.get('Status') == 'available')
        out.append({'service': 'AWS Aurora', 'state': 'UP' if ok else 'DOWN', 'note': f'{ok}/{len(clusters)} clusters available'})
    except Exception as e:
        out.append({'service': 'AWS Aurora', 'state': 'ERR', 'note': str(e)[:60]})
    try:
        tables = _boto('dynamodb').list_tables().get('TableNames', [])
        out.append({'service': 'AWS DynamoDB', 'state': 'UP', 'note': f'{len(tables)} tables'})
    except Exception as e:
        out.append({'service': 'AWS DynamoDB', 'state': 'ERR', 'note': str(e)[:60]})
    try:
        caches = _boto('elasticache').describe_cache_clusters().get('CacheClusters', [])
        ok = sum(1 for c in caches if c.get('CacheClusterStatus') == 'available')
        out.append({'service': 'AWS ElastiCache', 'state': 'UP' if ok else 'DOWN', 'note': f'{ok}/{len(caches)} clusters'})
    except Exception as e:
        out.append({'service': 'AWS ElastiCache', 'state': 'ERR', 'note': str(e)[:60]})
    try:
        clusters = _boto('ecs').list_clusters().get('clusterArns', [])
        out.append({'service': 'AWS ECS', 'state': 'UP' if clusters else 'DOWN', 'note': f'{len(clusters)} clusters'})
    except Exception as e:
        out.append({'service': 'AWS ECS', 'state': 'ERR', 'note': str(e)[:60]})
    try:
        lbs = _boto('elbv2').describe_load_balancers().get('LoadBalancers', [])
        ok = sum(1 for l in lbs if l.get('State', {}).get('Code') == 'active')
        out.append({'service': 'AWS ALB', 'state': 'UP' if ok else 'DOWN', 'note': f'{ok}/{len(lbs)} active'})
    except Exception as e:
        out.append({'service': 'AWS ALB', 'state': 'ERR', 'note': str(e)[:60]})
    try:
        buckets = _boto('s3').list_buckets().get('Buckets', [])
        out.append({'service': 'AWS S3', 'state': 'UP', 'note': f'{len(buckets)} buckets'})
    except Exception as e:
        out.append({'service': 'AWS S3', 'state': 'ERR', 'note': str(e)[:60]})
    return out


def _ping_s3_ingestion():
    """S3 Data Ingestion — raw bucket 적재 현황."""
    raw_bucket = os.environ.get('LIFESYNC_RAW_S3_BUCKET', '')
    if not raw_bucket:
        return {'raw_bucket_files': 0, 'today_ingested': 0, 'iot_count': 0,
                'last_upload': {}, 'failed_count': 0}
    from datetime import datetime, timezone
    today_prefix = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    try:
        s3 = _boto('s3')
        paginator = s3.get_paginator('list_objects_v2')
        total = today = iot = 0
        latest = None
        for page in paginator.paginate(Bucket=raw_bucket):
            for o in page.get('Contents', []):
                total += 1
                if today_prefix in o['Key']:
                    today += 1
                if 'wearable' in o['Key'].lower() or 'iot' in o['Key'].lower():
                    iot += 1
                if latest is None or o['LastModified'] > latest['LastModified']:
                    latest = o
        return {
            'raw_bucket_files': total,
            'today_ingested':   today,
            'iot_count':        iot,
            'last_upload': {
                'time': latest['LastModified'].strftime('%H:%M') if latest else '-',
                'file': latest['Key'].split('/')[-1] if latest else '-',
                'size_mb': round(latest['Size'] / 1024 / 1024, 2) if latest else 0,
            } if latest else {},
            'failed_count': 0,
        }
    except Exception:
        return {'raw_bucket_files': 0, 'today_ingested': 0, 'iot_count': 0,
                'last_upload': {}, 'failed_count': 0}


def _ping_domain_flow():
    """도메인별 S3 prefix 적재 현황 — 7 도메인."""
    raw_bucket = os.environ.get('LIFESYNC_RAW_S3_BUCKET', '')
    stream     = os.environ.get('INGESTION_STREAM_NAME', 'lifesync-kinesis-wearable-stream')
    domains    = [
        ('BANK',       'LS 은행',     'bank/'),
        ('CARD',       'LS 카드',     'card/'),
        ('INSURANCE',  'LS 보험',     'insurance/'),
        ('SECURITIES', 'LS 증권',     'securities/'),
        ('HEALTHCARE', 'LS 헬스케어', 'healthcare/'),
        ('HOSPITAL',   'LS 병원',     'hospital/'),
    ]
    out = []
    if not raw_bucket:
        return out
    from datetime import datetime, timezone, timedelta
    today_prefix = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    warn_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    s3 = _boto('s3')
    for code, label, prefix in domains:
        try:
            resp  = s3.list_objects_v2(Bucket=raw_bucket, Prefix=prefix, MaxKeys=1000)
            files = resp.get('Contents', [])
            today_count = sum(1 for f in files if today_prefix in f['Key'])
            latest      = max(files, key=lambda f: f['LastModified']) if files else None
            state = 'OK' if latest and latest['LastModified'] > warn_threshold else ('WARN' if latest else 'DOWN')
            out.append({
                'domain': code, 'label': label,
                'last_upload_at': latest['LastModified'].strftime('%H:%M:%S') if latest else '-',
                'files_today':   today_count, 'state': state,
                'source':        f's3://{raw_bucket}/{prefix}',
            })
        except Exception:
            out.append({'domain': code, 'label': label, 'last_upload_at': '-', 'files_today': 0, 'state': 'ERR', 'source': '-'})
    # WEARABLE: Kinesis IncomingRecords (last 5min)
    try:
        from datetime import datetime, timezone, timedelta
        cw    = _boto('cloudwatch')
        now   = datetime.now(timezone.utc)
        stats = cw.get_metric_statistics(
            Namespace='AWS/Kinesis', MetricName='IncomingRecords',
            Dimensions=[{'Name': 'StreamName', 'Value': stream}],
            StartTime=now - timedelta(minutes=5), EndTime=now, Period=60, Statistics=['Sum'],
        )
        total = sum(p.get('Sum', 0) for p in stats.get('Datapoints', []))
        out.append({'domain': 'WEARABLE', 'label': '웨어러블',
                    'last_upload_at': now.strftime('%H:%M:%S'),
                    'files_today': int(total),
                    'state': 'OK' if total > 0 else 'WARN',
                    'source': f'Kinesis: {stream}'})
    except Exception:
        out.append({'domain': 'WEARABLE', 'label': '웨어러블', 'last_upload_at': '-',
                    'files_today': 0, 'state': 'ERR', 'source': f'Kinesis: {stream}'})
    return out


def _ping_vm_status():
    """Group/Wearable VM EC2 상태."""
    try:
        ec2  = _boto('ec2')
        resp = ec2.describe_instances(Filters=[
            {'Name': 'tag:Project', 'Values': ['lifesync']},
            {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopping', 'stopped']},
        ])
        out = []
        for r in resp.get('Reservations', []):
            for inst in r.get('Instances', []):
                name = next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), '-')
                out.append({
                    'vm_id':   inst['InstanceId'],
                    'name':    name,
                    'state':   inst['State']['Name'],
                    'cpu_pct': 0, 'mem_pct': 0,  # CloudWatch agent metric으로 별도 보강
                })
        return out
    except Exception:
        return []


def _ping_lambda_metrics():
    """주요 Lambda 함수 호출률 (최근 1h)."""
    from datetime import datetime, timezone, timedelta
    fns = [
        'lifesync-batch-loader-lambda',
        'lifesync-ingest-lambda',
        'lifesync-recommendation-engine-lambda',
        'lifesync-wearable-stream-lambda',
    ]
    cw  = _boto('cloudwatch')
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    out = []
    for fn in fns:
        try:
            inv = cw.get_metric_statistics(
                Namespace='AWS/Lambda', MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': fn}],
                StartTime=start, EndTime=now, Period=3600, Statistics=['Sum'],
            )
            err = cw.get_metric_statistics(
                Namespace='AWS/Lambda', MetricName='Errors',
                Dimensions=[{'Name': 'FunctionName', 'Value': fn}],
                StartTime=start, EndTime=now, Period=3600, Statistics=['Sum'],
            )
            dur = cw.get_metric_statistics(
                Namespace='AWS/Lambda', MetricName='Duration',
                Dimensions=[{'Name': 'FunctionName', 'Value': fn}],
                StartTime=start, EndTime=now, Period=3600, Statistics=['Average'],
            )
            out.append({
                'fn': fn,
                'invocations_1h':  int(sum(p['Sum']     for p in inv.get('Datapoints', []))),
                'errors_1h':       int(sum(p['Sum']     for p in err.get('Datapoints', []))),
                'avg_duration_ms': int(sum(p['Average'] for p in dur.get('Datapoints', [])) / max(1, len(dur.get('Datapoints', [])))),
            })
        except Exception:
            out.append({'fn': fn, 'invocations_1h': 0, 'errors_1h': 0, 'avg_duration_ms': 0})
    return out


def _ping_glue_last_run():
    """Glue Job 최근 run."""
    job = os.environ.get('GLUE_JOB_PHYSICAL_NAME', 'lifesync-etl')
    try:
        runs = _boto('glue').get_job_runs(JobName=job, MaxResults=1).get('JobRuns', [])
        if not runs:
            return {}
        r = runs[0]
        return {
            'job_name':     job,
            'state':        r.get('JobRunState'),
            'started_at':   r['StartedOn'].strftime('%Y-%m-%d %H:%M:%S') if r.get('StartedOn') else '-',
            'completed_at': r['CompletedOn'].strftime('%Y-%m-%d %H:%M:%S') if r.get('CompletedOn') else '-',
            'duration_sec': int(r.get('ExecutionTime') or 0),
        }
    except Exception:
        return {}


def _ping_next_batch():
    """EventBridge 다음 배치 예정."""
    rule = os.environ.get('GLUE_SCHEDULE_RULE', 'lifesync-daily-etl-rule')
    try:
        info = _boto('events').describe_rule(Name=rule)
        return {
            'rule_name':         rule,
            'schedule':          info.get('ScheduleExpression', '-'),
            'next_scheduled_at': '-',  # AWS는 next fire time API 없음 — UI에서 schedule expression만 표시
        }
    except Exception:
        return {}


# ── 멀티클라우드 — TGW / VPN / VPC Peering ping ───────────
def _ping_tgw():
    try:
        tgws = _boto('ec2').describe_transit_gateways().get('TransitGateways', [])
        if not tgws:
            return {}
        t = tgws[0]
        atts = _boto('ec2').describe_transit_gateway_attachments(
            Filters=[{'Name': 'transit-gateway-id', 'Values': [t['TransitGatewayId']]}]
        ).get('TransitGatewayAttachments', [])
        return {
            'id':           t['TransitGatewayId'],
            'state':        t.get('State', '-'),
            'attachments': len([a for a in atts if a.get('State') == 'available']),
            'note':         t.get('Description', '-'),
        }
    except Exception:
        return {}


def _ping_vpn():
    try:
        conns = _boto('ec2').describe_vpn_connections().get('VpnConnections', [])
        out = []
        for c in conns:
            for t in c.get('VgwTelemetry', []) or [{'OutsideIpAddress': '-', 'Status': '-'}]:
                out.append({
                    'id':               f"{c['VpnConnectionId']}-{t.get('OutsideIpAddress', '?')}",
                    'status':           t.get('Status', '-').upper(),
                    'bgp_asn':          c.get('CustomerGatewayConfiguration', '-'),
                    'traffic_in_mbps':  0,
                    'traffic_out_mbps': 0,
                    'peer':             c.get('Tags', [{}])[0].get('Value', '-') if c.get('Tags') else '-',
                })
        return {'tunnels': out}
    except Exception:
        return {}


def _ping_vpc_peering():
    try:
        peers = _boto('ec2').describe_vpc_peering_connections().get('VpcPeeringConnections', [])
        return [
            {
                'id':        p['VpcPeeringConnectionId'],
                'state':     p.get('Status', {}).get('Code', '-'),
                'requester': p.get('RequesterVpcInfo', {}).get('VpcId', '-'),
                'accepter':  p.get('AccepterVpcInfo', {}).get('VpcId', '-'),
            }
            for p in peers
        ]
    except Exception:
        return []


def _ping_wearable_realtime():
    """Wearable CloudWatch custom metric (hr/bp/spo2/steps/alerts/send)."""
    from datetime import datetime, timezone, timedelta
    cw    = _boto('cloudwatch')
    now   = datetime.now(timezone.utc)
    start = now - timedelta(minutes=5)
    metrics = [
        ('심박수',        'wearable_hr',      'bpm',     '60-100'),
        ('혈압',          'wearable_bp_sys',  '',        '< 120/80'),
        ('산소포화도',    'wearable_spo2',    '%',       '≥ 95'),
        ('운동량 (steps)','wearable_steps',   '',        '—'),
        ('이상 이벤트',   'wearable_alerts',  '24h',     '24h'),
        ('데이터 송신',   'wearable_send',    '/min',    '—'),
    ]
    out = []
    for label, m, suffix, rng in metrics:
        try:
            stats = cw.get_metric_statistics(
                Namespace='LifeSync/Wearable', MetricName=m,
                StartTime=start, EndTime=now, Period=60, Statistics=['Average'],
            )
            pts = stats.get('Datapoints', [])
            v = round(pts[-1]['Average'], 1) if pts else 0
            out.append({'metric': label, 'current': f'{v}{suffix}', 'range': rng,
                        'state': 'OK', 'source': f'CW · {m}'})
        except Exception:
            out.append({'metric': label, 'current': '-', 'range': rng,
                        'state': 'ERR', 'source': f'CW · {m}'})
    return out


def _ping_local_lab():
    """Local Lab 상태 — onprem Lambda action 'local_lab_status'."""
    try:
        data = _call_onprem('local_lab_status')
        return data.get('environments', [])
    except Exception:
        return []


def _ping_kinesis():
    """
    P1 r23, P4 r15,r16. Kinesis 스트림 상태 + 데이터 처리 지연.
    INGESTION_STREAM_NAME (default 'lifesync-kinesis-wearable-stream') 단건 조회.
    실패/스트림 없음 시 빈 dict.
    """
    from datetime import datetime, timezone, timedelta
    stream = os.environ.get('INGESTION_STREAM_NAME', 'lifesync-kinesis-wearable-stream')
    try:
        info = _boto('kinesis').describe_stream_summary(StreamName=stream).get('StreamDescriptionSummary', {})
    except Exception:
        return {}
    out = {
        'stream_name'  : info.get('StreamName', stream),
        'status'       : info.get('StreamStatus', 'UNKNOWN'),
        'shard_count'  : info.get('OpenShardCount', 0),
        'retention_hrs': info.get('RetentionPeriodHours', 0),
    }
    # CloudWatch 평균 IteratorAgeMilliseconds (최근 5분)
    try:
        cw    = _boto('cloudwatch')
        now   = datetime.now(timezone.utc)
        start = now - timedelta(minutes=5)
        stat  = cw.get_metric_statistics(
            Namespace='AWS/Kinesis', MetricName='GetRecords.IteratorAgeMilliseconds',
            Dimensions=[{'Name': 'StreamName', 'Value': stream}],
            StartTime=start, EndTime=now, Period=60, Statistics=['Average'],
        )
        pts = stat.get('Datapoints', [])
        out['iterator_age_avg_ms'] = round(sum(p['Average'] for p in pts) / len(pts), 1) if pts else 0
    except Exception:
        out['iterator_age_avg_ms'] = None
    return out


def _ping_wearable_metrics():
    """
    P4 r45~r52. Wearable custom namespace 'LifeSync/Wearable' 5분 평균.
    metrics: heart_rate / blood_pressure_sys / blood_pressure_dia / spo2 / steps / alerts.
    """
    from datetime import datetime, timezone, timedelta
    try:
        cw    = _boto('cloudwatch')
        now   = datetime.now(timezone.utc)
        start = now - timedelta(minutes=5)
    except Exception:
        return []
    out = []
    for metric, label in [
        ('heart_rate',        '심박수'),
        ('blood_pressure_sys','수축기혈압'),
        ('blood_pressure_dia','이완기혈압'),
        ('spo2',              '산소포화도'),
        ('steps',             '걸음수'),
        ('activity_kcal',     '활동칼로리'),
        ('alerts',            '이상이벤트'),
    ]:
        try:
            stat = cw.get_metric_statistics(
                Namespace='LifeSync/Wearable', MetricName=metric,
                StartTime=start, EndTime=now, Period=60, Statistics=['Average','Sum'],
            )
            pts = stat.get('Datapoints', [])
            if pts:
                avg = round(sum(p.get('Average', 0) for p in pts) / len(pts), 1)
                tot = round(sum(p.get('Sum', 0) for p in pts), 1)
                out.append({'metric': metric, 'label': label, 'avg': avg, 'sum': tot})
            else:
                out.append({'metric': metric, 'label': label, 'avg': None, 'sum': 0})
        except Exception:
            out.append({'metric': metric, 'label': label, 'avg': None, 'sum': 0})
    return out


def _ping_emr():
    """
    P4 r13. EMR 클러스터 상태 (lifesync 태그 또는 RUNNING/WAITING).
    """
    try:
        clusters = _boto('emr').list_clusters(
            ClusterStates=['STARTING','BOOTSTRAPPING','RUNNING','WAITING','TERMINATING']
        ).get('Clusters', [])
    except Exception:
        return []
    return [{
        'cluster_id'  : c.get('Id'),
        'name'        : c.get('Name'),
        'state'       : c.get('Status', {}).get('State'),
        'state_change_at': str(c.get('Status', {}).get('StateChangeReason', {}).get('Code') or ''),
    } for c in clusters]


def _ddb_score_distribution():
    """
    P3 r22. lifesync_customer_result Scan + dynamic_score 0~100 히스토그램.
    Scan 비용 주의 — 운영은 lambda 일배치 결과를 mart 테이블에 두고 read 권장.
    """
    try:
        items = get_dynamo_table().scan(ProjectionExpression='dynamic_score').get('Items', [])
    except Exception:
        return []
    buckets = [0]*10  # 0~9, 10~19, ..., 90~100
    for it in items:
        try:
            s = int(float(it.get('dynamic_score', 0)))
            idx = min(s // 10, 9)
            buckets[idx] += 1
        except Exception:
            continue
    return [{'bucket': f'{i*10}~{i*10+9}', 'count': buckets[i]} for i in range(10)]


def _ddb_prob_distribution():
    """
    P3 r8. lifesync_customer_result Scan + vip_prob/signup_prob/rec_prob 평균 + 0.0~1.0 히스토그램.
    """
    try:
        items = get_dynamo_table().scan(
            ProjectionExpression='vip_prob, signup_prob, rec_prob'
        ).get('Items', [])
    except Exception:
        return {}
    sums  = {'vip_prob': 0.0, 'signup_prob': 0.0, 'rec_prob': 0.0}
    cnts  = {'vip_prob': 0,   'signup_prob': 0,   'rec_prob': 0}
    bins  = {k: [0]*10 for k in sums}  # 0.0~0.1, ..., 0.9~1.0
    for it in items:
        for k in sums:
            try:
                v = float(it.get(k, 0))
                sums[k] += v
                cnts[k] += 1
                idx = min(int(v * 10), 9)
                bins[k][idx] += 1
            except Exception:
                continue
    return {
        'avg': {k: round(sums[k] / cnts[k], 3) if cnts[k] else 0 for k in sums},
        'histogram': {k: [{'bin': f'{i*0.1:.1f}~{(i+1)*0.1:.1f}', 'count': bins[k][i]} for i in range(10)] for k in bins},
    }


# ── GCP SDK 헬퍼 ────────────────────────────────────────────
# 인증: ADC (Application Default Credentials) — GOOGLE_APPLICATION_CREDENTIALS env
#   또는 Workload Identity Federation. 인증 없으면 모든 함수가 안전하게 [] / {} 반환.
GCP_PROJECT_ID  = os.environ.get('GCP_PROJECT_ID', '')
GCP_BQ_DATASET  = os.environ.get('GCP_BQ_DATASET', 'lifesync_curated')
GCP_VERTEX_LOC  = os.environ.get('GCP_VERTEX_LOCATION', 'asia-northeast3')

_gcp_bq_client      = None
_gcp_aip_initialized= False
_gcp_mon_client     = None


def _get_bq():
    global _gcp_bq_client
    if not GCP_PROJECT_ID:
        return None
    if _gcp_bq_client is None:
        try:
            from google.cloud import bigquery as _bq
            _gcp_bq_client = _bq.Client(project=GCP_PROJECT_ID)
        except Exception:
            return None
    return _gcp_bq_client


def _init_aip():
    global _gcp_aip_initialized
    if not GCP_PROJECT_ID:
        return False
    if not _gcp_aip_initialized:
        try:
            from google.cloud import aiplatform
            aiplatform.init(project=GCP_PROJECT_ID, location=GCP_VERTEX_LOC)
            _gcp_aip_initialized = True
        except Exception:
            return False
    return _gcp_aip_initialized


def _get_mon():
    global _gcp_mon_client
    if not GCP_PROJECT_ID:
        return None
    if _gcp_mon_client is None:
        try:
            from google.cloud import monitoring_v3 as _mon
            _gcp_mon_client = _mon.MetricServiceClient()
        except Exception:
            return None
    return _gcp_mon_client


def _stub_gcp_status():
    """
    P4 r32~36 — GCP BigQuery / Vertex AI / Cloud Run 상태.
    Cloud Monitoring API 로 service 별 uptime/health 조회. 인증/호출 실패 시 빈 list.
    """
    mon = _get_mon()
    if mon is None:
        return []
    try:
        # BQ 쿼리 잡 카운트 (최근 7일) — Monitoring 'bigquery.googleapis.com/job/num_in_flight'
        from google.cloud import monitoring_v3 as _mon
        from google.protobuf import timestamp_pb2
        import time
        now      = int(time.time())
        interval = _mon.TimeInterval({
            'end_time':   timestamp_pb2.Timestamp(seconds=now),
            'start_time': timestamp_pb2.Timestamp(seconds=now - 7 * 86400),
        })
        out = []
        for service, metric in [
            ('BigQuery',  'bigquery.googleapis.com/query/count'),
            ('Vertex AI', 'aiplatform.googleapis.com/prediction/online/prediction_count'),
            ('Cloud Run', 'run.googleapis.com/request_count'),
        ]:
            try:
                req = _mon.ListTimeSeriesRequest({
                    'name':     f'projects/{GCP_PROJECT_ID}',
                    'filter':   f'metric.type="{metric}"',
                    'interval': interval,
                    'view':     _mon.ListTimeSeriesRequest.TimeSeriesView.HEADERS,
                })
                series = list(mon.list_time_series(request=req))
                out.append({'service': service, 'state': 'UP', 'series_count': len(series)})
            except Exception as e:
                out.append({'service': service, 'state': 'UNKNOWN', 'error': str(e)[:80]})
        return out
    except Exception:
        return []


def _stub_vertex_metrics():
    """
    P3 r22 — Vertex AI 모델 평가 메트릭 (Precision/Recall 등).
    Model.list() → 최신 모델의 evaluation 가져옴.
    """
    if not _init_aip():
        return {}
    try:
        from google.cloud import aiplatform
        models = aiplatform.Model.list(order_by='create_time desc')
        if not models:
            return {}
        latest = models[0]
        evals  = latest.list_model_evaluations()
        if not evals:
            return {'model_id': latest.resource_name, 'evaluations': []}
        ev = list(evals)[0]
        return {
            'model_id'   : latest.resource_name,
            'display_name': latest.display_name,
            'create_time': str(latest.create_time),
            'metrics'    : dict(ev.metrics) if hasattr(ev, 'metrics') else {},
        }
    except Exception:
        return {}


def _stub_feature_importance():
    """
    P3 r9 — Feature Importance: BigQuery lifesync_curated.ai_feature_table 컬럼별 분포.
    """
    bq = _get_bq()
    if bq is None:
        return []
    try:
        sql = f"""
            SELECT column_name, AVG(value) AS avg_val, STDDEV(value) AS std_val
            FROM `{GCP_PROJECT_ID}.{GCP_BQ_DATASET}.ai_feature_table`
            GROUP BY column_name
            ORDER BY ABS(avg_val) DESC
            LIMIT 20
        """
        return [dict(row) for row in bq.query(sql).result()]
    except Exception:
        return []


def _stub_bigquery_analytics(query_kind='recommendation_mart'):
    """
    P3 r17,r28 — BigQuery 마트 ad-hoc 조회.
      recommendation_mart : lifesync_curated.recommendation_mart GROUP BY name
      customer_summary    : lifesync_serving.v_customer_summary 샘플
      prediction_result   : lifesync_ml.*_prediction_result Precision/Recall
    """
    bq = _get_bq()
    if bq is None:
        return []
    try:
        if query_kind == 'recommendation_mart':
            sql = f"""SELECT recommendation_name, COUNT(*) AS cnt
                      FROM `{GCP_PROJECT_ID}.{GCP_BQ_DATASET}.recommendation_mart`
                      GROUP BY recommendation_name ORDER BY cnt DESC LIMIT 20"""
        elif query_kind == 'customer_summary':
            sql = f"""SELECT * FROM `{GCP_PROJECT_ID}.lifesync_serving.v_customer_summary` LIMIT 100"""
        elif query_kind == 'prediction_result':
            sql = f"""SELECT model_name,
                             COUNTIF(actual_label IS NOT NULL) AS labeled,
                             AVG(IF(predicted_label = actual_label, 1.0, 0.0)) AS accuracy
                      FROM `{GCP_PROJECT_ID}.lifesync_ml.vip_prediction_result`
                      WHERE actual_label IS NOT NULL
                      GROUP BY model_name"""
        else:
            return []
        return [dict(row) for row in bq.query(sql).result()]
    except Exception:
        return []


_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        host = os.environ.get('REDIS_HOST')
        if not host:
            return None
        try:
            import redis as _redis_lib
            _redis_client = _redis_lib.Redis(
                host=host,
                port=int(os.environ.get('REDIS_PORT', '6379')),
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
        except Exception:
            return None
    return _redis_client


def _stub_redis_personalized(global_id):
    """
    Redis Personalized Top 3 — ZREVRANGE rec:{global_id} 0 N WITHSCORES (TTL 6h).
    miss/실패 시 빈 dict 반환 → /users/<id> 라우트에서 MOCKUP_REDIS_PERSONALIZED fallback.
    """
    r = _get_redis()
    if r is None:
        return {}
    try:
        pairs = r.zrevrange(f'rec:{global_id}', 0, 2, withscores=True)
        if not pairs:
            return {}
        return {
            'top': [{'product_id': pid, 'score': float(score)} for pid, score in pairs],
            'source': 'redis',
        }
    except Exception:
        return {}


# ── analytics batch 결과 read 헬퍼 (P3 r10/r12/r13) ─────────────
def _aurora_recommend_trend_7day():
    """Aurora customer_recommend_daily 에서 최근 7일치 + 7일 평균. P3 r10."""
    try:
        with get_db() as db, db.cursor() as cur:
            cur.execute(
                "SELECT date, recommended, ctr, cvr, "
                "       AVG(ctr) OVER() AS avg_ctr, "
                "       AVG(cvr) OVER() AS avg_cvr "
                "FROM customer_recommend_daily "
                "WHERE date >= CURDATE() - INTERVAL 7 DAY "
                "ORDER BY date"
            )
            rows = cur.fetchall()
        for r in rows:
            r['date'] = r['date'].strftime('%m-%d') if r.get('date') else ''
        return rows
    except Exception:
        return []


def _ddb_query_today(table_name, sk_prefix=None):
    """analytics_* DDB 테이블 오늘 snapshot_date 조회. sk_prefix 있으면 begins_with."""
    from datetime import date as _date
    from boto3.dynamodb.conditions import Key
    today = _date.today().isoformat()
    try:
        table = boto3.resource('dynamodb', region_name=AWS_REGION).Table(table_name)
        kw = {'KeyConditionExpression': Key('snapshot_date').eq(today)}
        if sk_prefix:
            kw['KeyConditionExpression'] &= Key('segment_key').begins_with(sk_prefix)
        return table.query(**kw).get('Items', [])
    except Exception:
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
            return redirect(url_for('dashboard'))
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))


# 기존 /overview URL은 /dashboard 로 영구 이동
@app.route('/overview')
@login_required
def overview():
    return redirect(url_for('dashboard'))


# ── Executive Dashboard ───────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    """대시보드 PPTX Slide 1 도형 의도 — 작은 KPI 9개 + 큰 박스 4개 + 하단 박스 2개."""
    return render_template('dashboard.html',
        active='dashboard',
        kpi_top=MOCKUP_KPI_TOP,
        kpi_mid=MOCKUP_KPI_MID,
        aws_status=MOCKUP_AWS_STATUS_DETAIL,
        gcp_status=MOCKUP_GCP_STATUS_DETAIL,
        s3_box=MOCKUP_S3_INGESTION_BOX,
        signup_box=MOCKUP_SIGNUP_BOX,
        recent_uploads=MOCKUP_RECENT_UPLOADS,
    )


# ── Customer 360 — 검색 + 단일 결과 카드 (PPTX Slide 2) ───
@app.route('/users')
@login_required
def users():
    q = request.args.get('q', '').strip()
    if not q:
        return render_template('users.html',
            active='customer',
            q='',
            customer=None,
            recommend_history=[],
            personalized=None,
        )

    # 검색: global_id 우선, 그 다음 이름/이메일
    customer = None
    if USE_MOCK:
        customer = next((u for u in MOCK_USERS if u['global_id'] == q or q in u['name'] or q in u['email']), None)
        if customer:
            gid = customer['global_id']
            scores            = MOCK_SCORES.get(gid)
            recommend_history = MOCK_RECOMMEND_HISTORY.get(gid, [])
            personalized      = MOCKUP_REDIS_PERSONALIZED
        else:
            scores = None; recommend_history = []; personalized = None
    else:
        try:
            item = get_dynamo_table().get_item(Key={'global_id': q}).get('Item')
            if item:
                customer = {
                    'global_id':  item['global_id'],
                    'ls_user_id': '-',
                    'name':       '-',
                    'email':      '-',
                    'grade':      item.get('dynamic_grade', '-'),
                }
                scores            = item
                recommend_history = []  # Aurora 별도 쿼리 — 시연 보류
                personalized      = MOCKUP_REDIS_PERSONALIZED
            else:
                scores = None; recommend_history = []; personalized = None
        except Exception:
            scores = None; recommend_history = []; personalized = None

    return render_template('users.html',
        active='customer',
        q=q,
        customer=customer,
        scores=scores,
        recommend_history=recommend_history,
        personalized=personalized,
        crosssell=MOCKUP_CROSSSELL_LIST,
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

    # Redis Personalized Top 3 (USE_MOCK: dict / 운영: stub — ElastiCache 가동 후 활성)
    if USE_MOCK:
        personalized = MOCKUP_REDIS_PERSONALIZED
    else:
        personalized = _stub_redis_personalized(global_id) or MOCKUP_REDIS_PERSONALIZED

    return render_template('user_detail.html',
        active='customer',
        user=user,
        scores=scores,
        consents=consents,
        recommend_history=recommend_history,
        identities=identities,
        personalized=personalized,
    )


# ── AI 추천 ───────────────────────────────────────────
@app.route('/ai')
@login_required
def ai():
    if USE_MOCK:
        top10        = MOCKUP_RECOMMEND_TOP10
        by_category  = MOCKUP_RECOMMEND_BY_CATEGORY
        by_grade     = MOCKUP_RECOMMEND_BY_GRADE
        score_dist   = MOCKUP_SCORE_DISTRIBUTION
    else:
        # Aurora 기반 — 카테고리별/등급별/TOP10 (DB 없으면 빈 리스트)
        top10 = by_category = by_grade = []
        score_dist = {'dynamic_score': []}
        try:
            db = get_db()
            try:
                with db.cursor() as cur:
                    cur.execute(
                        'SELECT p.product_name AS product, p.category, '
                        '       COUNT(*) AS recommended, '
                        '       ROUND(SUM(r.clicked_flag = "Y") / COUNT(*) * 100, 1) AS ctr, '
                        '       ROUND(SUM(r.purchased_flag = "Y") / COUNT(*) * 100, 1) AS cvr '
                        'FROM customer_recommend_history r '
                        'JOIN product_master p ON r.product_id = p.product_id '
                        'GROUP BY p.product_id, p.product_name, p.category '
                        'ORDER BY recommended DESC LIMIT 10'
                    )
                    top10 = [dict(r, rank=i + 1) for i, r in enumerate(cur.fetchall())]

                    cur.execute(
                        'SELECT p.category, '
                        '       ROUND(SUM(r.clicked_flag = "Y")  / COUNT(*) * 100, 1) AS ctr, '
                        '       ROUND(SUM(r.purchased_flag = "Y") / COUNT(*) * 100, 1) AS cvr '
                        'FROM customer_recommend_history r '
                        'JOIN product_master p ON r.product_id = p.product_id '
                        'GROUP BY p.category ORDER BY ctr DESC'
                    )
                    by_category = list(cur.fetchall())
            finally:
                db.close()
        except Exception:
            pass
        # DynamoDB — AI Score 분포 (5 bucket)
        try:
            items = get_dynamo_table().scan(
                ProjectionExpression='dynamic_score, dynamic_grade'
            ).get('Items', [])
            from collections import defaultdict
            buckets = ['0-20', '20-40', '40-60', '60-80', '80-100']
            def _bucket(v):
                v = float(v or 0)
                if v < 20:  return '0-20'
                if v < 40:  return '20-40'
                if v < 60:  return '40-60'
                if v < 80:  return '60-80'
                return '80-100'
            ds = defaultdict(int); gc = defaultdict(lambda: {'cnt': 0})
            for i in items:
                ds[_bucket(i.get('dynamic_score'))] += 1
                gc[i.get('dynamic_grade', 'BASIC')]['cnt'] += 1
            score_dist = {
                'dynamic_score': [{'bucket': b, 'count': ds[b]} for b in buckets],
            }
            by_grade = [{'grade': g, 'cvr': 0} for g in GRADES if gc[g]['cnt']]
        except Exception:
            pass

    # Vertex AI / BigQuery — 항상 mock (GCP 실연동 자리는 stub)
    if USE_MOCK:
        ai_kpi             = MOCKUP_AI_KPI
        vertex_ai          = MOCKUP_VERTEX_AI
        feature_importance = MOCKUP_FEATURE_IMPORTANCE
        recommend_trend    = MOCKUP_RECOMMEND_TREND
    else:
        ai_kpi             = MOCKUP_AI_KPI
        vertex_ai          = _stub_vertex_metrics() or MOCKUP_VERTEX_AI
        feature_importance = _stub_feature_importance() or MOCKUP_FEATURE_IMPORTANCE
        recommend_trend    = _aurora_recommend_trend_7day() or MOCKUP_RECOMMEND_TREND

    return render_template('ai.html',
        active='ai',
        top10=top10,
        by_category=by_category,
        by_grade=by_grade,
        score_dist=score_dist,
        ai_kpi=ai_kpi,
        vertex_ai=vertex_ai,
        feature_importance=feature_importance,
        age_model_ratio=MOCKUP_AGE_MODEL_RATIO,
        recommend_trend=recommend_trend,
    )


# ── 신규 admin JSON API — analytics batch 결과 read ─────────────
from flask import jsonify  # noqa: E402

@app.route('/api/admin/recommend-trend')
@login_required
def api_admin_recommend_trend():
    """P3 r10. Aurora customer_recommend_daily 최근 7일 + 평균."""
    rows = _aurora_recommend_trend_7day() if not USE_MOCK else MOCKUP_RECOMMEND_TREND
    return jsonify(rows)


@app.route('/api/admin/segment-performance')
@login_required
def api_admin_segment_performance():
    """P3 r12. analytics_segment_performance 오늘자 — dim prefix 필터 가능 (?dim=gender)."""
    dim = request.args.get('dim')  # gender / age_band / region / income / asset
    prefix = f'{dim}#' if dim else None
    rows = _ddb_query_today(DDB_SEGMENT_TABLE, sk_prefix=prefix)
    return jsonify(rows)


@app.route('/api/admin/demographic-summary')
@login_required
def api_admin_demographic_summary():
    """P3 r13. analytics_demographic_summary 오늘자 — dim prefix 필터 가능."""
    dim = request.args.get('dim')
    prefix = f'{dim}#' if dim else None
    rows = _ddb_query_today(DDB_DEMOGRAPHIC_TABLE, sk_prefix=prefix)
    return jsonify(rows)


@app.route('/api/admin/local-lab-status')
@login_required
def api_admin_local_lab_status():
    """P4 r38~43, r60. 온프레 환경/서비스 종합 헬스 — Lambda onprem-query 'local_lab_status' 경유."""
    if USE_MOCK:
        return jsonify({'status': 'pass', 'time': '',
                        'environments': MOCKUP_LOCAL_LAB, 'checks': {}})
    data = _call_onprem('local_lab_status')
    return jsonify(data or {'status': 'fail', 'environments': [], 'checks': {}, 'output': 'onprem lambda unavailable'})


# ── 시트 정의 /api/* 라우트 — 기존 _ping_* / _stub_* 함수 JSON wrap ─────────────

@app.route('/api/dashboard/summary')
@login_required
def api_dashboard_summary():
    """P1 r29. KPI 종합 — 통합/플랫폼/분석 고객 수 + Aurora 추천 이력 + DDB 결과."""
    if USE_MOCK:
        return jsonify({'kpi_top': MOCKUP_KPI_TOP, 'kpi_mid': MOCKUP_KPI_MID})
    return jsonify({
        'master_customer'  : _call_onprem('count_master_customer'),
        'users_active'     : _call_onprem('count_users'),
        'users_consented'  : _call_onprem('count_users_consented'),
    })


@app.route('/api/s3/status')
@login_required
def api_s3_status():
    """P1 r30. S3 적재 현황 — boto3 list_buckets + list_objects."""
    return jsonify(_ping_s3_ingestion() if not USE_MOCK else MOCKUP_S3_INGESTION_BOX)


@app.route('/api/cloud/status')
@login_required
def api_cloud_status():
    """P1 r31. AWS/GCP 헬스 종합."""
    if USE_MOCK:
        return jsonify({'aws': MOCKUP_AWS_STATUS_DETAIL, 'gcp': MOCKUP_GCP_STATUS_DETAIL})
    return jsonify({'aws': _ping_cloud_status(), 'gcp': _stub_gcp_status() or MOCKUP_GCP_STATUS_DETAIL})


@app.route('/api/customer/profile/<global_id>')
@login_required
def api_customer_profile(global_id):
    """P2 r44. customer_pii_secure + customer_360_profile + master_customer + users."""
    if USE_MOCK:
        return jsonify(MOCK_USERS.get(global_id, {}))
    return jsonify(_call_onprem('get_all', global_id=global_id))


@app.route('/api/customer/ai-result/<global_id>')
@login_required
def api_customer_ai_result(global_id):
    """P2 r45. DDB lifesync_customer_result GetItem."""
    if USE_MOCK:
        return jsonify(MOCK_SCORES.get(global_id, {}))
    try:
        return jsonify(get_dynamo_table().get_item(Key={'global_id': global_id}).get('Item', {}))
    except Exception:
        return jsonify({})


@app.route('/api/customer/recommend/<global_id>')
@login_required
def api_customer_recommend(global_id):
    """P2 r46. Redis ZREVRANGE rec:{global_id} 0 N WITHSCORES."""
    data = _stub_redis_personalized(global_id) if not USE_MOCK else MOCKUP_REDIS_PERSONALIZED
    return jsonify(data or {})


@app.route('/api/customer/history/<global_id>')
@login_required
def api_customer_history(global_id):
    """P2 r47. Aurora customer_recommend_history."""
    if USE_MOCK:
        return jsonify(MOCK_RECOMMEND_HISTORY.get(global_id, []))
    try:
        with get_db() as db, db.cursor() as cur:
            cur.execute(
                "SELECT p.product_name, r.recommended_at, r.clicked_flag, r.purchased_flag "
                "FROM customer_recommend_history r "
                "JOIN product_master p ON r.product_id = p.product_id "
                "WHERE r.global_id=%s ORDER BY r.recommended_at DESC LIMIT 50",
                (global_id,),
            )
            return jsonify([{**r, 'recommended_at': str(r['recommended_at'])} for r in cur.fetchall()])
    except Exception:
        return jsonify([])


@app.route('/api/customer/activity/<global_id>')
@login_required
def api_customer_activity(global_id):
    """P2 r48. Aurora customer_dashboard_log."""
    if USE_MOCK:
        return jsonify([])
    try:
        with get_db() as db, db.cursor() as cur:
            cur.execute(
                "SELECT view_time, page_path, action_type "
                "FROM customer_dashboard_log WHERE global_id=%s "
                "ORDER BY view_time DESC LIMIT 50",
                (global_id,),
            )
            return jsonify([{**r, 'view_time': str(r['view_time'])} for r in cur.fetchall()])
    except Exception:
        return jsonify([])


@app.route('/api/ai/summary')
@login_required
def api_ai_summary():
    """P3. AI KPI 종합 (DDB 등급 분포 + Aurora CTR/CVR + Vertex AI metric)."""
    return jsonify({
        'ai_kpi'        : MOCKUP_AI_KPI,
        'vertex_metrics': (_stub_vertex_metrics() if not USE_MOCK else {}) or {},
        'score_dist'    : (_ddb_score_distribution() if not USE_MOCK else []),
    })


@app.route('/api/ai/recommend-stats')
@login_required
def api_ai_recommend_stats():
    """P3. 추천 통계 — vip/signup/rec prob 평균 + 히스토그램."""
    return jsonify(_ddb_prob_distribution() if not USE_MOCK else {})


@app.route('/api/bigquery/analytics')
@login_required
def api_bigquery_analytics():
    """P3 r28. BigQuery 마트 ad-hoc — ?kind=recommendation_mart|customer_summary|prediction_result."""
    kind = request.args.get('kind', 'recommendation_mart')
    return jsonify(_stub_bigquery_analytics(kind) if not USE_MOCK else [])


@app.route('/api/network/tgw')
@login_required
def api_network_tgw():
    """P4 r56. TGW + Attachment 상태."""
    return jsonify(_ping_tgw() if not USE_MOCK else MOCKUP_TGW)


@app.route('/api/network/vpn')
@login_required
def api_network_vpn():
    """P4 r57. VPN 터널 상태 + CloudWatch 트래픽."""
    return jsonify(_ping_vpn() if not USE_MOCK else MOCKUP_VPN)


@app.route('/api/vm/group')
@login_required
def api_vm_group():
    """P4 r58. Group VM EC2 인스턴스 (tag Project=lifesync)."""
    if USE_MOCK:
        return jsonify(MOCKUP_AFFILIATE_HEALTH)
    rows = _ping_vm_status() or []
    return jsonify([r for r in rows if 'wearable' not in str(r.get('tag', '')).lower()])


@app.route('/api/vm/wearable')
@login_required
def api_vm_wearable():
    """P4 r59. Wearable VM + CloudWatch custom metric (LifeSync/Wearable)."""
    return jsonify({
        'instances': _ping_vm_status() if not USE_MOCK else [],
        'metrics'  : _ping_wearable_metrics() if not USE_MOCK else MOCKUP_WEARABLE_REALTIME,
    })


@app.route('/api/kinesis/status')
@login_required
def api_kinesis_status():
    """P1 r23, P4 r15. Kinesis stream 단건 상태."""
    return jsonify(_ping_kinesis() if not USE_MOCK else {})


@app.route('/api/emr/status')
@login_required
def api_emr_status():
    """P4 r13. EMR Cluster 목록 + 상태."""
    return jsonify(_ping_emr() if not USE_MOCK else [])


@app.route('/api/admin/applications')
@login_required
def api_admin_applications():
    """
    상품 신청 내역 조회 — customer_product_application 테이블.
    Query params:
      status   : RECEIVED / IN_REVIEW / APPROVED / REJECTED / CANCELED (선택)
      gid      : 특정 global_id (선택)
      limit    : default 50, max 200
      offset   : default 0
    """
    if USE_MOCK:
        return jsonify({'total': 0, 'rows': []})

    status = request.args.get('status')
    gid    = request.args.get('gid')
    try:
        limit  = min(int(request.args.get('limit', '50')), 200)
        offset = max(int(request.args.get('offset', '0')), 0)
    except ValueError:
        return jsonify({'error': 'limit/offset must be int'}), 400

    where, args = ['1=1'], []
    if status:
        where.append('a.status = %s');     args.append(status)
    if gid:
        where.append('a.global_id = %s'); args.append(gid)
    where_sql = ' AND '.join(where)

    try:
        with get_db() as db, db.cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM customer_product_application a WHERE {where_sql}",
                tuple(args),
            )
            total = cur.fetchone()['cnt']

            cur.execute(
                "SELECT a.application_id, a.global_id, a.ls_user_id, "
                "       a.product_code, p.product_name, "
                "       c.company_name, cat.category_name, "
                "       a.applicant_name, a.applicant_phone, a.applicant_email, "
                "       a.apply_amount, a.contact_time, a.memo, "
                "       a.agree_marketing, a.status, a.created_at, a.updated_at "
                "FROM customer_product_application a "
                "LEFT JOIN product_master  p   ON a.product_id  = p.product_id "
                "LEFT JOIN company_master  c   ON p.company_id  = c.company_id "
                "LEFT JOIN category_master cat ON p.category_id = cat.category_id "
                f"WHERE {where_sql} "
                "ORDER BY a.created_at DESC LIMIT %s OFFSET %s",
                tuple(args) + (limit, offset),
            )
            rows = []
            for r in cur.fetchall():
                rows.append({**r,
                    'created_at': str(r['created_at']) if r.get('created_at') else None,
                    'updated_at': str(r['updated_at']) if r.get('updated_at') else None,
                })
    except Exception as e:
        return jsonify({'error': f'조회 실패: {str(e)}'}), 500

    return jsonify({'total': total, 'limit': limit, 'offset': offset, 'rows': rows})


# ── 운영 모니터링 ─────────────────────────────────────
@app.route('/ops')
@login_required
def ops():
    if USE_MOCK:
        cloud_status      = MOCKUP_CLOUD_STATUS
        domain_flow       = MOCKUP_DOMAIN_FLOW
        lambda_metrics    = MOCKUP_LAMBDA_METRICS
        glue_last         = MOCKUP_GLUE_LAST_RUN
        next_batch        = MOCKUP_NEXT_BATCH
        recent_errors     = MOCKUP_RECENT_ERRORS
        tgw               = MOCKUP_TGW
        vpn               = MOCKUP_VPN
        vpc_peering       = MOCKUP_VPC_PEERING
        wearable_realtime = MOCKUP_WEARABLE_REALTIME
        affiliate_health  = MOCKUP_AFFILIATE_HEALTH
        backend_services  = MOCKUP_BACKEND_SERVICES
    else:
        aws_status        = _ping_cloud_status()
        cloud_status      = aws_status + MOCKUP_CLOUD_STATUS[-2:]  # AWS 실연동 + GCP mock
        domain_flow       = _ping_domain_flow()
        lambda_metrics    = _ping_lambda_metrics()
        glue_last         = _ping_glue_last_run()
        next_batch        = _ping_next_batch()
        recent_errors     = []
        tgw               = _ping_tgw()       or MOCKUP_TGW
        vpn               = _ping_vpn()       or MOCKUP_VPN
        vpc_peering       = _ping_vpc_peering() or MOCKUP_VPC_PEERING
        wearable_realtime = _ping_wearable_realtime()
        affiliate_health  = MOCKUP_AFFILIATE_HEALTH  # 계열사 ping은 PrivateAPI 외부 — mock fallback
        backend_services  = MOCKUP_BACKEND_SERVICES

    return render_template('ops.html',
        active='ops',
        cloud_status=cloud_status,
        domain_flow=domain_flow,
        lambda_metrics=lambda_metrics,
        glue_last=glue_last,
        next_batch=next_batch,
        recent_errors=recent_errors,
        tgw=tgw,
        vpn=vpn,
        vpc_peering=vpc_peering,
        wearable_realtime=wearable_realtime,
        affiliate_health=affiliate_health,
        backend_services=backend_services,
    )


@app.context_processor
def inject_config():
    return {
        'config': {'USE_MOCK': USE_MOCK, 'ADMIN_USER': ADMIN_USER},
        'consent_labels': CONSENT_LABELS,
    }


if __name__ == '__main__':
    app.run(debug=True, port=5001)

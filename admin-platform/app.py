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
        DOMAINS, INTEGRITY_TABLE_ROWS, INTEGRITY_TOKEN_MAP_COVERAGE,
    )

# 신규 페이지에서 mock fallback 으로 사용 (USE_MOCK=true 일 때 항상 적재)
from mockup_data import (
    MOCKUP_KPI_SUMMARY, MOCKUP_S3_INGESTION,
    MOCKUP_INFRA, MOCKUP_DOMAIN_FLOW, MOCKUP_VM_STATUS,
    MOCKUP_LAMBDA_METRICS, MOCKUP_GLUE_LAST_RUN, MOCKUP_NEXT_BATCH,
    MOCKUP_RECOMMEND_BY_CATEGORY, MOCKUP_RECOMMEND_BY_GRADE, MOCKUP_RECOMMEND_TOP10,
    MOCKUP_AI_MODEL, MOCKUP_ANALYSIS_TREND, MOCKUP_SCORE_DISTRIBUTION,
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


# ── Mockup 시안 (정식 화면 아님 · mock 데이터 임의) ──
from mockup_data import (
    MOCKUP_ETL_LAST_RUN, MOCKUP_ETL_NEXT, MOCKUP_EXTERNAL_SYSTEMS, MOCKUP_RECENT_ERRORS,
    MOCKUP_INFRA, MOCKUP_PII_STATUS, MOCKUP_AI_MODEL, MOCKUP_ANALYSIS_TREND, MOCKUP_CUSTOMER,
)


@app.route('/mockup/overview')
@login_required
def mockup_overview():
    ext_ok = sum(1 for s in MOCKUP_EXTERNAL_SYSTEMS if s['status'] == 'OK')
    return render_template('mockup/overview.html',
        active='mockup_overview',
        etl_last=MOCKUP_ETL_LAST_RUN,
        etl_next=MOCKUP_ETL_NEXT,
        ext_systems=MOCKUP_EXTERNAL_SYSTEMS,
        ext_ok=ext_ok,
        ext_total=len(MOCKUP_EXTERNAL_SYSTEMS),
        recent_errors=MOCKUP_RECENT_ERRORS,
        infra=MOCKUP_INFRA,
    )


@app.route('/mockup/analytics')
@login_required
def mockup_analytics():
    return render_template('mockup/analytics.html',
        active='mockup_analytics',
        pii=MOCKUP_PII_STATUS,
        ai_model=MOCKUP_AI_MODEL,
        analysis_trend=MOCKUP_ANALYSIS_TREND,
    )


@app.route('/mockup/customer-data')
@login_required
def mockup_customer_data():
    return render_template('mockup/customer_data.html',
        active='mockup_customer',
        c=MOCKUP_CUSTOMER,
    )


# ── Data Integrity (A-1-1) ────────────────────────────
@app.route('/data-integrity')
@login_required
def data_integrity():
    if USE_MOCK:
        table_rows     = INTEGRITY_TABLE_ROWS
        token_coverage = INTEGRITY_TOKEN_MAP_COVERAGE

        consent_by_domain = {d: {'Y': 0, 'N': 0} for d in DOMAINS}
        for user_consents in MOCK_CONSENTS.values():
            for c in user_consents:
                if c['domain'] in consent_by_domain:
                    consent_by_domain[c['domain']][c['consent_flag']] += 1

        mapping_by_domain = {d: 0 for d in DOMAINS}
        for user_ids in MOCK_IDENTITIES.values():
            for m in user_ids:
                if m['company_id'] in mapping_by_domain:
                    mapping_by_domain[m['company_id']] += 1

        total_mappings = sum(len(v) for v in MOCK_IDENTITIES.values())
        avg_mapping    = round(total_mappings / max(1, len(MOCK_IDENTITIES)), 2)
    else:
        # 운영: onprem Lambda data_integrity_summary + DynamoDB
        try:
            data = _call_onprem('data_integrity_summary')
            table_rows        = data.get('table_rows', [])
            token_coverage    = data.get('token_coverage', {})
            consent_by_domain = data.get('consent_by_domain', {})
            mapping_by_domain = data.get('mapping_by_domain', {})
            avg_mapping       = data.get('avg_mapping', 0)
        except Exception:
            table_rows, token_coverage, consent_by_domain, mapping_by_domain, avg_mapping = [], {}, {}, {}, 0

    return render_template('data_integrity.html',
        active='data_integrity',
        table_rows=table_rows,
        token_coverage=token_coverage,
        consent_by_domain=consent_by_domain,
        mapping_by_domain=mapping_by_domain,
        avg_mapping=avg_mapping,
    )


@app.context_processor
def inject_config():
    return {
        'config': {'USE_MOCK': USE_MOCK, 'ADMIN_USER': ADMIN_USER},
        'consent_labels': CONSENT_LABELS,
    }


if __name__ == '__main__':
    app.run(debug=True, port=5001)

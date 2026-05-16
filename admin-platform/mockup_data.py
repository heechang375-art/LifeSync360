"""시안용 mock 데이터 — 정식 mock_data.py와 분리.

이 파일의 모든 데이터는 시안(mockup) 전용으로 임의 작성됨.
운영 모드에서는 사용되지 않음.
"""

# ── 운영 모니터링 — 최근 오류 (ops 화면) ──────────────────
MOCKUP_RECENT_ERRORS = [
    {'time': '10:42', 'system': 'INSURANCE', 'severity': 'WARN',  'message': 'API timeout 5s 초과 (재시도 성공)'},
    {'time': '06:18', 'system': 'WEARABLE',  'severity': 'ERROR', 'message': '인증 토큰 만료 (1회)'},
]


# ── Executive Dashboard 보조 카드 ─────────────────────────
MOCKUP_KPI_SUMMARY = {
    'total_customers': 100_000,
    'total_recommend': 1_234_890,
    'ctr_7d':              23.4,
    'cvr_7d':               4.8,
    'redis_cache_keys':  98_420,
    'redis_hit_rate':      87.3,
    'req_per_sec':         412,
    'p95_latency_ms':      138,
}

MOCKUP_S3_INGESTION = {
    'raw_bucket_files': 84_290,
    'today_ingested':   12_438,
    'iot_count':       284_113,
    'last_upload':     {'time': '09:14', 'file': 'wearable_2026-05-16.csv', 'size_mb': 2.3},
    'failed_count':     0,
}


# ── 운영 모니터링 — 도메인별 데이터 흐름 (S3 prefix 적재 현황) ──
MOCKUP_DOMAIN_FLOW = [
    {'domain': 'BANK',       'label': 'LS 은행',     'last_upload_at': '11:24:30', 'files_today':  144, 'state': 'OK',   'source': 's3://lifesync-raw/bank/'},
    {'domain': 'CARD',       'label': 'LS 카드',     'last_upload_at': '11:24:25', 'files_today':  144, 'state': 'OK',   'source': 's3://lifesync-raw/card/'},
    {'domain': 'INSURANCE',  'label': 'LS 보험',     'last_upload_at': '10:42:00', 'files_today':  120, 'state': 'WARN', 'source': 's3://lifesync-raw/insurance/'},
    {'domain': 'SECURITIES', 'label': 'LS 증권',     'last_upload_at': '11:24:32', 'files_today':  144, 'state': 'OK',   'source': 's3://lifesync-raw/securities/'},
    {'domain': 'HEALTHCARE', 'label': 'LS 헬스케어', 'last_upload_at': '11:24:28', 'files_today':  144, 'state': 'OK',   'source': 's3://lifesync-raw/healthcare/'},
    {'domain': 'HOSPITAL',   'label': 'LS 병원',     'last_upload_at': '11:24:31', 'files_today':  144, 'state': 'OK',   'source': 's3://lifesync-raw/hospital/'},
    {'domain': 'WEARABLE',   'label': '웨어러블',    'last_upload_at': '11:24:15', 'files_today': 2880, 'state': 'OK',   'source': 'Kinesis: lifesync-wearable-stream'},
]


# ── 운영 모니터링 — Group / Wearable VM ───────────────────
MOCKUP_VM_STATUS = [
    {'vm_id': 'i-0a1b...01', 'name': 'group-vm-1 (bank/card)',      'state': 'running', 'cpu_pct': 32, 'mem_pct': 58},
    {'vm_id': 'i-0a1b...02', 'name': 'group-vm-2 (insur/secur)',    'state': 'running', 'cpu_pct': 28, 'mem_pct': 61},
    {'vm_id': 'i-0a1b...03', 'name': 'group-vm-3 (health/hosp)',    'state': 'running', 'cpu_pct': 41, 'mem_pct': 70},
    {'vm_id': 'i-0a1b...04', 'name': 'wearable-vm-1 (agent)',       'state': 'running', 'cpu_pct': 55, 'mem_pct': 72},
]


# ── 운영 모니터링 — Lambda 호출률 (최근 1h) ───────────────
MOCKUP_LAMBDA_METRICS = [
    {'fn': 'lifesync-batch-loader-lambda',         'invocations_1h': 4_320, 'errors_1h': 0, 'avg_duration_ms':   412},
    {'fn': 'lifesync-ingest-lambda',               'invocations_1h': 8_640, 'errors_1h': 3, 'avg_duration_ms':   184},
    {'fn': 'lifesync-recommendation-engine-lambda','invocations_1h':    24, 'errors_1h': 0, 'avg_duration_ms': 2_310},
    {'fn': 'lifesync-wearable-stream-lambda',      'invocations_1h':12_480, 'errors_1h': 1, 'avg_duration_ms':    87},
]


# ── 운영 모니터링 — Glue ETL ──────────────────────────────
MOCKUP_GLUE_LAST_RUN = {
    'job_name':     'lifesync-glue-etl-processed',
    'state':        'SUCCEEDED',
    'started_at':   '2026-05-16 03:00:00',
    'completed_at': '2026-05-16 03:47:21',
    'duration_sec': 2_841,
}

MOCKUP_NEXT_BATCH = {
    'rule_name':         'lifesync-daily-etl-rule',
    'schedule':          'cron(0 3 * * ? *)',
    'next_scheduled_at': '2026-05-17 03:00:00',
}


# ── AI 추천 — 카테고리·등급별 + TOP10 (Aurora 쿼리 fallback) ──
MOCKUP_RECOMMEND_BY_CATEGORY = [
    {'category': '카드',     'ctr': 31.2, 'cvr': 8.7},
    {'category': '은행',     'ctr': 28.4, 'cvr': 9.1},
    {'category': '헬스케어', 'ctr': 25.8, 'cvr': 6.2},
    {'category': '보험',     'ctr': 19.1, 'cvr': 3.4},
    {'category': '증권',     'ctr': 22.4, 'cvr': 4.8},
]

MOCKUP_RECOMMEND_BY_GRADE = [
    {'grade': 'VIP',    'cvr': 12.4},
    {'grade': 'GOLD',   'cvr':  8.7},
    {'grade': 'SILVER', 'cvr':  5.2},
    {'grade': 'BASIC',  'cvr':  3.9},
    {'grade': 'CARE',   'cvr':  6.1},
]

MOCKUP_RECOMMEND_TOP10 = [
    {'rank':  1, 'product': 'VIP 신용카드',      'category': '카드',     'recommended': 12_840, 'ctr': 31.2, 'cvr': 8.7},
    {'rank':  2, 'product': 'PB 예금 패키지',    'category': '은행',     'recommended': 11_205, 'ctr': 28.4, 'cvr': 9.1},
    {'rank':  3, 'product': '건강검진 패키지',   'category': '헬스케어', 'recommended':  9_012, 'ctr': 25.8, 'cvr': 6.2},
    {'rank':  4, 'product': '암보험 라이트',     'category': '보험',     'recommended':  7_892, 'ctr': 22.4, 'cvr': 5.5},
    {'rank':  5, 'product': 'ISA 절세 상품',     'category': '증권',     'recommended':  6_521, 'ctr': 21.1, 'cvr': 4.8},
    {'rank':  6, 'product': 'VIP 헬스케어',      'category': '헬스케어', 'recommended':  5_914, 'ctr': 26.3, 'cvr': 7.1},
    {'rank':  7, 'product': '자동차 보험 비교',  'category': '보험',     'recommended':  4_820, 'ctr': 18.5, 'cvr': 3.4},
    {'rank':  8, 'product': '자유적금 플러스',   'category': '은행',     'recommended':  4_280, 'ctr': 19.8, 'cvr': 5.0},
    {'rank':  9, 'product': '걷기 챌린지 앱',    'category': '헬스케어', 'recommended':  3_812, 'ctr': 15.4, 'cvr': 2.1},
    {'rank': 10, 'product': '프리미엄 실손보험', 'category': '보험',     'recommended':  3_104, 'ctr': 17.2, 'cvr': 4.3},
]


# ── Cloud Status — AWS + GCP 통합 (Executive Dashboard) ───
# 실제 데이터 전송은 미구축이지만 멀티클라우드 아키텍처상 GCP 카드 표시.
MOCKUP_CLOUD_STATUS = [
    {'provider': 'AWS', 'service': 'Aurora',       'icon': '🗄', 'state': 'UP', 'note': 'writer 1 · reader 2',     'metric': 'conn 12% · P95 8ms'},
    {'provider': 'AWS', 'service': 'DynamoDB',     'icon': '⚡', 'state': 'UP', 'note': '4 tables · 1.2M items',   'metric': 'RCU 24 · WCU 8'},
    {'provider': 'AWS', 'service': 'ElastiCache',  'icon': '🔥', 'state': 'UP', 'note': 'cluster · 3 nodes',       'metric': '0.2ms · 99% hit'},
    {'provider': 'AWS', 'service': 'ECS',          'icon': '🐳', 'state': 'UP', 'note': '2/2 running',             'metric': 'CPU 32% · Mem 48%'},
    {'provider': 'AWS', 'service': 'ALB',          'icon': '🌐', 'state': 'UP', 'note': '2/2 healthy targets',     'metric': '24h 5xx 0.02%'},
    {'provider': 'AWS', 'service': 'S3',           'icon': '📦', 'state': 'UP', 'note': '6 buckets',               'metric': 'today 12.4K objs'},
    {'provider': 'GCP', 'service': 'BigQuery',     'icon': '📊', 'state': 'UP', 'note': 'dataset: lifesync_dwh',    'metric': '7d 142 jobs · 0 err'},
    {'provider': 'GCP', 'service': 'Vertex AI',    'icon': '🤖', 'state': 'UP', 'note': 'endpoint: nba-v2.3.1',     'metric': '24h 996K infer'},
]


# ── AI 추천 — Vertex AI KPI 4 (CTR/CVR/Accuracy/PR) ─────
MOCKUP_AI_KPI = {
    'ctr_7d':     23.4,
    'cvr_7d':      4.8,
    'accuracy':   87.4,
    'precision':   0.82,
    'recall':      0.79,
    'pr_combined': '0.82 / 0.79',
}


# ── Vertex AI — 모델 메트릭 + Feature Importance Top 8 ────
MOCKUP_VERTEX_AI = {
    'model_id':    'nba-recommender',
    'version':     'v2.3.1',
    'auc':         0.847,
    'accuracy':    0.874,
    'precision':   0.82,
    'recall':      0.79,
    'trained_at':  '2026-04-28 04:00:00',
    'endpoint':    'projects/lifesync-prod/locations/asia-northeast3/endpoints/nba-v2',
}

MOCKUP_FEATURE_IMPORTANCE = [
    {'name': 'age',                'score': 0.182},
    {'name': 'ai_score_prev',      'score': 0.156},
    {'name': 'wearable_avg_hr',    'score': 0.124},
    {'name': 'income_band',        'score': 0.108},
    {'name': 'recent_purchase',    'score': 0.094},
    {'name': 'session_count_7d',   'score': 0.076},
    {'name': 'city_tier',          'score': 0.062},
    {'name': 'campaign_response',  'score': 0.048},
]


# ── 운영 모니터링 — Transit Gateway / VPN / VPC Peering ───
MOCKUP_TGW = {
    'id':           'tgw-0a3b8c2d1e4f5g6h7',
    'state':        'available',
    'attachments':  3,
    'note':         'AWS Aurora VPC ↔ GCP VPN ↔ On-prem',
}

MOCKUP_VPN = {
    'tunnels': [
        {'id': 'tun-aws-gcp-1', 'status': 'UP', 'bgp_asn': 65000, 'traffic_in_mbps': 12.4, 'traffic_out_mbps': 8.2,  'peer': 'GCP Cloud VPN'},
        {'id': 'tun-aws-gcp-2', 'status': 'UP', 'bgp_asn': 65000, 'traffic_in_mbps': 11.8, 'traffic_out_mbps': 7.9,  'peer': 'GCP Cloud VPN'},
        {'id': 'tun-aws-onprem', 'status': 'UP', 'bgp_asn': 65100, 'traffic_in_mbps':  2.1, 'traffic_out_mbps': 0.9, 'peer': 'On-prem strongSwan'},
    ],
}

MOCKUP_VPC_PEERING = [
    {'id': 'pcx-platform-aurora',  'state': 'active', 'requester': 'Platform VPC',   'accepter': 'Aurora VPC'},
    {'id': 'pcx-platform-onprem',  'state': 'active', 'requester': 'Platform VPC',   'accepter': 'Management VPC (TGW)'},
]


# ── 운영 모니터링 — Wearable VM 실시간 메트릭 6행 ─────────
MOCKUP_WEARABLE_REALTIME = [
    {'metric': '심박수',        'current': '78 bpm',  'range': '60-100',     'state': 'OK',   'source': 'CW custom · wearable_hr'},
    {'metric': '혈압',          'current': '118/76',  'range': '< 120/80',   'state': 'OK',   'source': 'CW custom · wearable_bp'},
    {'metric': '산소포화도',    'current': '98%',     'range': '≥ 95',       'state': 'OK',   'source': 'CW custom · wearable_spo2'},
    {'metric': '운동량 (steps)','current': '6,420',   'range': '—',          'state': 'OK',   'source': 'CW custom · wearable_steps'},
    {'metric': '이상 이벤트',   'current': '2 alerts','range': '24h',        'state': 'WARN', 'source': 'CW Logs Insights'},
    {'metric': '데이터 송신',   'current': '412/min', 'range': '—',          'state': 'OK',   'source': 'Kinesis IncomingRecords'},
]


# ── 운영 모니터링 — Local Lab (VirtualBox / Docker) ───────
# 아키텍처 V3.7 Lite 기준 K8s 없음. VirtualBox 4 + Docker 만 노출.
MOCKUP_LOCAL_LAB = [
    {'env': 'VirtualBox · ls-vpngw',  'state': 'Running', 'note': 'strongSwan VPN · 192.168.56.10'},
    {'env': 'VirtualBox · ls-db',     'state': 'Running', 'note': 'MySQL 8.0 · 192.168.56.11'},
    {'env': 'VirtualBox · ls-token',  'state': 'Running', 'note': 'Tokenization · 192.168.56.12'},
    {'env': 'VirtualBox · ls-api',    'state': 'Running', 'note': 'Private API + cron · 192.168.56.13'},
    {'env': 'Docker · flask-app',     'state': 'Running', 'note': 'lifesync360-platform · port 80'},
]


# ── Customer 360 — Redis Personalized Top 3 (mock) ────────
MOCKUP_REDIS_PERSONALIZED = {
    'top3': [
        {'rank': 1, 'product': 'PB 예금 패키지',   'category': '은행',     'ai_score': 0.92, 'color': '#8b5cf6'},
        {'rank': 2, 'product': 'VIP 신용카드',     'category': '카드',     'ai_score': 0.88, 'color': '#3b82f6'},
        {'rank': 3, 'product': '건강검진 패키지',  'category': '헬스케어', 'ai_score': 0.85, 'color': '#14b8a6'},
    ],
    'crosssell_count': 12,
    'crosssell_note':  '보험·헬스 추천 풀 12건',
    'source':          'Redis key: recommend:{global_id}',
    'ttl_minutes':     360,
}

# Customer 360 — 교차판매 추천 리스트 (slide2 하단 박스)
MOCKUP_CROSSSELL_LIST = [
    {'product': '암 보험 라이트',       'category': '보험',    'reason': '건강 점수 78 · 40대 평균'},
    {'product': '실손 보험 플러스',     'category': '보험',    'reason': '미가입 + 동의 Y'},
    {'product': '건강검진 정기 패키지', 'category': '헬스케어','reason': '연간 추천 1회'},
    {'product': '여행자 보험',          'category': '보험',    'reason': '계절성 (여름 시즌)'},
    {'product': '단기 적금 6개월',      'category': '은행',    'reason': 'AI Score 82 추천'},
]


# ── Customer 360 — 상단 KPI 카드 ───────────────────────────
MOCKUP_CUSTOMER_KPI = {
    'total_customers':   100_000,
    'vip_gold_count':      4_810,
    'vip_gold_pct':            4.8,
    'active_campaigns':        7,
    'new_signup_24h':        238,
    'avg_ai_score':         72.4,
}


# ── AI 추천 — AI Score (DynamoDB dynamic_score) 분포 ──────
MOCKUP_SCORE_DISTRIBUTION = {
    'dynamic_score': [
        {'bucket': '0-20',   'count':    342},
        {'bucket': '20-40',  'count':  4_281},
        {'bucket': '40-60',  'count': 18_512},
        {'bucket': '60-80',  'count': 48_204},
        {'bucket': '80-100', 'count': 28_661},
    ],
}


# ── Executive Dashboard — PPTX slide1 도형 의도 ──────────
# 상단 5 KPI
MOCKUP_KPI_TOP = [
    {'label': '총 고객 수',     'value': '100,000',    'sub': '활성 고객',                                        'color': '#6366f1'},
    {'label': '추천 이력 수',   'value': '1,234,890',  'sub': '누적 추천 건수',                                   'color': '#3b82f6'},
    {'label': '24h 활성 (DAU)', 'value': '18,420 명',  'sub': '세션 21,840 · 세션당 4.2 · 재방문 1.2x',          'color': '#14b8a6'},
    {'label': '추천 CTR',       'value': '23.4%',      'sub': '클릭률 7d 평균',                                   'color': '#f59e0b'},
    {'label': '구매 전환률',    'value': '4.8%',       'sub': '구매 전환 7d 평균',                                'color': '#16a34a'},
]

# 중단 4 KPI
MOCKUP_KPI_MID = [
    {'label': 'AI 추천 상태',       'value': '● UP',        'sub': 'nba-recommender v2.3.1',  'color': '#16a34a'},
    {'label': 'Redis 추천 Cache 수','value': '98,420 keys', 'sub': 'hit-rate 87.3%',          'color': '#8b5cf6'},
    {'label': '웨어러블 건수',      'value': '284,113',     'sub': 'IoT 데이터 24h',          'color': '#14b8a6'},
    {'label': '고객 데이터 적재량', 'value': '1.4 TB',      'sub': '누적 적재',                'color': '#14b8a6'},
]

# 메인 큰 박스 1 — AWS 상태 상세 (5.4 x 13.1cm, 세로 리스트)
MOCKUP_AWS_STATUS_DETAIL = [
    {'service': 'Aurora MySQL',     'state': 'UP', 'metric': 'writer 1 · reader 2',       'detail': 'conn 12% · P95 8ms'},
    {'service': 'DynamoDB',         'state': 'UP', 'metric': '4 tables · 1.2M items',     'detail': 'RCU 24 · WCU 8'},
    {'service': 'ElastiCache Redis','state': 'UP', 'metric': 'cluster · 3 nodes',         'detail': '0.2ms · 99% hit'},
    {'service': 'ECS',              'state': 'UP', 'metric': '2/2 running',               'detail': 'CPU 32% · Mem 48%'},
    {'service': 'ALB',              'state': 'UP', 'metric': '2/2 healthy targets',       'detail': '24h 5xx 0.02%'},
    {'service': 'S3',               'state': 'UP', 'metric': '6 buckets',                 'detail': 'today 12.4K objs'},
]

# 메인 큰 박스 2 — GCP 상태 상세 (7.8 x 8.2cm)
MOCKUP_GCP_STATUS_DETAIL = [
    {'service': 'BigQuery',  'state': 'UP', 'metric': 'lifesync_dwh',          'detail': '7d 142 jobs · 0 err'},
    {'service': 'Vertex AI', 'state': 'UP', 'metric': 'nba-recommender v2.3.1','detail': '24h 996K infer'},
]

# 메인 큰 박스 3 — S3 적재 상세 (7.1 x 7.9cm, "오늘 적재 건수" 위치)
MOCKUP_S3_INGESTION_BOX = [
    {'label': 'Raw Bucket 파일 수',    'value': '84,290',       'note': 's3://lifesync-raw'},
    {'label': '오늘 적재 건수',        'value': '12,438',       'note': '+8% vs 어제'},
    {'label': '웨어러블 / IoT 적재량', 'value': '284,113',      'note': 'kinesis 5min sum'},
    {'label': '처리 실패',             'value': '0',            'note': '오류 없음'},
    {'label': '최근 업로드',           'value': '09:14',        'note': 'wearable_2026-05-16.csv 2.3MB'},
]

# 메인 큰 박스 4 — 플랫폼 가입률 (8.8 x 8.2cm, 전체 + 5 연령별)
MOCKUP_SIGNUP_BOX = {
    'overall': 64.2,
    'by_age': [
        {'age': '20대',  'signup_rate': 71.2, 'count': 18_400},
        {'age': '30대',  'signup_rate': 68.4, 'count': 24_120},
        {'age': '40대',  'signup_rate': 62.1, 'count': 27_810},
        {'age': '50대',  'signup_rate': 54.8, 'count': 19_220},
        {'age': '60대~', 'signup_rate': 41.3, 'count': 10_450},
    ],
}

# 하단 박스 — 최근 업로드 파일 리스트 (14.1 x 4.4cm)
MOCKUP_RECENT_UPLOADS = [
    {'time': '09:14:32', 'file': 'wearable_2026-05-16.csv',       'size': '2.3 MB',  'source': 'Kinesis · wearable-stream', 'state': 'OK'},
    {'time': '09:12:08', 'file': 'bank/dt=2026-05-16/batch-001.json','size': '1.7 MB','source': 's3://lifesync-raw/bank/',  'state': 'OK'},
    {'time': '09:08:21', 'file': 'card/dt=2026-05-16/batch-001.json','size': '1.2 MB','source': 's3://lifesync-raw/card/',  'state': 'OK'},
    {'time': '09:05:44', 'file': 'consent-filter/20260516/consented_customers.csv.gz', 'size': '8.4 MB', 'source': 'consent_filter Lambda', 'state': 'OK'},
    {'time': '09:00:12', 'file': 'healthcare/dt=2026-05-16/batch-001.json', 'size': '0.9 MB', 'source': 's3://lifesync-raw/healthcare/', 'state': 'OK'},
]


# ── Executive Dashboard — 연령별 가입률 분포 (5행) ────────
MOCKUP_AGE_SIGNUP_RATE = [
    {'age': '20대',  'signup_rate': 71.2, 'count': 18_400},
    {'age': '30대',  'signup_rate': 68.4, 'count': 24_120},
    {'age': '40대',  'signup_rate': 62.1, 'count': 27_810},
    {'age': '50대',  'signup_rate': 54.8, 'count': 19_220},
    {'age': '60대~', 'signup_rate': 41.3, 'count': 10_450},
]


# ── AI 추천 — 연령별 모델 비율 (Slide 3) ────────────────
MOCKUP_AGE_MODEL_RATIO = [
    {'age': '20대',  'ratio': 18.4, 'top_category': '카드'},
    {'age': '30대',  'ratio': 24.1, 'top_category': '은행'},
    {'age': '40대',  'ratio': 27.8, 'top_category': '보험'},
    {'age': '50대',  'ratio': 19.2, 'top_category': '헬스케어'},
    {'age': '60대~', 'ratio': 10.5, 'top_category': '병원'},
]


# ── AI 추천 — 추천 Trend (7일 시계열: CTR/CVR/추천 수) ─────
MOCKUP_RECOMMEND_TREND = [
    {'date': '05-09', 'recommended': 142_521, 'ctr': 21.4, 'cvr': 4.2},
    {'date': '05-10', 'recommended': 148_302, 'ctr': 22.8, 'cvr': 4.5},
    {'date': '05-11', 'recommended': 151_120, 'ctr': 23.1, 'cvr': 4.6},
    {'date': '05-12', 'recommended': 155_887, 'ctr': 24.0, 'cvr': 4.9},
    {'date': '05-13', 'recommended': 156_032, 'ctr': 24.2, 'cvr': 5.0},
    {'date': '05-14', 'recommended': 156_198, 'ctr': 23.9, 'cvr': 4.8},
    {'date': '05-15', 'recommended': 156_341, 'ctr': 23.4, 'cvr': 4.8},
]


# ── 운영 모니터링 — 7 계열사별 헬스 (Slide 4) ─────────────
MOCKUP_AFFILIATE_HEALTH = [
    {'affiliate': '은행',       'cpu_pct': 32, 'mem_pct': 58, 'api_state': 'UP',   'last_ping': '11:24:30'},
    {'affiliate': '카드',       'cpu_pct': 28, 'mem_pct': 61, 'api_state': 'UP',   'last_ping': '11:24:25'},
    {'affiliate': '보험',       'cpu_pct': 41, 'mem_pct': 70, 'api_state': 'SLOW', 'last_ping': '11:23:50'},
    {'affiliate': '인터넷보험', 'cpu_pct': 19, 'mem_pct': 44, 'api_state': 'UP',   'last_ping': '11:24:18'},
    {'affiliate': '증권',       'cpu_pct': 35, 'mem_pct': 52, 'api_state': 'UP',   'last_ping': '11:24:32'},
    {'affiliate': '헬스케어',   'cpu_pct': 47, 'mem_pct': 65, 'api_state': 'UP',   'last_ping': '11:24:28'},
    {'affiliate': '병원',       'cpu_pct': 25, 'mem_pct': 49, 'api_state': 'UP',   'last_ping': '11:24:31'},
]


# ── 운영 모니터링 — 백엔드 서비스 상태 (Slide 4) ──────────
MOCKUP_BACKEND_SERVICES = [
    {'service': '통합고객 DB',              'state': 'UP', 'note': 'Aurora MySQL 8.0 · writer 1 / reader 2'},
    {'service': 'Token 서버',               'state': 'UP', 'note': 'onprem ls-token · AES-GCM'},
    {'service': 'API 서버',                 'state': 'UP', 'note': 'onprem ls-api · FastAPI'},
    {'service': '회원가입 / 고객정보 조회', 'state': 'UP', 'note': 'PrivateAPI /internal/auth, /internal/customer'},
    {'service': '동의고객 데이터 적재',     'state': 'UP', 'note': 'consent_filter Lambda · 일배치'},
    {'service': 'Ansible 자동화',           'state': 'UP', 'note': 'Control Node · last run 03:00'},
]

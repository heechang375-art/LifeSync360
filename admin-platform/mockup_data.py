"""시안용 mock 데이터 — 정식 mock_data.py와 분리.

이 파일의 모든 데이터는 시안(mockup) 전용으로 임의 작성됨.
운영 모드에서는 사용되지 않음.
"""

# ── 운영 모니터링 (개요 + 서버 상태 통합 시안) ─────────────
MOCKUP_ETL_LAST_RUN = {
    'job_name':       'gcp_consent_filter',
    'completed_at':   '2026-05-15 09:00:12',
    'duration_sec':   1287,
    'status':         'SUCCESS',
    'rows_processed': 7_658_421,
}

MOCKUP_ETL_NEXT = {
    'job_name':     'daily_full_sync',
    'scheduled_at': '2026-05-15 21:00:00',
}

MOCKUP_EXTERNAL_SYSTEMS = [
    {'system': 'BANK',       'label': 'LS 은행',     'status': 'OK',   'response_ms':  142, 'last_call': '11:24:30'},
    {'system': 'CARD',       'label': 'LS 카드',     'status': 'OK',   'response_ms':   98, 'last_call': '11:24:25'},
    {'system': 'INSURANCE',  'label': 'LS 보험',     'status': 'WARN', 'response_ms': 2450, 'last_call': '11:23:50', 'note': 'P95 응답지연 초과'},
    {'system': 'SECURITIES', 'label': 'LS 증권',     'status': 'OK',   'response_ms':  187, 'last_call': '11:24:32'},
    {'system': 'HEALTHCARE', 'label': 'LS 헬스케어', 'status': 'OK',   'response_ms':  156, 'last_call': '11:24:28'},
    {'system': 'HOSPITAL',   'label': 'LS 병원',     'status': 'OK',   'response_ms':  203, 'last_call': '11:24:31'},
    {'system': 'WEARABLE',   'label': '웨어러블',    'status': 'OK',   'response_ms':   89, 'last_call': '11:24:15'},
]

MOCKUP_RECENT_ERRORS = [
    {'time': '10:42', 'system': 'INSURANCE', 'severity': 'WARN',  'message': 'API timeout 5s 초과 (재시도 성공)'},
    {'time': '06:18', 'system': 'WEARABLE',  'severity': 'ERROR', 'message': '인증 토큰 만료 (1회)'},
]

MOCKUP_INFRA = [
    {'name': 'ECS Service', 'icon': '🐳', 'status': 'OK',   'detail': '2/2 running',         'metric': 'CPU 32% · Mem 48%'},
    {'name': 'Aurora',      'icon': '🗄', 'status': 'OK',   'detail': 'aurora-mysql 5.7',    'metric': '12% conn · 8ms P95'},
    {'name': 'DynamoDB',    'icon': '⚡', 'status': 'OK',   'detail': '4 tables · 1.2M items', 'metric': 'RCU 24 · WCU 8'},
    {'name': 'Redis',       'icon': '🔥', 'status': 'OK',   'detail': '64MB used / 256MB',   'metric': '0.2ms · 99% hit'},
    {'name': 'ALB',         'icon': '🌐', 'status': 'OK',   'detail': '2/2 healthy targets', 'metric': '24h 5xx 0.02%'},
]


# ── 분석 데이터 시안 (추가 카드) ─────────────────────────
MOCKUP_PII_STATUS = {
    'pii_columns': [
        {'column': 'name_enc',    'filled_pct': 99.98},
        {'column': 'rrn_enc',     'filled_pct': 99.95},
        {'column': 'mobile_enc',  'filled_pct': 99.82},
        {'column': 'email_enc',   'filled_pct': 98.65},
        {'column': 'address_enc', 'filled_pct': 97.42},
    ],
    'pii_token_pattern_ok': 99.99,
    'token_map_unique':     True,
    'orphan_count':         0,
}

MOCKUP_AI_MODEL = {
    'model_name':          'lifesync_dynamic_grade_v2',
    'version':             'v2.3.1',
    'trained_at':          '2026-05-10 04:00:00',
    'features':            ['health_score', 'fin_score', 'behavior_score', 'age_band',
                            'income_grade', 'asset_grade', 'wearable_flag', 'consent_count'],
    'algorithm':           'XGBoost (gbtree, depth=6)',
    'auc':                 0.842,
    'last_inferred_at':    '2026-05-15 09:00:12',
    'inference_count_24h': 996_341,
}

MOCKUP_ANALYSIS_TREND = [
    {'date': '05-09', 'count': 993_211},
    {'date': '05-10', 'count': 994_502},
    {'date': '05-11', 'count': 995_120},
    {'date': '05-12', 'count': 995_887},
    {'date': '05-13', 'count': 996_032},
    {'date': '05-14', 'count': 996_198},
    {'date': '05-15', 'count': 996_341},
]


# ── 고객 360도 뷰 시안 ────────────────────────────────────
MOCKUP_CUSTOMER = {
    'global_id':         'G000297409',
    'ls_user_id':        'LS-AABBCC11-000001',
    'name':              '김철수',
    'email':             'test@lifesync.com',
    'grade':             'VIP',
    'status':            'ACTIVE',
    # 인구통계 (customer_360_profile)
    'gender':            '남성',
    'age_band':          '40대',
    'region':            '서울',
    'income_grade':      '높음',
    'asset_grade':       '높음',
    'wearable_flag':     '연동',
    'first_created_dt':  '2022-03-15',
    'last_login_dt':     '2026-05-15 09:30',
    # 등급/점수/NBA (DynamoDB lifesync_customer_result)
    'dynamic_score':     92.4,
    'health_score':      88,
    'fin_score':         85,
    'behavior_score':    76,
    'next_best_action':  '프리미엄 건강검진 예약하기',
    'vip_prob':          0.85,
    'signup_prob':       0.72,
    'rec_prob':          0.91,
    # LTV / 그룹 기여도 (분석문서 C-5)
    'ltv_estimated':     12_500_000,
    'group_contribution': [
        {'domain': 'BANK',       'label': 'LS 은행',     'amount': 4_200_000},
        {'domain': 'CARD',       'label': 'LS 카드',     'amount': 3_100_000},
        {'domain': 'INSURANCE',  'label': 'LS 보험',     'amount': 2_800_000},
        {'domain': 'SECURITIES', 'label': 'LS 증권',     'amount': 1_400_000},
        {'domain': 'HEALTHCARE', 'label': 'LS 헬스케어', 'amount':   600_000},
        {'domain': 'HOSPITAL',   'label': 'LS 병원',     'amount':   400_000},
    ],
    # 7 도메인 매핑·동의 매트릭스
    'identities': [
        {'domain': 'BANK',       'label': 'LS 은행',     'mapped': True,  'match_type': 'EXACT',     'consented': True,  'linked_at': '2026-04-20', 'affiliate_id': 'BK-000001'},
        {'domain': 'CARD',       'label': 'LS 카드',     'mapped': True,  'match_type': 'EXACT',     'consented': True,  'linked_at': '2026-04-20', 'affiliate_id': 'CD-000001'},
        {'domain': 'INSURANCE',  'label': 'LS 보험',     'mapped': True,  'match_type': 'FUZZY 95%', 'consented': False, 'linked_at': '2026-04-21', 'affiliate_id': 'IN-000001'},
        {'domain': 'SECURITIES', 'label': 'LS 증권',     'mapped': False, 'match_type': None,        'consented': False, 'linked_at': None,         'affiliate_id': None},
        {'domain': 'HEALTHCARE', 'label': 'LS 헬스케어', 'mapped': True,  'match_type': 'EXACT',     'consented': True,  'linked_at': '2026-04-23', 'affiliate_id': 'HC-000001'},
        {'domain': 'HOSPITAL',   'label': 'LS 병원',     'mapped': False, 'match_type': None,        'consented': False, 'linked_at': None,         'affiliate_id': None},
        {'domain': 'WEARABLE',   'label': '웨어러블',    'mapped': False, 'match_type': None,        'consented': False, 'linked_at': None,         'affiliate_id': None},
    ],
    # 추천 이력
    'recommend_history': [
        {'product': 'VIP 종합 건강검진',   'at': '2026-05-04 10:00', 'status': '구매완료'},
        {'product': 'VIP 자산관리 서비스', 'at': '2026-05-03 09:00', 'status': '클릭'},
        {'product': '프리미엄 실손보험',   'at': '2026-05-01 08:00', 'status': '추천됨'},
        {'product': '걷기 챌린지',         'at': '2026-04-28 12:00', 'status': '구매완료'},
        {'product': 'ISA 통합계좌',        'at': '2026-04-25 11:00', 'status': '클릭'},
    ],
    # PII 토큰
    'pii_token':     'PII-7f3a1b2c8d9e4f01',
    'token_created': '2022-03-15 10:00',
    # 매칭 audit log 요약
    'audit_summary': {
        'total_attempts':  8,
        'matched':         4,
        'no_match':        4,
        'last_attempt_at': '2026-04-23 11:00',
    },
}

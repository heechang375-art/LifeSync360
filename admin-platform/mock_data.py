MOCK_USERS = [
    {'ls_user_id': 'LS-20260423-000001', 'global_id': 'G001', 'name': '김철수', 'email': 'test@lifesync.com',  'grade': 'PLATINUM'},
    {'ls_user_id': 'LS-20260423-000002', 'global_id': 'G002', 'name': '이영희', 'email': 'lee@lifesync.com',   'grade': 'GOLD'},
    {'ls_user_id': 'LS-20260423-000003', 'global_id': 'G003', 'name': '박민준', 'email': 'park@lifesync.com',  'grade': 'SILVER'},
    {'ls_user_id': 'LS-20260423-000004', 'global_id': 'G004', 'name': '정수연', 'email': 'jung@lifesync.com',  'grade': 'BRONZE'},
    {'ls_user_id': 'LS-20260423-000005', 'global_id': 'G005', 'name': '최동훈', 'email': 'choi@lifesync.com',  'grade': 'BASIC'},
    {'ls_user_id': 'LS-20260423-000006', 'global_id': 'G006', 'name': '한지민', 'email': 'han@lifesync.com',   'grade': 'GOLD'},
    {'ls_user_id': 'LS-20260423-000007', 'global_id': 'G007', 'name': '오세진', 'email': 'oh@lifesync.com',    'grade': 'SILVER'},
]

MOCK_SCORES = {
    'G001': {'dynamic_score': '92.4', 'health_score': '88', 'fin_score': '85', 'behavior_score': '76',
             'dynamic_grade': 'VIP',    'next_best_action': 'VIP 종합 건강검진 예약을 권장합니다',  'vip_prob': '0.94', 'signup_prob': '0.81', 'rec_prob': '0.77', 'update_time': '2026-05-04T14:30:00'},
    'G002': {'dynamic_score': '75.2', 'health_score': '72', 'fin_score': '80', 'behavior_score': '68',
             'dynamic_grade': 'GOLD',   'next_best_action': '자유적금 플러스 가입을 권장합니다',    'vip_prob': '0.45', 'signup_prob': '0.62', 'rec_prob': '0.55', 'update_time': '2026-05-04T13:20:00'},
    'G003': {'dynamic_score': '61.8', 'health_score': '58', 'fin_score': '65', 'behavior_score': '55',
             'dynamic_grade': 'SILVER', 'next_best_action': '걷기 챌린지 참여를 권장합니다',        'vip_prob': '0.12', 'signup_prob': '0.34', 'rec_prob': '0.28', 'update_time': '2026-05-03T10:00:00'},
    'G006': {'dynamic_score': '78.1', 'health_score': '80', 'fin_score': '74', 'behavior_score': '70',
             'dynamic_grade': 'GOLD',   'next_best_action': '건강지킴이 보험 가입을 권장합니다',    'vip_prob': '0.38', 'signup_prob': '0.58', 'rec_prob': '0.49', 'update_time': '2026-05-04T09:10:00'},
}

MOCK_CONSENTS = {
    'G001': [
        {'consent_key': 'bank',               'consent_yn': 'Y', 'updated_at': '2026-04-20 10:00:00'},
        {'consent_key': 'card',               'consent_yn': 'Y', 'updated_at': '2026-04-20 10:00:00'},
        {'consent_key': 'insurance',          'consent_yn': 'Y', 'updated_at': '2026-04-20 10:00:00'},
        {'consent_key': 'internet_insurance', 'consent_yn': 'N', 'updated_at': '2026-04-20 10:00:00'},
        {'consent_key': 'securities',         'consent_yn': 'Y', 'updated_at': '2026-04-20 10:00:00'},
        {'consent_key': 'healthcare',         'consent_yn': 'Y', 'updated_at': '2026-04-20 10:00:00'},
        {'consent_key': 'hospital',           'consent_yn': 'N', 'updated_at': '2026-04-20 10:00:00'},
    ],
    'G002': [
        {'consent_key': 'bank',      'consent_yn': 'Y', 'updated_at': '2026-04-21 09:30:00'},
        {'consent_key': 'card',      'consent_yn': 'N', 'updated_at': '2026-04-21 09:30:00'},
        {'consent_key': 'insurance', 'consent_yn': 'Y', 'updated_at': '2026-04-21 09:30:00'},
        {'consent_key': 'hospital',  'consent_yn': 'Y', 'updated_at': '2026-04-21 09:30:00'},
    ],
    'G003': [
        {'consent_key': 'bank', 'consent_yn': 'N', 'updated_at': '2026-04-22 14:00:00'},
        {'consent_key': 'card', 'consent_yn': 'N', 'updated_at': '2026-04-22 14:00:00'},
    ],
    'G006': [
        {'consent_key': 'bank',       'consent_yn': 'Y', 'updated_at': '2026-04-23 11:00:00'},
        {'consent_key': 'healthcare', 'consent_yn': 'Y', 'updated_at': '2026-04-23 11:00:00'},
        {'consent_key': 'hospital',   'consent_yn': 'Y', 'updated_at': '2026-04-23 11:00:00'},
    ],
}

MOCK_RECOMMEND_HISTORY = {
    'G001': [
        {'product_name': 'VIP 종합 건강검진',       'recommended_at': '2026-05-04 10:00:00', 'clicked_at': '2026-05-04 10:30:00', 'purchased_at': '2026-05-04 11:00:00'},
        {'product_name': 'PLATINUM 자산관리 서비스', 'recommended_at': '2026-05-03 09:00:00', 'clicked_at': '2026-05-03 09:15:00', 'purchased_at': None},
        {'product_name': '프리미엄 실손보험',        'recommended_at': '2026-05-01 08:00:00', 'clicked_at': None,                  'purchased_at': None},
    ],
    'G002': [
        {'product_name': '자유적금 플러스',  'recommended_at': '2026-05-04 08:00:00', 'clicked_at': None,                  'purchased_at': None},
        {'product_name': '건강보험 GOLD',   'recommended_at': '2026-05-02 14:00:00', 'clicked_at': '2026-05-02 15:00:00', 'purchased_at': None},
    ],
    'G003': [],
    'G006': [
        {'product_name': '건강지킴이 보험', 'recommended_at': '2026-05-03 14:00:00', 'clicked_at': '2026-05-03 15:00:00', 'purchased_at': '2026-05-03 16:30:00'},
    ],
}

MOCK_IDENTITIES = {
    'G001': [
        {'company_id': 'bank',      'affiliate_customer_id': 'BK-000001', 'linked_at': '2026-04-20 10:00:00'},
        {'company_id': 'card',      'affiliate_customer_id': 'CD-000001', 'linked_at': '2026-04-20 10:00:00'},
        {'company_id': 'insurance', 'affiliate_customer_id': 'IN-000001', 'linked_at': '2026-04-21 09:00:00'},
        {'company_id': 'hospital',  'affiliate_customer_id': 'HP-000001', 'linked_at': '2026-04-22 11:00:00'},
    ],
    'G002': [
        {'company_id': 'bank',     'affiliate_customer_id': 'BK-000002', 'linked_at': '2026-04-21 09:30:00'},
        {'company_id': 'hospital', 'affiliate_customer_id': 'HP-000002', 'linked_at': '2026-04-21 10:00:00'},
    ],
    'G003': [],
    'G006': [
        {'company_id': 'bank',       'affiliate_customer_id': 'BK-000006', 'linked_at': '2026-04-23 11:00:00'},
        {'company_id': 'healthcare', 'affiliate_customer_id': 'HC-000006', 'linked_at': '2026-04-23 11:30:00'},
    ],
}

MOCK_CAMPAIGNS = [
    {'campaign_id': 'C001', 'campaign_name': 'VIP 건강검진 패키지',  'target_grade': 'PLATINUM', 'start_dt': '2026-05-01', 'end_dt': '2026-05-31'},
    {'campaign_id': 'C002', 'campaign_name': '봄맞이 저축 캠페인',   'target_grade': 'GOLD',     'start_dt': '2026-04-15', 'end_dt': '2026-05-15'},
    {'campaign_id': 'C003', 'campaign_name': '건강 걷기 챌린지',     'target_grade': 'BASIC',    'start_dt': '2026-05-01', 'end_dt': '2026-06-30'},
]

MOCK_RECENT_RECOMMENDS = [
    {'global_id': 'G001', 'product_name': 'VIP 종합 건강검진',      'recommended_at': '2026-05-04 10:00:00', 'clicked_at': '2026-05-04 10:30:00', 'purchased_at': '2026-05-04 11:00:00'},
    {'global_id': 'G002', 'product_name': '자유적금 플러스',         'recommended_at': '2026-05-04 08:00:00', 'clicked_at': None,                  'purchased_at': None},
    {'global_id': 'G006', 'product_name': '건강지킴이 보험',         'recommended_at': '2026-05-03 14:00:00', 'clicked_at': '2026-05-03 15:00:00', 'purchased_at': '2026-05-03 16:30:00'},
    {'global_id': 'G001', 'product_name': 'PLATINUM 자산관리 서비스','recommended_at': '2026-05-03 09:00:00', 'clicked_at': '2026-05-03 09:15:00', 'purchased_at': None},
    {'global_id': 'G003', 'product_name': '걷기 챌린지 앱',          'recommended_at': '2026-05-02 11:00:00', 'clicked_at': None,                  'purchased_at': None},
]

# 상품별 추천→클릭→가입 집계 (click_rate / purchase_rate는 app.py에서 계산)
MOCK_PRODUCT_FUNNEL = [
    {'product_name': '건강지킴이 보험',         'affiliate': 'insurance',  'recommended': 12, 'clicked': 8, 'purchased': 5},
    {'product_name': 'VIP 종합 건강검진',        'affiliate': 'healthcare', 'recommended': 9,  'clicked': 7, 'purchased': 4},
    {'product_name': '자유적금 플러스',          'affiliate': 'bank',       'recommended': 15, 'clicked': 6, 'purchased': 3},
    {'product_name': 'PLATINUM 자산관리 서비스', 'affiliate': 'securities', 'recommended': 7,  'clicked': 4, 'purchased': 2},
    {'product_name': '건강보험 GOLD',            'affiliate': 'insurance',  'recommended': 11, 'clicked': 5, 'purchased': 2},
    {'product_name': '프리미엄 실손보험',        'affiliate': 'insurance',  'recommended': 8,  'clicked': 2, 'purchased': 0},
    {'product_name': '걷기 챌린지 앱',           'affiliate': 'healthcare', 'recommended': 6,  'clicked': 1, 'purchased': 0},
]

# 상품 조회수 TOP 5 (event_type='product_view' 집계)
MOCK_TOP_VIEWED = [
    {'event_target': '건강지킴이 보험',         'count': 34},
    {'event_target': '자유적금 플러스',          'count': 28},
    {'event_target': 'VIP 종합 건강검진',        'count': 22},
    {'event_target': '프리미엄 실손보험',        'count': 19},
    {'event_target': 'PLATINUM 자산관리 서비스', 'count': 15},
]

# 탭별 클릭 현황 (event_type='tab_click' 집계)
MOCK_TAB_CLICKS = [
    {'event_target': '건강',   'count': 89},
    {'event_target': '금융',   'count': 67},
    {'event_target': '보험',   'count': 54},
    {'event_target': '포인트', 'count': 38},
    {'event_target': '마이',   'count': 31},
]

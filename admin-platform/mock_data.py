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

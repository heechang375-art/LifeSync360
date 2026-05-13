import json
from pathlib import Path
from werkzeug.security import generate_password_hash
from upgrade_actions_engine import get_personalized_actions

_PRODUCTS_DIR = Path(__file__).parent.parent / 'data' / 'products'

# ── 사용자 (3명) ──────────────────────────────────────────────────
MOCK_USERS = {
    'test@lifesync.com': {
        'ls_user_id':    'LS-AABBCC11-000001',
        'global_id':     'G000000001',
        'name':          '김철수',
        'email':         'test@lifesync.com',
        'password_hash': generate_password_hash('password123'),
        'grade':         'PLATINUM',
    },
    'test2@lifesync.com': {
        'ls_user_id':    'LS-DDEEFF22-000002',
        'global_id':     'G000000002',
        'name':          '이수진',
        'email':         'test2@lifesync.com',
        'password_hash': generate_password_hash('password123'),
        'grade':         'GOLD',
    },
    'test3@lifesync.com': {
        'ls_user_id':    'LS-99AABB33-000003',
        'global_id':     'G000000003',
        'name':          '박지훈',
        'email':         'test3@lifesync.com',
        'password_hash': generate_password_hash('password123'),
        'grade':         'SILVER',
    },
}

# ── 건강 데이터 (ls_user_id 기준) ─────────────────────────────────
# breakdown: 심혈관 max 35 / 활동 max 35 / 신체지표 max 20 / 임상 max 10
_HEALTH_BY_USER = {
    'LS-AABBCC11-000001': {
        'dynamic_score': 92.4, 'health_score': 88, 'fin_score': 85, 'behavior_score': 76,
        'breakdown': [
            {'label': '심혈관',   'score': 32, 'max': 35},
            {'label': '활동',     'score': 31, 'max': 35},
            {'label': '신체지표', 'score': 17, 'max': 20},
            {'label': '임상',     'score': 8,  'max': 10},
        ],
        'indicators': [
            {'label': '혈당',   'status': 'NORMAL'},
            {'label': '지질',   'status': 'CAUTION'},
            {'label': '간기능', 'status': 'NORMAL'},
            {'label': '신장',   'status': 'NORMAL'},
        ],
        'spending': [
            {'label': '식품',   'pct': 38},
            {'label': '쇼핑',   'pct': 22},
            {'label': '의료',   'pct': 15},
            {'label': '교통',   'pct': 14},
            {'label': '여가',   'pct': 11},
        ],
    },
    'LS-DDEEFF22-000002': {
        'dynamic_score': 74.0, 'health_score': 72, 'fin_score': 68, 'behavior_score': 81,
        'breakdown': [
            {'label': '심혈관',   'score': 24, 'max': 35},
            {'label': '활동',     'score': 26, 'max': 35},
            {'label': '신체지표', 'score': 14, 'max': 20},
            {'label': '임상',     'score': 8,  'max': 10},
        ],
        'indicators': [
            {'label': '혈당',   'status': 'CAUTION'},
            {'label': '지질',   'status': 'CAUTION'},
            {'label': '간기능', 'status': 'NORMAL'},
            {'label': '신장',   'status': 'NORMAL'},
        ],
        'spending': [
            {'label': '식품',   'pct': 42},
            {'label': '쇼핑',   'pct': 25},
            {'label': '의료',   'pct': 12},
            {'label': '교통',   'pct': 13},
            {'label': '여가',   'pct': 8},
        ],
    },
    'LS-99AABB33-000003': {
        'dynamic_score': 55.2, 'health_score': 53, 'fin_score': 58, 'behavior_score': 61,
        'breakdown': [
            {'label': '심혈관',   'score': 18, 'max': 35},
            {'label': '활동',     'score': 19, 'max': 35},
            {'label': '신체지표', 'score': 11, 'max': 20},
            {'label': '임상',     'score': 5,  'max': 10},
        ],
        'indicators': [
            {'label': '혈당',   'status': 'DANGER'},
            {'label': '지질',   'status': 'CAUTION'},
            {'label': '간기능', 'status': 'CAUTION'},
            {'label': '신장',   'status': 'NORMAL'},
        ],
        'spending': [
            {'label': '식품',   'pct': 35},
            {'label': '쇼핑',   'pct': 18},
            {'label': '의료',   'pct': 25},
            {'label': '교통',   'pct': 12},
            {'label': '여가',   'pct': 10},
        ],
    },
}

_DEFAULT_UID = 'LS-AABBCC11-000001'

def get_mock_health(ls_user_id):
    return _HEALTH_BY_USER.get(ls_user_id, _HEALTH_BY_USER[_DEFAULT_UID])

# ── 포인트 ─────────────────────────────────────────────────────────
MOCK_POINTS = {'balance': 12500, 'next_grade': None, 'next_grade_points': 0, 'next_grade_percent': 100}

MOCK_POINT_HISTORY = [
    {'date': '2026.05.06', 'desc': '걷기 챌린지 달성',     'points': '+200', 'type': 'earn'},
    {'date': '2026.05.03', 'desc': '건강데이터 제공',       'points': '+50',  'type': 'earn'},
    {'date': '2026.05.01', 'desc': '정밀 건강검진 할인',    'points': '-800', 'type': 'use'},
    {'date': '2026.04.28', 'desc': '월간 목표 달성',        'points': '+300', 'type': 'earn'},
    {'date': '2026.04.25', 'desc': '보험료 자동이체',       'points': '+100', 'type': 'earn'},
    {'date': '2026.04.20', 'desc': '건강점수 10점 향상',    'points': '+500', 'type': 'earn'},
    {'date': '2026.04.15', 'desc': 'ETF 자동적립 신청',     'points': '+150', 'type': 'earn'},
    {'date': '2026.04.10', 'desc': '건강데이터 제공',       'points': '+50',  'type': 'earn'},
]

# ── 등급 업그레이드 액션 가이드 ────────────────────────────────────
UPGRADE_ACTIONS = [
    {'icon': '👟', 'title': '걷기 챌린지 참여',    'desc': '매일 8,000보 × 30일',     'points': '+5,000P', 'badge': '충성도 +10'},
    {'icon': '🏥', 'title': '건강검진 수검',        'desc': '당해 연도 건강검진 완료', 'points': '+500P',   'badge': '건강점수 +7'},
    {'icon': '📡', 'title': '웨어러블 연동',        'desc': '기기 데이터 연결하기',    'points': '+200P',   'badge': '건강점수 +5'},
    {'icon': '💳', 'title': '보험 납입 6개월 유지', 'desc': '연속 정상납입 유지',      'points': '+300P',   'badge': '충성도 +10'},
    {'icon': '🔗', 'title': '계열사 3개 이상 연동', 'desc': '데이터 동의 확대',        'points': '+150P',   'badge': '충성도 +18'},
]

# ── 상품 JSON 로딩 ────────────────────────────────────────────────
def _desc(cat, raw):
    if cat in ('deposit_product', 'savings_product'):
        r, m = raw.get('기준금리(연)', ''), raw.get('최고금리(연)', '')
        return f"{r} / 최고 {m}" if r else raw.get('상품유형', '')
    if cat == 'loan_product':
        r, l = raw.get('최저금리(연)', ''), raw.get('대출한도', '')
        return f"최저 {r} / 한도 {l}" if r else raw.get('상품유형', '')
    if cat == 'card_product':
        fee, pct = raw.get('연회비(원)', ''), raw.get('기본적립률(%)', '')
        return f"연회비 {fee}원 / 기본적립 {pct}%" if fee else ''
    if cat in ('insurance_product', 'internet_insurance_product'):
        pm, tg = raw.get('월 보험료(평균)', ''), raw.get('대상고객', '')
        return f"월 {pm} / {tg}" if pm else raw.get('카버리지', '')
    if cat == 'exercise_recommendation':
        ev, ia = raw.get('운동유형', ''), raw.get('활동강도 (분/칼로리)', '')
        return f"{ev} / {ia}" if ev else ''
    if cat == 'health_checkup':
        cnt, pt = raw.get('항목수', ''), raw.get('가격트랙', '')
        return f"{cnt}개 항목 / {pt}" if cnt else ''
    if cat == 'portfolio_product':
        tend, ret = raw.get('투자성향', ''), raw.get('연수익률 (평균/목표)', '')
        return f"투자성향 {tend} / 목표수익 {ret}" if tend else ''
    return ''

def _detail(cat, raw):
    keys_map = {
        'deposit_product':            ['우대금리조건', 'AI 추천 조건', '가입기간', '비고'],
        'savings_product':            ['우대금리조건', 'AI 추천 조건', '납입기간', '비고'],
        'loan_product':               ['우대금리 조건', 'AI 추천 조건', '상환방식', '비고'],
        'card_product':               ['다시 보기', '포인트 적립 조건', '추가 혜택', '연회비(원)'],
        'insurance_product':          ['카버리지', '대상고객', '주요 보장 내용', '가입기간'],
        'internet_insurance_product': ['카버리지', '대상고객', '주요 보장 내용', '가입기간'],
        'exercise_recommendation':    ['활동강도 (분/칼로리)', '추천 시 조건', '추천 이유 (우선순위)', '최대 횟수'],
        'health_checkup':             ['패키지트리거', '권장타겟그룹', '항목수', '가격트랙'],
        'portfolio_product':          ['주요 국내 주식 ETF', '해외주식 ETF', '채권/대안자산', '연수익률 (평균/목표)'],
    }
    items = []
    for k in keys_map.get(cat, []):
        v = str(raw.get(k, '')).strip()
        if v and v != 'nan':
            items.append(v)
    return items[:4] or ['상세 정보를 앱에서 확인하세요']

def _type_label(cat, raw):
    m = {
        'deposit_product':            lambda r: r.get('상품유형', '예금'),
        'savings_product':            lambda r: r.get('상품유형', '적금'),
        'loan_product':               lambda r: r.get('대출유형', r.get('상품유형', '대출')),
        'card_product':               lambda r: '신용카드',
        'insurance_product':          lambda r: r.get('카버리지', '보험'),
        'internet_insurance_product': lambda r: r.get('카버리지', '온라인보험'),
        'exercise_recommendation':    lambda r: r.get('운동유형', '헬스케어'),
        'health_checkup':             lambda r: '건강검진',
        'portfolio_product':          lambda r: r.get('투자성향', '포트폴리오'),
    }
    return m.get(cat, lambda r: '상품')(raw)

def _load_json_products(company_key, filename, max_products=4):
    path = _PRODUCTS_DIR / f'{filename}.json'
    if not path.exists():
        return []
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        result = []
        for i, p in enumerate(data.get('products', [])):
            if len(result) >= max_products:
                break
            name = p.get('product_name', '').strip()
            if not name:
                continue
            raw = p.get('raw', {})
            cat = p.get('category', '')
            d = _desc(cat, raw)
            result.append({
                'id':     p.get('product_code', str(i)),
                'type':   _type_label(cat, raw),
                'name':   name,
                'desc':   d or '상세 정보 확인',
                'tag':    '맞춤추천' if i == 0 else '',
                'detail': _detail(cat, raw),
            })
        return result
    except Exception:
        return []

# ── 폴백 상품 (JSON 로딩 실패 시) ────────────────────────────────
_FALLBACK = {
    'bank': [
        {'id': 'bank_f01', 'type': '예금', 'name': 'LifeSync 정기예금 12개월', 'desc': '기준금리 3.50% / 최고 3.90%', 'tag': '맞춤추천',
         'detail': ['LifeSync 앱 가입 +0.1% / 건강점수≥70 +0.2%', '최소 가입금액 100만원', '만기일시지급', '세금우대 가능']},
        {'id': 'bank_f02', 'type': '예금', 'name': '건강점수 연동 우대예금', 'desc': '건강점수 구간별 자동우대 최고 3.90%', 'tag': '',
         'detail': ['건강점수 ≥90 +0.5% / ≥75 +0.3% / ≥60 +0.1%', '최소 가입금액 50만원', 'AI 핵심 연동 예금', '12개월']},
        {'id': 'bank_f03', 'type': '적금', 'name': '건강목표 달성 적금', 'desc': '기준금리 3.50% / 최고 4.30%', 'tag': '',
         'detail': ['걸음수 8,000보 30일 연속 +0.5%', '건강점수 10점 향상 +0.3%', '6개월 납입', 'AI 핵심: 건강+금융 교차']},
        {'id': 'bank_f04', 'type': '대출', 'name': 'LifeSync 직장인 신용대출', 'desc': '최저 4.50% / 한도 최대 1억원', 'tag': '',
         'detail': ['재직 1년 이상 직장인 대상', '건강점수≥70 -0.2%', '원리금균등 상환', '당일 심사 및 지급']},
    ],
    'card': [
        {'id': 'card_f01', 'type': '신용카드', 'name': 'The Black', 'desc': 'VIP 전용 프리미엄', 'tag': '맞춤추천',
         'detail': ['공항 라운지 무제한', '해외결제 수수료 면제', '전 가맹점 2% 적립', '연회비 15만원']},
        {'id': 'card_f02', 'type': '신용카드', 'name': 'The Blue', 'desc': '일상 특화 적립 카드', 'tag': '',
         'detail': ['식품·편의점 5% 적립', '대중교통 10% 할인', '전 가맹점 1.5% 적립', '연회비 3만원']},
        {'id': 'card_f03', 'type': '체크카드', 'name': '헬스케어 체크카드', 'desc': '병원·약국 5% 캐시백', 'tag': '',
         'detail': ['병원·약국 5% 캐시백', '편의점 3% 캐시백', '월 최대 3만원', '연회비 없음']},
    ],
    'insurance': [
        {'id': 'ins_f01', 'type': '건강보험', 'name': '건강지킴이 보험', 'desc': '심혈관 특약 / 건강점수 연동 할인', 'tag': '맞춤추천',
         'detail': ['심혈관 질환 특약 포함', '건강점수 연동 할인 최대 15%', '월 보험료 3.2만원부터', '비급여 실손 90% 보장']},
        {'id': 'ins_f02', 'type': '실손보험', 'name': '실손 플러스', 'desc': '월 15,000원부터 / 4세대 실손', 'tag': '',
         'detail': ['4세대 실손보험', '입원·통원 통합 보장', '자기부담금 20%', '갱신주기 5년']},
        {'id': 'ins_f03', 'type': '생명보험', 'name': '라이프 종신보험', 'desc': '사망+중증질환 / 건강점수 우대', 'tag': '',
         'detail': ['사망 및 중증질환 보장', '건강점수 연동 우대', '비과세 저축기능 포함', '중도해지환급금 있음']},
    ],
    'internet_insurance': [
        {'id': 'inet_f01', 'type': '여행보험', 'name': '다이렉트 여행자보험', 'desc': '하루 1,000원부터', 'tag': '맞춤추천',
         'detail': ['국내외 여행 중 상해·질병 보장', '출발 당일 가입 가능', '1일~90일 단기 선택', '비대면 청구 지원']},
        {'id': 'inet_f02', 'type': '펫보험', 'name': '반려동물 다이렉트', 'desc': '월 2만원대, 통원 포함', 'tag': '',
         'detail': ['통원·입원·수술 통합 보장', '연간 보장 한도 300만원', '강아지·고양이 공통', '가입 나이 생후 3개월~8세']},
        {'id': 'inet_f03', 'type': '운전자보험', 'name': '운전자보험 다이렉트', 'desc': '연 3만원대, 형사합의금 포함', 'tag': '',
         'detail': ['형사합의금 최대 3,000만원', '벌금 및 방어비용 지원', '자동차보험과 중복 가능', '비대면 가입 즉시 보장']},
    ],
    'securities': [
        {'id': 'sec_f01', 'type': 'ISA', 'name': 'ISA 통합계좌', 'desc': '비과세 한도 연 200만원', 'tag': '맞춤추천',
         'detail': ['연간 200만원 비과세', '국내주식·ETF·펀드 통합', '의무가입기간 3년', '서민형 400만원 비과세']},
        {'id': 'sec_f02', 'type': '해외주식', 'name': '해외주식 직구', 'desc': '수수료 0.07%, 환전 우대 90%', 'tag': '',
         'detail': ['미국·일본·중국·홍콩', '수수료 0.07%', '환전 우대율 90%', '실시간 AI 리포트 제공']},
        {'id': 'sec_f03', 'type': 'ETF적립', 'name': 'ETF 자동적립', 'desc': '월 1만원부터 자동 분산투자', 'tag': '',
         'detail': ['월 1만원부터', '국내·해외 ETF 100종', '매월 지정일 자동 매수', '수수료 무료']},
    ],
    'healthcare': [
        {'id': 'hc_f01', 'type': '검진', 'name': 'VIP 종합 건강검진', 'desc': '제휴병원 30% 할인 / 150개 항목', 'tag': '맞춤추천',
         'detail': ['전국 제휴병원 30% 할인', '150개 항목 종합검진', '검진 결과 AI 분석 제공', '예약 후 2주 내 진행']},
        {'id': 'hc_f02', 'type': '챌린지', 'name': '걷기 챌린지', 'desc': '30일 달성 시 5,000P', 'tag': '진행중',
         'detail': ['매일 8,000보 달성 시 인정', '30일 완주 시 5,000P 지급', '웨어러블 자동 연동', '중도 이탈 후 재참여 가능']},
        {'id': 'hc_f03', 'type': '건강관리', 'name': '체중관리 AI 코칭', 'desc': 'BMI 기반 맞춤 운동 추천', 'tag': '',
         'detail': ['AI 맞춤 운동 처방', '주 3회 이상 달성 시 포인트', '영양사 1:1 상담 월 1회', '건강점수 연동']},
    ],
    'hospital': [
        {'id': 'hosp_f01', 'type': '건강검진', 'name': '정밀 건강검진 패키지', 'desc': 'AI 판독 포함, 건강점수 연동', 'tag': '맞춤추천',
         'detail': ['200개 항목 정밀검진', 'AI 영상 판독 포함', '검진 결과 → 건강점수 자동 반영', '당일 결과 확인 가능']},
        {'id': 'hosp_f02', 'type': '비급여할인', 'name': '비급여 진료 할인', 'desc': '도수치료·영양주사 20% 할인', 'tag': '',
         'detail': ['도수치료·체외충격파 20% 할인', '영양주사·미용의료 할인', '월 최대 10만원 할인 한도', 'LS 회원 전용 우선 예약']},
        {'id': 'hosp_f03', 'type': '만성질환', 'name': '만성질환 관리 프로그램', 'desc': '고혈압·당뇨 월 정기 케어', 'tag': '',
         'detail': ['매월 전담 간호사 1:1 상담', '혈압·혈당 원격 모니터링', '처방전 비대면 발급', '건강점수 연동 할인 최대 20%']},
    ],
}

def _build_recommendations():
    config = [
        ('bank',       '은행',      'bank',               5),
        ('card',       '카드',      'card',               4),
        ('insurance',  '보험',      'insurance',          4),
        ('internet_insurance',   '온라인보험', 'internet_insurance', 3),
        ('securities', '증권',      'securities',         3),
        ('healthcare', '헬스케어',  'healthcare',         3),
        ('hospital',   'LS 병원',   'hospital',           3),
    ]
    recs = []
    for key, name, filename, max_p in config:
        products = _load_json_products(key, filename, max_p)
        if not products:
            products = _FALLBACK.get(key, [])
        recs.append({'key': key, 'name': name, 'products': products})
    return recs

MOCK_RECOMMENDATIONS = _build_recommendations()

PRODUCTS_MAP = {
    p['id']: {**p, 'category': rec['name']}
    for rec in MOCK_RECOMMENDATIONS
    for p in rec['products']
}

# ── 업그레이드 액션 개인화 (유저 컨텍스트) ───────────────────────────
# 운영 시: DynamoDB(스코어/활동) + Aurora(동의 수) + BQ(검진일/걸음수) 실데이터로 교체
_MOCK_USER_CONTEXT = {
    'LS-AABBCC11-000001': {   # 김철수 PLATINUM — 대부분 완료, 걷기만 미달
        'health_score':      88,
        'wearable_linked':   True,
        'checkup_this_year': True,
        'insurance_months':  8,
        'consent_count':     5,
        'avg_steps':         7800,
    },
    'LS-DDEEFF22-000002': {   # 이수진 GOLD — 웨어러블/검진/보험납입/연동 미완료
        'health_score':      72,
        'wearable_linked':   False,
        'checkup_this_year': False,
        'insurance_months':  4,
        'consent_count':     2,
        'avg_steps':         5500,
    },
    'LS-99AABB33-000003': {   # 박지훈 SILVER — 전반적으로 미완료
        'health_score':      53,
        'wearable_linked':   False,
        'checkup_this_year': False,
        'insurance_months':  2,
        'consent_count':     1,
        'avg_steps':         4200,
    },
}
_DEFAULT_CTX = _MOCK_USER_CONTEXT['LS-AABBCC11-000001']

def get_mock_upgrade_actions(ls_user_id: str) -> list:
    ctx = _MOCK_USER_CONTEXT.get(ls_user_id, _DEFAULT_CTX)
    return get_personalized_actions(ctx)

# ── 계열사 동의 현황 (my-products 접근 제어용) ────────────────────────
# 상품 표시 동의 (broad) — AI 스코어링 동의(consent_count)와는 별개
MOCK_CONSENTED_KEYS = {
    'LS-AABBCC11-000001': {'bank', 'card', 'insurance', 'internet_insurance', 'securities', 'healthcare', 'hospital'},
    'LS-DDEEFF22-000002': {'bank', 'card', 'insurance', 'healthcare'},
    'LS-99AABB33-000003': {'bank', 'card', 'healthcare'},
}

# ── 계열사별 보유 상품 (더미) ─────────────────────────────────────────
MOCK_MY_PRODUCTS = {
    'LS-AABBCC11-000001': {   # 김철수 PLATINUM
        'bank': [
            {'type': '정기예금', 'name': 'LifeSync 정기예금 12개월',  'meta': '잔액 5,000,000원 · 만기 2026.11.01', 'status': '유지중', 'sc': 'ok'},
            {'type': '적금',    'name': '건강목표 달성 적금',         'meta': '월 납입 300,000원 · 잔여 4개월',      'status': '납입중', 'sc': 'ok'},
            {'type': '대출',    'name': 'LifeSync 직장인 신용대출',   'meta': '잔액 30,000,000원 · 금리 4.50%',      'status': '상환중', 'sc': 'warn'},
        ],
        'card': [
            {'type': '신용카드', 'name': 'The Black', 'meta': '이번달 1,245,000원 사용', 'status': '정상', 'sc': 'ok'},
        ],
        'insurance': [
            {'type': '건강보험', 'name': '건강지킴이 보험', 'meta': '월 보험료 32,000원',  'status': '유지중', 'sc': 'ok'},
            {'type': '실손보험', 'name': '실손 플러스',     'meta': '월 보험료 15,000원',  'status': '유지중', 'sc': 'ok'},
        ],
        'internet_insurance': [
            {'type': '운전자보험', 'name': '운전자보험 다이렉트', 'meta': '연 28,000원', 'status': '유지중', 'sc': 'ok'},
        ],
        'securities': [
            {'type': 'ISA',    'name': 'ISA 통합계좌',  'meta': '평가금액 12,500,000원 · 수익률 +8.3%', 'status': '운용중', 'sc': 'ok'},
            {'type': 'ETF적립', 'name': 'ETF 자동적립', 'meta': '월 200,000원 · 8개월째',              'status': '적립중', 'sc': 'ok'},
        ],
        'healthcare': [
            {'type': '챌린지', 'name': '걷기 챌린지', 'meta': '22일 달성 / 30일 목표', 'status': '진행중', 'sc': 'info'},
        ],
        'hospital': [
            {'type': '건강검진', 'name': '정밀 건강검진 패키지', 'meta': '2026.03.15 수검 완료', 'status': '완료', 'sc': 'ok'},
        ],
    },
    'LS-DDEEFF22-000002': {   # 이수진 GOLD
        'bank': [
            {'type': '정기예금', 'name': 'LifeSync 정기예금 12개월', 'meta': '잔액 2,000,000원 · 만기 2026.09.15', 'status': '유지중', 'sc': 'ok'},
        ],
        'card': [
            {'type': '신용카드', 'name': 'The Blue', 'meta': '이번달 432,000원 사용', 'status': '정상', 'sc': 'ok'},
        ],
        'insurance': [
            {'type': '건강보험', 'name': '건강지킴이 보험', 'meta': '월 보험료 32,000원 · 4개월째', 'status': '유지중', 'sc': 'ok'},
        ],
        'internet_insurance': [],
        'securities': [],
        'healthcare': [
            {'type': '건강관리', 'name': '체중관리 AI 코칭', 'meta': '3주차 진행중', 'status': '진행중', 'sc': 'info'},
        ],
        'hospital': [],
    },
    'LS-99AABB33-000003': {   # 박지훈 SILVER
        'bank': [
            {'type': '적금', 'name': '건강목표 달성 적금', 'meta': '월 납입 100,000원 · 잔여 9개월', 'status': '납입중', 'sc': 'ok'},
        ],
        'card': [
            {'type': '체크카드', 'name': '헬스케어 체크카드', 'meta': '이번달 128,000원 사용', 'status': '정상', 'sc': 'ok'},
        ],
        'insurance': [],
        'internet_insurance': [],
        'securities': [],
        'healthcare': [
            {'type': '검진', 'name': 'VIP 종합 건강검진', 'meta': '예약 대기중', 'status': '대기중', 'sc': 'warn'},
        ],
        'hospital': [],
    },
}

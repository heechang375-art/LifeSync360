"""
lifesync360_bq_features.py — STEP 2
Glue + EMR 처리 시뮬레이션 → BigQuery / Vertex AI 피처 생성

PPTX 스코어 로직 기준:
  LifeSync Score = 건강 35% + 금융 35% + 소비 15% + 충성도 15%
  entity_id = global_id (1M 전체 동일 기준)

입력: data/output/customer_profile.csv (1M)
      data/output/aurora_users.csv      (300K)

출력: data/output/bq_curated_unified.csv   (1M행, 36컬럼)
      data/output/vertex_feature_table.csv (1M행, entity_id=global_id)
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED       = 42
TOTAL      = 1_000_000
TODAY      = date(2026, 5, 7)
CURATED_DT = TODAY.isoformat()
VIEW_TS    = '2026-05-07T04:00:00Z'

OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'output'

# ── 소득별 금융 피처 범위 ──────────────────────────────────────
INCOME_BANK = {'HIGH': (3_000_000, 8_000_000), 'MID': (1_000_000, 3_000_000), 'LOW': (300_000, 1_000_000)}
INCOME_CARD = {'HIGH': (1_000_000, 4_000_000), 'MID': (300_000,   1_200_000), 'LOW': (100_000,   400_000)}
INCOME_SEC  = {'HIGH': (5_000_000, 50_000_000),'MID': (500_000,  10_000_000), 'LOW': (100_000, 2_000_000)}

CARD_CATEGORIES = ['FOOD', 'SHOPPING', 'MEDICAL', 'TRANSPORT', 'ENTERTAINMENT']
ASSET_TYPES     = ['STOCK', 'FUND', 'ETF', 'BOND']

# ── 라이프스타일별 활동 피처 범위 ─────────────────────────────
LIFESTYLE_STEPS    = {'활동적': (8_000, 15_000), '균형형': (5_000, 10_000), '정적': (2_000, 5_000), '불규칙': (3_000, 9_000)}
LIFESTYLE_EXERCISE = {'활동적': (4, 7),           '균형형': (2, 4),          '정적': (0, 2),         '불규칙': (0, 5)}
LIFESTYLE_HR       = {'활동적': (60, 80),          '균형형': (65, 85),        '정적': (70, 90),        '불규칙': (65, 90)}

# ── 건강상태별 신체지표 범위 ──────────────────────────────────
HEALTH_BMI = {'양호': (18.5, 24.0), '보통': (22.0, 27.0), '주의': (23.0, 30.0), '나쁨': (25.0, 35.0)}
HEALTH_BP  = {'양호': (110, 125),   '보통': (120, 135),   '주의': (125, 145),   '나쁨': (130, 160)}

# ── 건강점수 (PPTX: 심혈관35% + 활동35% + 신체20% + 임상10%) ─
HEALTH_SCORE_BASE = {'양호': (75, 95), '보통': (55, 75), '주의': (35, 55), '나쁨': (15, 35)}
SCENARIO_ADJ = {
    '정상_안정형':        (5,  10),
    '운동_시작_개선형':   (0,   5),
    '고혈압_진단_개선형': (-5,  0),
    '만성질환_관리형':    (-10,-5),
    '건강_악화_위험형':   (-15,-10),
}
SCENARIO_ICD10 = {
    '고혈압_진단_개선형': 'I10',
    '만성질환_관리형':    'E11',
    '건강_악화_위험형':   'I10|E11',
}

# ── 등급별 포인트 범위 ────────────────────────────────────────
GRADE_POINTS = {
    'VIP':      (50_000, 200_000),
    'PLATINUM': (30_000, 100_000),
    'GOLD':     (10_000,  50_000),
    'SILVER':   ( 3_000,  15_000),
    'BASIC':    (     0,   3_000),
}


def ri(rng, lo, hi):
    return rng.randint(lo, hi)

def rf(rng, lo, hi, dp=1):
    return round(rng.uniform(lo, hi), dp)

def health_grade(score):
    if score >= 80: return 'PLATINUM'
    if score >= 70: return 'GOLD'
    if score >= 60: return 'SILVER'
    if score >= 50: return 'BRONZE'
    return 'BASIC'

def calc_health_score(rng, health_st, scenario, h_indicators):
    lo, hi = HEALTH_SCORE_BASE[health_st]
    score  = rng.randint(lo, hi)
    adj_lo, adj_hi = SCENARIO_ADJ[scenario]
    score += rng.randint(adj_lo, adj_hi)
    for ind in h_indicators:
        if ind == 'DANGER':   score -= 5
        elif ind == 'CAUTION': score -= 2
    return max(0, min(100, score))


def main():
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print('[INFO] aurora_users.csv 로드 중...')
    ls_map = {}
    with open(OUTPUT_DIR / 'aurora_users.csv', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            ls_map[row['global_id']] = (row['ls_user_id'], row['grade'])

    bq_header = [
        'global_id', 'ls_user_id', 'curated_date',
        'bank_avg_monthly_txn', 'bank_txn_count_30d',
        'card_monthly_spend', 'card_top_category',
        'insurance_active_count', 'insurance_total_premium', 'insurance_has_realexpense',
        'inet_insurance_active',
        'sec_total_eval_amount', 'sec_return_rate_avg', 'sec_asset_type_mix',
        'hc_avg_daily_calories', 'hc_exercise_freq_week',
        'hos_last_checkup_date', 'hos_chronic_diseases', 'hos_bmi', 'hos_bp_systolic',
        'hos_blood_glucose_status', 'hos_lipid_status', 'hos_liver_status', 'hos_kidney_status',
        'wear_heart_rate_avg_7d', 'wear_hrv_avg_7d', 'wear_spo2_avg_7d',
        'wear_steps_avg_7d', 'wear_calories_avg_7d',
        'health_score_latest', 'health_grade',
        'loyalty_grade', 'total_points',
        'age', 'gender',
        'view_updated_at',
    ]
    # Vertex AI: entity_id + feature_time + 피처 (global_id/ls_user_id/날짜 제외)
    vtx_header = ['entity_id', 'feature_time'] + bq_header[3:-1]

    bq_path  = OUTPUT_DIR / 'bq_curated_unified.csv'
    vtx_path = OUTPUT_DIR / 'vertex_feature_table.csv'

    print('[INFO] bq_curated_unified.csv + vertex_feature_table.csv 생성 중...')

    with (
        open(bq_path,  'w', newline='', encoding='utf-8-sig') as bf,
        open(vtx_path, 'w', newline='', encoding='utf-8-sig') as vf,
        open(OUTPUT_DIR / 'customer_profile.csv', encoding='utf-8-sig') as pf,
    ):
        bw = csv.writer(bf)
        vw = csv.writer(vf)
        bw.writerow(bq_header)
        vw.writerow(vtx_header)

        for i, row in enumerate(csv.DictReader(pf)):
            gid       = row['global_id']
            health_st = row['건강 상태']
            income    = row['소득 구간']
            lifestyle = row['라이프스타일']
            scenario  = row['시나리오']
            age       = int(row['나이'])
            gender    = row['성별']
            h_inds    = [row['혈당_상태'], row['지질_상태'], row['간기능_상태'], row['신장기능_상태']]

            ls_info = ls_map.get(gid)
            ls_user_id    = ls_info[0] if ls_info else ''
            loyalty_grade = ls_info[1] if ls_info else 'BASIC'

            # ── 은행 ─────────────────────────────────────────
            if row['은행 가입'] == 'Y':
                lo, hi   = INCOME_BANK[income]
                bank_avg = ri(rng, lo, hi)
                bank_cnt = ri(rng, 5, 30)
            else:
                bank_avg = bank_cnt = 0

            # ── 카드 ─────────────────────────────────────────
            if row['카드 가입'] == 'Y':
                lo, hi     = INCOME_CARD[income]
                card_spend = ri(rng, lo, hi)
                card_cat   = rng.choice(CARD_CATEGORIES)
            else:
                card_spend = 0
                card_cat   = 'UNKNOWN'

            # ── 보험 ─────────────────────────────────────────
            if row['보험 가입'] == 'Y':
                ins_cnt     = ri(rng, 1, 5)
                ins_premium = ri(rng, 50_000, 100_000) * ins_cnt
                ins_realexp = rng.random() < 0.60
            else:
                ins_cnt = ins_premium = 0
                ins_realexp = False

            # ── 인터넷보험 ───────────────────────────────────
            inet_active = row['인터넷보험 가입'] == 'Y'

            # ── 증권 ─────────────────────────────────────────
            if row['증권 가입'] == 'Y':
                lo, hi    = INCOME_SEC[income]
                sec_eval  = ri(rng, lo, hi)
                sec_ret   = rf(rng, -10.0, 20.0, 2)
                n_types   = rng.randint(1, 4)
                sec_types = '|'.join(rng.sample(ASSET_TYPES, n_types))
            else:
                sec_eval = 0
                sec_ret  = ''
                sec_types = ''

            # ── 헬스케어 ─────────────────────────────────────
            if row['헬스케어 가입'] == 'Y':
                hc_cal  = ri(rng, 1_500, 2_500)
                lo, hi  = LIFESTYLE_EXERCISE[lifestyle]
                hc_freq = ri(rng, lo, hi)
            else:
                hc_cal = hc_freq = 0

            # ── 병원 ─────────────────────────────────────────
            if row['병원 가입'] == 'Y':
                days_ago   = ri(rng, 30, 730)
                checkup_dt = (TODAY - timedelta(days=days_ago)).isoformat()
                chronic    = SCENARIO_ICD10.get(scenario, '')
                lo, hi     = HEALTH_BMI[health_st]
                hos_bmi    = rf(rng, lo, hi, 1)
                lo, hi     = HEALTH_BP[health_st]
                hos_bp     = ri(rng, lo, hi)
            else:
                checkup_dt = chronic = ''
                hos_bmi    = ''
                hos_bp     = ''

            # ── 웨어러블 ─────────────────────────────────────
            if row['웨어러블 가입'] == 'Y':
                lo, hi     = LIFESTYLE_HR[lifestyle]
                wear_hr    = rf(rng, lo, hi, 1)
                wear_hrv   = rf(rng, 20.0, 80.0, 1)
                wear_spo2  = rf(rng, 95.0, 100.0, 1)
                lo, hi     = LIFESTYLE_STEPS[lifestyle]
                wear_steps = ri(rng, lo, hi)
                wear_cal   = rf(rng, 200.0, 700.0, 1)
            else:
                wear_hr = wear_hrv = wear_spo2 = ''
                wear_steps = ''
                wear_cal   = ''

            # ── 건강점수 (PPTX 스코어 로직) ──────────────────
            h_score = calc_health_score(rng, health_st, scenario, h_inds)
            h_grade = health_grade(h_score)

            # ── 포인트 ───────────────────────────────────────
            lo, hi    = GRADE_POINTS[loyalty_grade]
            total_pts = ri(rng, lo, hi)

            # ── 피처 벡터 (bq_header[3:-1] 순서와 일치) ─────
            features = [
                bank_avg, bank_cnt,
                card_spend, card_cat,
                ins_cnt, ins_premium, ins_realexp,
                inet_active,
                sec_eval, sec_ret, sec_types,
                hc_cal, hc_freq,
                checkup_dt, chronic, hos_bmi, hos_bp,
                h_inds[0], h_inds[1], h_inds[2], h_inds[3],
                wear_hr, wear_hrv, wear_spo2, wear_steps, wear_cal,
                h_score, h_grade,
                loyalty_grade, total_pts,
                age, gender,
            ]

            bw.writerow([gid, ls_user_id, CURATED_DT] + features + [VIEW_TS])
            vw.writerow([gid, VIEW_TS] + features)

            if (i + 1) % 100_000 == 0:
                print(f'  {i + 1:,} / {TOTAL:,} 처리 완료')

    print(f'\n[완료]')
    print(f'  bq_curated_unified.csv:   {TOTAL:,}행, {len(bq_header)}컬럼')
    print(f'  vertex_feature_table.csv: {TOTAL:,}행, {len(vtx_header)}컬럼')
    print(f'  entity_id = global_id (전체 {TOTAL:,}명 기준)')
    print(f'  LifeSync 가입자 {len(ls_map):,}명: ls_user_id 매핑됨')


if __name__ == '__main__':
    main()

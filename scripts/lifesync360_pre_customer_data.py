"""
lifesync360_pre_customer_data.py  —  STEP 1
100만명 고객 기본 프로파일 + DB 적재용 CSV 생성

이미지 기준 비율 적용:
  연령 : 20대 15% / 30대 25% / 40대 30% / 50대 20% / 60대이상 10%
  계열사: 은행 100% / 카드 70% / 보험 50% / 온라인보험 25%
          병원 20% / 헬스케어 30% / 증권 25% / 웨어러블 30%

산출물 (data/output/):
  customer_profile.csv        전체 프로파일 (100만행, 39컬럼)
  customer_master.csv         onprem master_customer 적재용
  customer_identity_map.csv   onprem customer_identity_map 적재용
  aurora_users.csv            Aurora users 적재용 (LifeSync 가입자 30만)
"""
import csv
import hashlib
import random
from datetime import date
from pathlib import Path

import numpy as np

SEED  = 42
TOTAL = 1_000_000
TODAY = date(2026, 5, 7)

OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'output'

# ── 분포 (이미지 기준) ────────────────────────────────────────────
AGE_BRACKETS = [
    (20, 29, 0.15),
    (30, 39, 0.25),
    (40, 49, 0.30),
    (50, 59, 0.20),
    (60, 79, 0.10),
]

AFFILIATE_RATES = {
    '은행':     ('bank',               'BNK', 1.00),
    '카드':     ('card',               'CRD', 0.70),
    '보험':     ('insurance',          'INS', 0.50),
    '인터넷보험': ('internet_insurance', 'IIN', 0.25),
    '병원':     ('hospital',           'HOS', 0.20),
    '헬스케어':  ('healthcare',         'HCR', 0.30),
    '증권':     ('securities',         'SEC', 0.25),
    '웨어러블':  ('wearable',           'WBL', 0.30),
}

# 기존 프로파일 분포 그대로 유지
CUSTOMER_TYPES  = ['기본고객형', '금융적극형', '헬스관심형']
CUSTOMER_WGTS   = [0.50, 0.30, 0.20]
GENDERS         = ['MALE', 'FEMALE']
INCOME_LEVELS   = ['LOW', 'MID', 'HIGH']
HEALTH_STATUSES = ['양호', '보통', '주의', '나쁨']
HEALTH_WGTS     = [0.415, 0.333, 0.175, 0.077]
LIFESTYLES      = ['균형형', '정적', '불규칙', '활동적']
SCENARIOS       = ['정상_안정형', '고혈압_진단_개선형', '운동_시작_개선형', '만성질환_관리형', '건강_악화_위험형']
SCENARIO_WGTS   = [0.498, 0.174, 0.150, 0.119, 0.059]
HEALTH_STATES   = ['NORMAL', 'CAUTION', 'DANGER']
HEALTH_ST_WGTS  = [0.652, 0.228, 0.120]

# 동의율 (가입 시에만 적용)
CONSENT_RATES = {
    '은행': 0.808, '카드': 0.728, '보험': 0.515, '인터넷보험': 0.321,
    '병원': 0.571, '헬스케어': 0.285, '증권': 0.377, '웨어러블': 0.253,
}

LIFESYNC_RATE = 0.30   # 30만명 가입자
GRADES        = ['BASIC', 'SILVER', 'GOLD', 'PLATINUM', 'VIP']
GRADE_WGTS    = [0.40, 0.25, 0.20, 0.10, 0.05]

SURNAMES  = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
             '한', '오', '서', '신', '권', '황', '안', '송', '류', '홍']
GIVEN_M   = ['민준', '서준', '예준', '도윤', '시우', '주원', '하준', '지호', '준서', '현우',
             '민재', '현준', '도현', '정우', '지훈', '민성', '준혁', '재원', '성민', '태양']
GIVEN_F   = ['서연', '서윤', '지우', '서현', '민서', '하은', '하린', '지유', '윤서', '채원',
             '수아', '지민', '아린', '예린', '은서', '다은', '지아', '수빈', '나은', '유진']

AFF_KEYS = list(AFFILIATE_RATES.keys())  # 출력 순서 고정


def _wchoice(rng, values, weights):
    return rng.choices(values, weights=weights, k=1)[0]


def _birth_dt(rng, age_min, age_max):
    age   = rng.randint(age_min, age_max)
    year  = TODAY.year - age
    month = rng.randint(1, 12)
    day   = rng.randint(1, 28)
    return date(year, month, day).isoformat()


def _ls_user_id(seq, rng):
    hex_part = format(rng.getrandbits(32), '08X')
    return f'LS-{hex_part}-{seq:06d}'


def _seed_hash(email):
    return 'sha256_seed:' + hashlib.sha256(email.encode()).hexdigest()[:32]


def main():
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # LifeSync 가입자 인덱스 사전 결정 (300,000명)
    ls_count  = int(TOTAL * LIFESYNC_RATE)
    indices   = list(range(TOTAL))
    rng.shuffle(indices)
    ls_set    = set(indices[:ls_count])

    # 계열사별 순번 카운터
    aff_counters = {k: 1 for k in AFF_KEYS}
    ls_seq       = 1

    profile_path = OUTPUT_DIR / 'customer_profile.csv'
    master_path  = OUTPUT_DIR / 'customer_master.csv'
    cim_path     = OUTPUT_DIR / 'customer_identity_map.csv'
    aurora_path  = OUTPUT_DIR / 'aurora_users.csv'

    profile_header = (
        ['global_id', '고객 유형', '나이', '성별', '소득 구간', '건강 상태',
         '신용등급(1~10)', '라이프스타일', '시나리오', '가입계열사 수'] +
        [f'{k} 가입' for k in AFF_KEYS] +
        [f'{k} ID'   for k in AFF_KEYS] +
        [f'{k} 동의'  for k in AFF_KEYS] +
        ['혈당_상태', '지질_상태', '간기능_상태', '신장기능_상태']
    )

    print(f'[INFO] 출력 경로: {OUTPUT_DIR}')
    print(f'[INFO] 전체 고객: {TOTAL:,}명 / LifeSync 가입자: {ls_count:,}명\n')

    with (
        open(profile_path, 'w', newline='', encoding='utf-8-sig') as pf,
        open(master_path,  'w', newline='', encoding='utf-8-sig') as mf,
        open(cim_path,     'w', newline='', encoding='utf-8-sig') as cf,
        open(aurora_path,  'w', newline='', encoding='utf-8-sig') as af,
    ):
        pw = csv.writer(pf)
        mw = csv.writer(mf)
        cw = csv.writer(cf)
        aw = csv.writer(af)

        pw.writerow(profile_header)
        mw.writerow(['global_id', 'representative_name', 'birth_dt', 'gender', 'nationality'])
        cw.writerow(['global_id', 'company_id', 'affiliate_customer_id'])
        aw.writerow(['ls_user_id', 'global_id', 'email', 'password_hash', 'name', 'grade'])

        for i in range(TOTAL):
            gid    = f'G{i + 1:09d}'
            gender = rng.choice(GENDERS)
            name   = rng.choice(SURNAMES) + rng.choice(GIVEN_M if gender == 'MALE' else GIVEN_F)

            # 연령 (이미지 비율)
            a_min, a_max, _ = rng.choices(AGE_BRACKETS, weights=[w for *_, w in AGE_BRACKETS])[0]
            age      = rng.randint(a_min, a_max)
            birth_dt = _birth_dt(rng, a_min, a_max)

            ctype     = _wchoice(rng, CUSTOMER_TYPES, CUSTOMER_WGTS)
            income    = rng.choice(INCOME_LEVELS)
            health_st = _wchoice(rng, HEALTH_STATUSES, HEALTH_WGTS)
            credit    = rng.randint(1, 10)
            lifestyle = rng.choice(LIFESTYLES)
            scenario  = _wchoice(rng, SCENARIOS, SCENARIO_WGTS)

            # 계열사 가입 (이미지 비율)
            joined   = {}
            aff_ids  = {}
            consents = {}
            is_ls_member = i in ls_set
            for k, (co_id, prefix, rate) in AFFILIATE_RATES.items():
                j = rng.random() < rate
                joined[k] = 'Y' if j else 'N'
                if j:
                    aff_id     = f'{prefix}-{aff_counters[k]:08d}'
                    aff_ids[k] = aff_id
                    aff_counters[k] += 1
                    # LifeSync 미가입자: 동의 없음 / 가입자: 확률 적용
                    if is_ls_member:
                        consents[k] = 'Y' if rng.random() < CONSENT_RATES[k] else 'N'
                    else:
                        consents[k] = 'N'
                        rng.random()  # 시드 시퀀스 유지
                    cw.writerow([gid, AFFILIATE_RATES[k][0], aff_id])
                else:
                    aff_ids[k]  = ''
                    consents[k] = 'N'

            # LifeSync 가입자는 가입 계열사 중 최소 1개 동의 보장
            if is_ls_member:
                joined_keys = [k for k in AFF_KEYS if joined[k] == 'Y']
                if joined_keys and all(consents[k] == 'N' for k in joined_keys):
                    consents[rng.choice(joined_keys)] = 'Y'

            join_count = sum(1 for v in joined.values() if v == 'Y')

            # 건강지표 (건강 상태와 상관)
            if health_st == '양호':
                hw = [0.80, 0.15, 0.05]
            elif health_st == '보통':
                hw = [0.60, 0.30, 0.10]
            elif health_st == '주의':
                hw = [0.35, 0.45, 0.20]
            else:
                hw = [0.15, 0.35, 0.50]

            h_indicators = [
                _wchoice(rng, HEALTH_STATES, hw) if health_st != '양호' or rng.random() < 0.85 else 'NORMAL'
                for _ in range(4)
            ]
            # 정상_안정형 시나리오는 건강지표 모두 NORMAL or CAUTION
            if scenario == '정상_안정형':
                h_indicators = [
                    'NORMAL' if rng.random() < 0.75 else 'CAUTION'
                    for _ in range(4)
                ]

            # master_customer
            mw.writerow([gid, name, birth_dt, gender[0], 'KR'])

            # profile
            pw.writerow(
                [gid, ctype, age, gender, income, health_st, credit, lifestyle, scenario, join_count] +
                [joined[k]   for k in AFF_KEYS] +
                [aff_ids[k]  for k in AFF_KEYS] +
                [consents[k] for k in AFF_KEYS] +
                h_indicators
            )

            # Aurora users (LifeSync 가입자)
            if i in ls_set:
                ls_id   = _ls_user_id(ls_seq, rng)
                email   = f'user{ls_seq}@lifesync-test.com'
                grade   = _wchoice(rng, GRADES, GRADE_WGTS)
                aw.writerow([ls_id, gid, email, _seed_hash(email), name, grade])
                ls_seq += 1

            if (i + 1) % 100_000 == 0:
                print(f'  {i + 1:,} / {TOTAL:,} 처리 완료')

    total_aff = sum(aff_counters[k] - 1 for k in AFF_KEYS)
    print(f'\n[완료]')
    print(f'  customer_profile.csv:       {TOTAL:,}행')
    print(f'  customer_master.csv:        {TOTAL:,}행')
    print(f'  customer_identity_map.csv:  {total_aff:,}행')
    print(f'  aurora_users.csv:           {ls_count:,}행')
    print(f'\n계열사별 가입자 수:')
    for k in AFF_KEYS:
        cnt = aff_counters[k] - 1
        print(f'  {k:8s}: {cnt:,}명 ({cnt/TOTAL*100:.1f}%)')


if __name__ == '__main__':
    main()

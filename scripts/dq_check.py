"""
dq_check.py — Glue Data Quality 룰 시뮬레이션
customer_profile.csv / customer_master.csv / customer_identity_map.csv / aurora_users.csv 검증
"""
import csv
import re
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'output'

PROFILE_REQUIRED = ['global_id', '고객 유형', '나이', '성별', '소득 구간', '건강 상태']
MASTER_REQUIRED  = ['global_id', 'representative_name', 'birth_dt', 'gender', 'nationality']
CIM_REQUIRED     = ['global_id', 'company_id', 'affiliate_customer_id']
AURORA_REQUIRED  = ['ls_user_id', 'global_id', 'email', 'grade']

AFF_ID_PATTERNS = {
    'bank':               re.compile(r'^BNK-\d{8}$'),
    'card':               re.compile(r'^CRD-\d{8}$'),
    'insurance':          re.compile(r'^INS-\d{8}$'),
    'internet_insurance': re.compile(r'^IIN-\d{8}$'),
    'hospital':           re.compile(r'^HOS-\d{8}$'),
    'healthcare':         re.compile(r'^HCR-\d{8}$'),
    'securities':         re.compile(r'^SEC-\d{8}$'),
    'wearable':           re.compile(r'^WBL-\d{8}$'),
}
GID_RE   = re.compile(r'^G\d{9}$')
LSID_RE  = re.compile(r'^LS-[0-9A-F]{8}-\d{6}$')
EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
VALID_GRADES = {'BASIC', 'SILVER', 'GOLD', 'PLATINUM', 'VIP'}
VALID_GENDERS = {'MALE', 'FEMALE', 'M', 'F'}


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def null_check(rows, required):
    return sum(1 for r in rows for f in required if not r.get(f, '').strip())


def dup_check(rows, key):
    seen, dupes = set(), 0
    for r in rows:
        k = r.get(key, '')
        if k in seen:
            dupes += 1
        seen.add(k)
    return dupes


def main():
    res = {}

    # ── 1) customer_profile.csv ────────────────────────────────
    print('[1/4] customer_profile.csv ...')
    profile = read_csv(OUTPUT_DIR / 'customer_profile.csv')
    res['p_rows']     = len(profile)
    res['p_nulls']    = null_check(profile, PROFILE_REQUIRED)
    res['p_gid_dup']  = dup_check(profile, 'global_id')
    res['p_gid_fmt']  = sum(1 for r in profile if not GID_RE.match(r.get('global_id', '')))
    res['p_age_inv']  = sum(
        1 for r in profile
        if not r.get('나이', '').lstrip('-').isdigit()
        or not (20 <= int(r['나이']) <= 79)
    )
    res['p_gender_inv'] = sum(1 for r in profile if r.get('성별', '') not in VALID_GENDERS)

    # ── 2) customer_master.csv ────────────────────────────────
    print('[2/4] customer_master.csv ...')
    master = read_csv(OUTPUT_DIR / 'customer_master.csv')
    res['m_rows']    = len(master)
    res['m_nulls']   = null_check(master, MASTER_REQUIRED)
    res['m_gid_dup'] = dup_check(master, 'global_id')
    master_gids = {r['global_id'] for r in master}

    # ── 3) customer_identity_map.csv ─────────────────────────
    print('[3/4] customer_identity_map.csv ...')
    cim = read_csv(OUTPUT_DIR / 'customer_identity_map.csv')
    res['c_rows']       = len(cim)
    res['c_nulls']      = null_check(cim, CIM_REQUIRED)
    res['c_orphan']     = sum(1 for r in cim if r.get('global_id', '') not in master_gids)
    res['c_aff_fmt']    = sum(
        1 for r in cim
        if (pat := AFF_ID_PATTERNS.get(r.get('company_id', '')))
        and not pat.match(r.get('affiliate_customer_id', ''))
    )

    # ── 4) aurora_users.csv ───────────────────────────────────
    print('[4/4] aurora_users.csv ...')
    aurora = read_csv(OUTPUT_DIR / 'aurora_users.csv')
    res['a_rows']       = len(aurora)
    res['a_nulls']      = null_check(aurora, AURORA_REQUIRED)
    res['a_lsid_dup']   = dup_check(aurora, 'ls_user_id')
    res['a_gid_dup']    = dup_check(aurora, 'global_id')
    res['a_lsid_fmt']   = sum(1 for r in aurora if not LSID_RE.match(r.get('ls_user_id', '')))
    res['a_email_fmt']  = sum(1 for r in aurora if not EMAIL_RE.match(r.get('email', '')))
    res['a_orphan']     = sum(1 for r in aurora if r.get('global_id', '') not in master_gids)
    res['a_grade_inv']  = sum(1 for r in aurora if r.get('grade', '') not in VALID_GRADES)
    # LS 가입자 비율 (30% 기대)
    res['a_ls_ratio']   = res['a_rows'] / res['p_rows'] if res['p_rows'] else 0

    # ── 리포트 ────────────────────────────────────────────────
    SEP = '=' * 62
    print(f'\n{SEP}')
    print('  LifeSync360 DQ 검사 결과 (Glue DQ 룰 시뮬레이션)')
    print(SEP)

    checks = [
        # label                               actual                  expected  mode
        ('customer_profile 행 수',            res['p_rows'],          1_000_000, 'EQ'),
        ('  필수 필드 NULL',                   res['p_nulls'],         0,         'EQ'),
        ('  global_id 중복',                  res['p_gid_dup'],       0,         'EQ'),
        ('  global_id 포맷 오류 (G{9자리})',  res['p_gid_fmt'],       0,         'EQ'),
        ('  나이 범위 오류 (20~79세)',         res['p_age_inv'],       0,         'EQ'),
        ('  성별 값 오류',                     res['p_gender_inv'],    0,         'EQ'),
        ('customer_master 행 수',             res['m_rows'],          1_000_000, 'EQ'),
        ('  필수 필드 NULL',                   res['m_nulls'],         0,         'EQ'),
        ('  global_id 중복',                  res['m_gid_dup'],       0,         'EQ'),
        ('customer_identity_map 행 수',       res['c_rows'],          None,      'INFO'),
        ('  필수 필드 NULL',                   res['c_nulls'],         0,         'EQ'),
        ('  orphan global_id',                res['c_orphan'],        0,         'EQ'),
        ('  affiliate_id 포맷 오류',          res['c_aff_fmt'],       0,         'EQ'),
        ('aurora_users 행 수',                res['a_rows'],          300_000,   'EQ'),
        ('  필수 필드 NULL',                   res['a_nulls'],         0,         'EQ'),
        ('  ls_user_id 중복',                 res['a_lsid_dup'],      0,         'EQ'),
        ('  global_id 중복',                  res['a_gid_dup'],       0,         'EQ'),
        ('  ls_user_id 포맷 오류',            res['a_lsid_fmt'],      0,         'EQ'),
        ('  이메일 포맷 오류',                res['a_email_fmt'],     0,         'EQ'),
        ('  orphan global_id',                res['a_orphan'],        0,         'EQ'),
        ('  grade 값 오류',                   res['a_grade_inv'],     0,         'EQ'),
        ('  LS 가입 비율 (~30%)',             res['a_ls_ratio'],      0.30,      'APPROX'),
    ]

    pass_cnt = fail_cnt = 0
    for label, val, expected, mode in checks:
        if mode == 'INFO':
            print(f'  [INFO]  {label}: {val:,}')
        elif mode == 'APPROX':
            ok = abs(val - expected) < 0.01
            status = 'PASS' if ok else 'FAIL'
            mark = 'O' if ok else 'X'
            if ok: pass_cnt += 1
            else:  fail_cnt += 1
            print(f'  [{status}] {mark} {label}: {val:.4f}  (기대: ~{expected})')
        else:
            ok = (val == expected)
            status = 'PASS' if ok else 'FAIL'
            mark = 'O' if ok else 'X'
            if ok: pass_cnt += 1
            else:  fail_cnt += 1
            exp_str = f'{expected:,}' if isinstance(expected, int) else str(expected)
            print(f'  [{status}] {mark} {label}: {val:,}  (기대: {exp_str})')

    print(SEP)
    print(f'  결과: PASS {pass_cnt} / FAIL {fail_cnt}')
    if fail_cnt == 0:
        print('  → 모든 DQ 검사 통과. BQ 적재 진행 가능.')
    else:
        print('  → FAIL 항목 확인 후 재검사 필요.')
    print(SEP)


if __name__ == '__main__':
    main()

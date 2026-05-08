"""
상품 카탈로그 Aurora 적재 스크립트
데이터 소스: ../data/products/*.json (계열사별 분리 파일, 총 148개 상품)
  bank.json              35개 (예적금, 대출)
  card.json              20개 (신용/체크카드)
  insurance.json         30개 (오프라인 보험)
  internet_insurance.json 29개 (온라인 보험)
  securities.json        19개 (투자 포트폴리오)
  healthcare.json        15개 (운동/식단 추천)

실행 방법:
  1. .env 파일 작성 (AURORA_HOST, DB_USER, DB_PASS)
  2. pip install pymysql python-dotenv
  3. python seed_products.py

특정 계열사만 적재:
  python seed_products.py bank
  python seed_products.py card insurance
"""
import json, os, sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv

load_dotenv()

PRODUCTS_DIR = Path(__file__).parent.parent / 'data' / 'products'

REQUIRED_ENVS = ['AURORA_HOST', 'DB_USER', 'DB_PASS']
for key in REQUIRED_ENVS:
    if not os.environ.get(key):
        print(f"[ERROR] 환경변수 {key} 없음. .env 파일을 확인하세요.")
        sys.exit(1)

if not PRODUCTS_DIR.exists():
    print(f"[ERROR] 디렉토리 없음: {PRODUCTS_DIR}")
    sys.exit(1)

ALL_COMPANIES = ['bank', 'card', 'insurance', 'internet_insurance', 'securities', 'healthcare', 'hospital']

# 인자로 특정 계열사만 지정 가능 (예: python seed_products.py bank card)
target_companies = sys.argv[1:] if len(sys.argv) > 1 else ALL_COMPANIES
unknown = [c for c in target_companies if c not in ALL_COMPANIES]
if unknown:
    print(f"[ERROR] 알 수 없는 계열사: {unknown}")
    print(f"        사용 가능: {ALL_COMPANIES}")
    sys.exit(1)


def extract_product_type(record: dict) -> str:
    if record.get('product_type'):
        return record['product_type']
    raw = record.get('raw', {})
    for key in ('세부유형', '상품유형', '대출유형', '구분', '투자성향'):
        if raw.get(key):
            return str(raw[key]).strip()
    return ''


def extract_description(record: dict) -> str:
    if record.get('description'):
        return record['description']
    raw = record.get('raw', {})
    for key in ('주요 보장 내용', '핵심 혜택', '기대수익률(연)', '대상 고객 조건'):
        if raw.get(key):
            return str(raw[key]).strip()
    return ''


def extract_rec_condition(record: dict) -> str:
    if record.get('recommendation_condition'):
        return record['recommendation_condition']
    raw = record.get('raw', {})
    for key in ('AI 추천 대상', '건강점수 기반 추천 조건', 'AI 추천 타겟', 'AI 추천 트리거', '대상 고객 조건'):
        if raw.get(key):
            return str(raw[key]).strip()
    return ''


def extract_options(record: dict) -> list:
    if record.get('options'):
        return record['options']

    raw = record.get('raw', {})
    sheet = record.get('source_sheet', '')
    opts = []

    if '보험' in sheet:
        for key in ('주요 보장 내용', '특약 여부', '월 납부액(기준)', '보험기간'):
            if raw.get(key):
                opts.append({'key': key, 'value': str(raw[key])})
    elif '카드' in sheet:
        for key in ('핵심 혜택', '포인트 적립 공식', '연회비(원)', '건강점수 연동 조건'):
            if raw.get(key):
                opts.append({'key': key, 'value': str(raw[key])})
    elif '예적금' in sheet:
        for key in ('기준금리(연)', '우대금리 조건', '가입기간', '최소가입금액'):
            if raw.get(key):
                opts.append({'key': key, 'value': str(raw[key])})
    elif '대출' in sheet:
        for key in ('금리범위', '최대한도', '대출기간', '상환방식'):
            if raw.get(key):
                opts.append({'key': key, 'value': str(raw[key])})
    elif '금융상품' in sheet:
        for key in ('채권/안전자산', '기대수익률(연)', '변동성', '최소 투자금액'):
            if raw.get(key):
                opts.append({'key': key, 'value': str(raw[key])})

    return opts


def main():
    conn = pymysql.connect(
        host     = os.environ['AURORA_HOST'],
        user     = os.environ['DB_USER'],
        password = os.environ['DB_PASS'],
        db       = 'lifesync',
        charset  = 'utf8mb4'
    )

    companies = [
        ('bank',               'LS 은행',       'bank'),
        ('card',               'LS 카드',       'card'),
        ('insurance',          'LS 보험',       'insurance'),
        ('internet_insurance', 'LS 온라인보험', 'internet_insurance'),
        ('securities',         'LS 증권',       'securities'),
        ('healthcare',         'LS 헬스케어',   'healthcare'),
        ('hospital',           'LS 병원',       'hospital'),
    ]

    total_products = 0
    total_options  = 0
    total_rules    = 0

    with conn.cursor() as cur:
        # 1. company_master (전체 등록 — 항상 실행)
        for cid, cname, ctype in companies:
            cur.execute("""
                INSERT INTO company_master (company_id, company_name, company_type)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE company_name = VALUES(company_name)
            """, (cid, cname, ctype))
        print(f"[OK] company_master {len(companies)}개")

        # 2. 계열사별 JSON 파일 순서대로 적재
        for company_id in target_companies:
            json_path = PRODUCTS_DIR / f'{company_id}.json'
            if not json_path.exists():
                print(f"[SKIP] 파일 없음: {json_path}")
                continue

            with open(json_path, encoding='utf-8') as f:
                data = json.load(f)

            records = data['products']
            inserted_p = inserted_o = inserted_r = 0

            for rec in records:
                pid   = rec['product_code']
                cid   = rec['company_id']
                cat   = rec.get('category', '')
                ptype = extract_product_type(rec)
                desc  = extract_description(rec)
                rcond = extract_rec_condition(rec)
                name  = rec['product_name']

                cur.execute("""
                    INSERT INTO product_master
                      (product_id, company_id, category_id, product_type,
                       product_name, product_desc, min_grade)
                    VALUES (%s, %s, %s, %s, %s, %s, 'BASIC')
                    ON DUPLICATE KEY UPDATE
                      product_name = VALUES(product_name),
                      product_type = VALUES(product_type),
                      product_desc = VALUES(product_desc)
                """, (pid, cid, cat, ptype, name, desc))
                inserted_p += 1

                opts = extract_options(rec)
                if opts:
                    cur.execute("DELETE FROM product_option WHERE product_id = %s", (pid,))
                    for i, opt in enumerate(opts):
                        cur.execute("""
                            INSERT INTO product_option (product_id, option_key, option_value, sort_order)
                            VALUES (%s, %s, %s, %s)
                        """, (pid, opt.get('key', 'benefit'), opt.get('value', ''), i))
                        inserted_o += 1

                if rcond:
                    cur.execute("""
                        INSERT INTO recommend_rule (product_id, condition_key, condition_val, priority)
                        VALUES (%s, 'ai_condition', %s, 0)
                        ON DUPLICATE KEY UPDATE condition_val = VALUES(condition_val)
                    """, (pid, rcond))
                    inserted_r += 1

            print(f"[OK] {company_id:<22} 상품 {inserted_p}개 / 옵션 {inserted_o}개 / 룰 {inserted_r}개")
            total_products += inserted_p
            total_options  += inserted_o
            total_rules    += inserted_r

    conn.commit()
    conn.close()

    print()
    print(f"[TOTAL] 상품 {total_products}개 / 옵션 {total_options}개 / 룰 {total_rules}개")
    print()
    print("[INFO] recommend_rule은 GCP AI 결과 없을 때 Fallback 용도")
    print("       주 추천 경로: GCP Vertex AI → next_best_action → DynamoDB → Aurora 상품 조회")


if __name__ == '__main__':
    main()

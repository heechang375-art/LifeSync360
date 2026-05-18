# CHANGELOG

## 2026-05-17 — 신규 테이블 2개 추가 (STEP 10, 11)

### 추가된 테이블

| # | 테이블 | 용도 |
|---|---|---|
| 10 | `customer_product_application` | 상품 신청 이력 (이벤트 로그, 9 컬럼) |
| 11 | `customer_recommend_daily` | 일별 추천 성과 mart (analytics 일배치 적재 대상) |

### 변경 파일

| 파일 | 변경 |
|---|---|
| `Aurora_MySQL_DB_Create.sql` | STEP 10, 11 테이블 DDL + 인덱스 추가 |
| `service-db-execution.sh` | STEP 10, 11 실행 추가 |
| `9.customer_product_application.sql` | NEW — DDL + FK + 멱등 인덱스 |
| `10.customer_recommend_daily.sql` | NEW — DDL + 멱등 인덱스 |

### customer_product_application 설계 결정 (v3)

기존 테이블과의 정합성 검토 + 책임 범위 정리 결과:

- **컬럼 슬림화** — 신청 "사실" 만 기록하는 이벤트 로그로 단순화
  - 제거: `applicant_name`, `applicant_phone`, `applicant_email`,
    `apply_amount`, `contact_time`, `memo`, `agree_marketing` (7개)
  - 사유: 컨택 정보는 별도 시스템 책임. `apply_amount` 는 자유텍스트라
    `product_option` 의 정형 금액과 충돌

- **`status` 컬럼** — VARCHAR(20) → **ENUM**
  - `RECEIVED` / `IN_REVIEW` / `APPROVED` / `REJECTED` / `CANCELED`
  - ENUM 이외 값은 INSERT 단계에서 차단 (ERROR 1265)

- **`global_id` 타입 통일** — VARCHAR(20) → **VARCHAR(50)**
  - `customer_recommend_history`, `customer_dashboard_log` 와 동일
  - JOIN 시 암묵적 형변환 방지

- **`product_code` 컬럼 제거** — 정규화
  - `product_master.product_code` 와 중복 → product_id FK 하나로 충분
  - 상품 코드/이름은 `product_master` JOIN 으로 조회

**최종 컬럼:** 9개 (`application_id`, `global_id`, `ls_user_id`, `product_id`,
`status`, `reviewer_id`, `reviewed_at`, `created_at`, `updated_at`)

### 멱등성

- `CREATE TABLE IF NOT EXISTS`
- `CREATE INDEX` 는 `INFORMATION_SCHEMA.STATISTICS` 체크 후 동적 SQL 분기
- 같은 환경에서 여러 번 돌려도 안전

### 실행

기존과 동일:

```bash
cd Service-DB
bash service-db-execution.sh
```

`service-db-destory.sh` 는 `DROP DATABASE lifesync360` 한 줄이므로 수정 불필요.

### 상세 가이드

신규 테이블 컬럼 정보, 샘플 쿼리, 데이터 흐름은 `NEW_TABLES_GUIDE.md` 참조.

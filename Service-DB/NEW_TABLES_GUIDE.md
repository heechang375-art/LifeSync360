# 2026-05-17 신규 테이블 가이드

LifeSync360 Aurora MySQL `lifesync360` DB 에 추가되는 2개 테이블의 상세 명세.

> **🔧 v3 갱신** — 컬럼 슬림화 및 정합성 점검 반영
> - **컨택 정보 컬럼 7개 제거** (`applicant_name/phone/email`, `apply_amount`, `contact_time`, `memo`, `agree_marketing`)
>   → "신청했다" 는 사실만 기록. 컨택 정보는 별도 시스템 영역.
> - `status` 컬럼 VARCHAR(20) → **ENUM** 으로 변경 (값 검증)
> - `global_id` 타입 VARCHAR(20) → **VARCHAR(50)** (`customer_recommend_history` 등과 통일)
> - `product_code` 컬럼 제거 (`product_master` JOIN 으로 조회, 정규화)
> - 최종 컬럼 수: **9개** (v1 17개 → v2 16개 → v3 9개)

---

## 목차

- [STEP 10. customer_product_application — 상품 신청 이력](#step-10-customer_product_application--상품-신청-이력)
- [STEP 11. customer_recommend_daily — 일별 추천 성과 mart](#step-11-customer_recommend_daily--일별-추천-성과-mart)
- [두 테이블의 관계와 데이터 흐름](#두-테이블의-관계와-데이터-흐름)
- [샘플 쿼리](#샘플-쿼리)
- [기존 테이블과의 정합성](#기존-테이블과의-정합성)
- [검증 쿼리](#검증-쿼리)

---

## STEP 10. `customer_product_application` — 상품 신청 이력

### 용도

**고객이 어떤 상품을 신청했는지의 "사실"만 기록하는 이벤트 로그.**

신청자 컨택 정보 (이름/전화/이메일/메모/신청금액) 는 본 테이블에 저장하지 않습니다.
이런 정보는 별도 시스템 (CRM, 영업 채널 등) 에서 관리되며, Aurora 에는 신청
이벤트의 골격만 적재합니다.

### 설계 원칙

1. **Lean 이벤트 로그** — 누가(`global_id`/`ls_user_id`) 어떤 상품(`product_id`)을 언제(`created_at`) 신청했는지 + 처리 상태만
2. **자유텍스트 배제** — `status` 는 ENUM 으로 값 검증
3. **정규화 유지** — 상품 정보는 `product_master` JOIN, 신청금액은 상품 스펙(`product_option.min_deposit_amount` 등) 으로 추정 가능
4. **다른 테이블과 타입 통일** — `global_id` VARCHAR(50)

### 컬럼 정보 (총 9개)

#### 🔑 식별자 (3)

| 컬럼 | 타입 | NULL | 설명 |
|---|---|---|---|
| `application_id` | VARCHAR(40) | NOT NULL (PK) | 신청 고유 ID. 포맷: `APP-YYYYMMDDHHMMSS-{ls_user_id 끝6자}` |
| `global_id` | VARCHAR(50) | NOT NULL | 그룹 통합 고객 ID. **`customer_recommend_history`, `customer_dashboard_log` 와 동일 타입** |
| `ls_user_id` | VARCHAR(40) | NULL | LifeSync 내부 사용자 ID |

#### 🛒 대상 상품 (1)

| 컬럼 | 타입 | NULL | 설명 |
|---|---|---|---|
| `product_id` | BIGINT | NOT NULL | `product_master.product_id` FK 참조. 상품 정보(code/name/금액 등) 는 모두 JOIN 으로 조회 |

#### 🔄 처리 상태 (3)

| 컬럼 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `status` | **ENUM** | `'RECEIVED'` | 값 강제 검증 (아래 상태 전이도 참조) |
| `reviewer_id` | VARCHAR(40) | NULL | 검토자 ID (admin) |
| `reviewed_at` | DATETIME | NULL | 검토 완료 시각 |

**`status` 허용값 (ENUM):**

```
RECEIVED ──→ IN_REVIEW ──┬──→ APPROVED
  (접수)      (검토중)    ├──→ REJECTED
                          └──→ CANCELED
```

ENUM 이외 값을 INSERT 하면 `ERROR 1265: Data truncated for column 'status'` 로 차단됩니다.

#### ⏰ 타임스탬프 (2)

| 컬럼 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `created_at` | DATETIME | CURRENT_TIMESTAMP | 신청 시각 (자동) |
| `updated_at` | DATETIME | CURRENT_TIMESTAMP ON UPDATE | 마지막 수정 시각 (자동 갱신) |

### 인덱스 (4개)

| 인덱스명 | 컬럼 | 목적 |
|---|---|---|
| `idx_application_global` | `global_id` | 고객별 신청 이력 조회 |
| `idx_application_product` | `product_id` | 상품별 신청 통계 |
| `idx_application_status` | `(status, created_at)` | 상태별 신청 목록 (admin 화면) |
| `idx_application_created` | `created_at` | 기간별 조회 |

### 외래키

| 제약명 | 컬럼 | 참조 | 동작 |
|---|---|---|---|
| `fk_application_product` | `product_id` | `product_master(product_id)` | ON DELETE **RESTRICT** · ON UPDATE **CASCADE** |

- `RESTRICT`: 신청 기록이 있는 상품은 삭제 불가 (이력 보호)
- `CASCADE`: 상품 ID가 바뀌면 자동 반영

### 어떤 정보가 빠졌고, 왜 빠졌나

| 제거된 컬럼 | 빠진 이유 |
|---|---|
| `applicant_name` | 컨택 정보 — Aurora 가 들고 있을 책임 아님 |
| `applicant_phone` | 컨택 정보 — 검증 규칙도 없는 자유텍스트라 데이터 품질 보장 어려움 |
| `applicant_email` | 컨택 정보 |
| `apply_amount` | 자유텍스트 ("100만원" / "보장 5천만원") → 통계 불가, 상품 스펙과 충돌 가능. 상품별 정형 금액은 `product_option` 에 이미 있음 |
| `contact_time` | 컨택 정보, 검증 없는 자유텍스트 |
| `memo` | 컨택 정보 |
| `agree_marketing` | 마케팅 동의 정보 — 별도 동의 관리 시스템 영역 |

---

## STEP 11. `customer_recommend_daily` — 일별 추천 성과 mart

### 용도

매일 새벽 3시(KST) `analytics_aggregator` Lambda 가 `customer_recommend_history` 를
날짜별로 GROUP BY 집계해서 적재하는 **요약 테이블 (mart)**.

admin 대시보드에서 추천 성과 추이 차트를 빠르게 그릴 때 사용.

### 컬럼 정보 (총 8개)

#### 🔑 식별자

| 컬럼 | 타입 | NULL | 설명 |
|---|---|---|---|
| `date` | DATE | NOT NULL (PK) | 집계 기준 일자 (하루에 한 행) |

#### 📈 카운트

| 컬럼 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `recommended` | INT | 0 (NOT NULL) | 그날 추천 발생 건수 |
| `clicked` | INT | 0 (NOT NULL) | 그중 클릭된 건수 |
| `purchased` | INT | 0 (NOT NULL) | 그중 실제 신청/구매로 이어진 건수 |

#### 📊 비율 지표

| 컬럼 | 타입 | 설명 | 계산식 |
|---|---|---|---|
| `ctr` | DECIMAL(5,2) | Click-Through Rate (%) | `clicked / recommended × 100` |
| `cvr` | DECIMAL(5,2) | Conversion Rate (%) | `purchased / clicked × 100` (클릭한 건 중 구매로 이어진 비율) |

#### ⏰ 타임스탬프

| 컬럼 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `created_at` | DATETIME | CURRENT_TIMESTAMP | 집계 적재 시각 |
| `updated_at` | DATETIME | CURRENT_TIMESTAMP ON UPDATE | 재집계 시각 (자동 갱신) |

### 인덱스

| 인덱스명 | 컬럼 | 목적 |
|---|---|---|
| `idx_recommend_daily_date` | `date` | 기간별 조회 (PK 가 date 지만 명시 인덱스 추가) |

### 추가 효과 — history 테이블에 인덱스 자동 추가

이 SQL 실행 시 batch 집계 성능을 위해 기존 history 테이블에도 인덱스를 만듭니다:

```sql
CREATE INDEX idx_recommended_at ON customer_recommend_history(recommended_at);
```

→ Lambda 가 매일 `GROUP BY DATE(recommended_at)` 쿼리를 빠르게 돌릴 수 있게 됩니다.

---

## 두 테이블의 관계와 데이터 흐름

```
[고객 행동]                          [집계]                         [활용]

추천 노출 → customer_recommend_history ─┐
                  (raw event log)        │
                                          │  매일 03:00 KST
                                          │  Lambda batch
                                          ▼
                              customer_recommend_daily  ──→  admin 대시보드
                                  (일별 mart)                (성과 차트)


상품 클릭 → "신청하기" 버튼
              → POST /api/product/<code>/apply
                  → customer_product_application  ──→  admin 신청 관리
                       (신청 이벤트 로그)                  (RECEIVED → APPROVED)
                            │                                    │
                            └─ FK ─→ product_master              └─ 컨택은
                                       (code/name JOIN)             별도 시스템
```

### 핵심 차이

| 항목 | `customer_product_application` | `customer_recommend_daily` |
|---|---|---|
| 성격 | **이벤트 로그** (개별 신청 1건 = 1행) | **분석 mart** (하루 = 1행) |
| 입력 주체 | platform API (실시간 INSERT) | Lambda batch (일 1회 적재) |
| 데이터 양 | 신청자 수만큼 (수만~수십만) | 매일 1행씩 (1년 = 365행) |
| FK | 있음 (product_master) | 없음 |
| 주 사용처 | admin 신청 관리 화면 | admin 대시보드 추세 차트 |

---

## 샘플 쿼리

### customer_product_application

```sql
-- 신청 1건 등록 (platform API 가 실행) — 9개 컬럼 중 4개만 명시
INSERT INTO customer_product_application
(application_id, global_id, ls_user_id, product_id)
VALUES
('APP-20260517143052-A3F8C1', 'G00012345', 'LSUSER-A3F8C1', 1234);
-- status 는 ENUM default 'RECEIVED', created_at 은 자동


-- admin 화면: 검토 대기 신청 목록 (상품 정보는 JOIN 으로)
SELECT
    a.application_id,
    a.global_id,
    p.product_code,
    p.product_name,
    c.company_name,
    a.created_at
FROM customer_product_application a
JOIN product_master  p ON a.product_id = p.product_id
JOIN company_master  c ON p.company_id = c.company_id
WHERE a.status = 'RECEIVED'
ORDER BY a.created_at DESC
LIMIT 20;


-- admin: 신청 승인 처리 (ENUM 값만 가능)
UPDATE customer_product_application
SET status      = 'APPROVED',
    reviewer_id = 'ADMIN-001',
    reviewed_at = NOW()
WHERE application_id = 'APP-20260517143052-A3F8C1';


-- 특정 고객의 신청 이력 (카테고리 정보까지 포함)
SELECT
    a.application_id,
    p.product_code,
    p.product_name,
    cat.category_name,
    a.status,
    a.created_at
FROM customer_product_application a
JOIN product_master   p   ON a.product_id  = p.product_id
JOIN category_master  cat ON p.category_id = cat.category_id
WHERE a.global_id = 'G00012345'
ORDER BY a.created_at DESC;


-- 상품별 신청 건수 TOP 10
SELECT
    p.product_code,
    p.product_name,
    COUNT(*) AS apply_count
FROM customer_product_application a
JOIN product_master p ON a.product_id = p.product_id
GROUP BY p.product_id, p.product_code, p.product_name
ORDER BY apply_count DESC
LIMIT 10;


-- 일별 상태별 신청 추이
SELECT
    DATE(created_at) AS apply_date,
    status,
    COUNT(*)         AS cnt
FROM customer_product_application
WHERE created_at >= CURRENT_DATE - INTERVAL 7 DAY
GROUP BY DATE(created_at), status
ORDER BY apply_date DESC, status;


-- URL 의 product_code 로 신청하는 케이스 (platform API)
INSERT INTO customer_product_application
(application_id, global_id, ls_user_id, product_id)
SELECT
    'APP-20260517144210-C5D7E2',
    'G00099999',
    'LSUSER-C5D7E2',
    p.product_id
FROM product_master p
WHERE p.product_code = 'BANK-DEPOSIT-00001-01';
```

### customer_recommend_daily

```sql
-- Lambda batch: 어제자 추천 성과 집계 후 적재
INSERT INTO customer_recommend_daily
(date, recommended, clicked, purchased, ctr, cvr)
SELECT
    DATE(recommended_at)                                    AS date,
    COUNT(*)                                                AS recommended,
    SUM(CASE WHEN clicked_flag   = 'Y' THEN 1 ELSE 0 END)   AS clicked,
    SUM(CASE WHEN purchased_flag = 'Y' THEN 1 ELSE 0 END)   AS purchased,
    ROUND(SUM(CASE WHEN clicked_flag   = 'Y' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS ctr,
    ROUND(SUM(CASE WHEN purchased_flag = 'Y' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN clicked_flag = 'Y' THEN 1 ELSE 0 END), 0)
          * 100, 2) AS cvr
FROM customer_recommend_history
WHERE DATE(recommended_at) = CURRENT_DATE - INTERVAL 1 DAY
GROUP BY DATE(recommended_at)
ON DUPLICATE KEY UPDATE
    recommended = VALUES(recommended),
    clicked     = VALUES(clicked),
    purchased   = VALUES(purchased),
    ctr         = VALUES(ctr),
    cvr         = VALUES(cvr);


-- admin 대시보드: 최근 30일 성과 추이
SELECT date, recommended, clicked, purchased, ctr, cvr
FROM customer_recommend_daily
WHERE date >= CURRENT_DATE - INTERVAL 30 DAY
ORDER BY date ASC;


-- 월별 요약
SELECT
    DATE_FORMAT(date, '%Y-%m')     AS month,
    SUM(recommended)               AS total_recommended,
    SUM(clicked)                   AS total_clicked,
    SUM(purchased)                 AS total_purchased,
    ROUND(SUM(clicked)   / SUM(recommended)       * 100, 2) AS avg_ctr,
    ROUND(SUM(purchased) / NULLIF(SUM(clicked),0) * 100, 2) AS avg_cvr
FROM customer_recommend_daily
GROUP BY DATE_FORMAT(date, '%Y-%m')
ORDER BY month DESC;
```

---

## 기존 테이블과의 정합성

신규 테이블은 기존 테이블들과 다음과 같이 정합성을 맞춰 설계했습니다.

### `global_id` 타입 통일

| 테이블 | 타입 |
|---|---|
| `customer_recommend_history` | VARCHAR(**50**) |
| `customer_dashboard_log` | VARCHAR(**50**) |
| `customer_product_application` | VARCHAR(**50**) ✅ 통일 |

같은 고객 ID 로 세 테이블을 JOIN 할 때 타입 불일치로 인한 암묵적 형변환이 발생하지 않습니다.

### `product_id` FK 일관성

`product_master(product_id)` 를 참조하는 테이블들:

| 테이블 | FK 컬럼 | 비고 |
|---|---|---|
| `product_option` | `product_id` | 기존 |
| `customer_recommend_history` | `product_id` | 기존 |
| `customer_product_application` | `product_id` ✅ | 신규, **상품 정보는 JOIN 으로** |

### 자유텍스트 컬럼 정리

신청 테이블에서 `apply_amount` 자유텍스트가 빠진 배경:

- 예금 상품은 `product_option.min_deposit_amount` ("100,000,000 KRW" 같은 정형값) 보유
- 대출 상품은 `product_option.loan_limit`
- 적금 상품은 `product_option.monthly_limit`
- 카드 상품은 `product_option.annual_fee`

상품별 의미가 다르고 이미 정형 데이터가 있는 상황에서, 신청 시점의
자유텍스트 금액 ("100만원") 은 시스템 일관성을 해칩니다. 신청 결과는
"어떤 상품을 신청했다" 까지만 기록하고, 금액 정보가 필요하면 상품 스펙
(`product_option`) 을 참조합니다.

---

## 검증 쿼리

빌드 직후 신규 테이블 정상 생성 여부 확인:

```sql
USE lifesync360;

-- 1. 테이블 존재 확인
SHOW TABLES LIKE 'customer_product_application';
SHOW TABLES LIKE 'customer_recommend_daily';

-- 2. 컬럼 구조 확인 (9개 컬럼)
DESCRIBE customer_product_application;
DESCRIBE customer_recommend_daily;

-- 3. global_id 타입 통일 확인 (3개 모두 varchar(50))
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'lifesync360'
  AND COLUMN_NAME = 'global_id'
ORDER BY TABLE_NAME;

-- 4. status ENUM 확인
SELECT COLUMN_NAME, COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'lifesync360'
  AND TABLE_NAME   = 'customer_product_application'
  AND COLUMN_NAME  = 'status';

-- 5. 인덱스 확인
SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'lifesync360'
  AND TABLE_NAME IN ('customer_product_application', 'customer_recommend_daily')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- 6. FK 확인
SELECT
    TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'lifesync360'
  AND TABLE_NAME = 'customer_product_application'
  AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 7. history 테이블 batch 인덱스 확인
SELECT INDEX_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'lifesync360'
  AND TABLE_NAME   = 'customer_recommend_history'
  AND COLUMN_NAME  = 'recommended_at';
```

-- ===============================================================
-- STEP 10. customer_product_application — 상품 신청 이력
--
-- 목적:
-- 고객이 어떤 상품을 신청했는지의 "사실"만 기록.
-- 컨택 정보 (이름/전화/이메일/메모) 는 별도 시스템에서 관리.
--
-- 설계 원칙:
-- 1. "신청했다" 이벤트만 적재 (lean)
-- 2. 컨택/금액/내용 등 자유텍스트 항목 제외
-- 3. status 는 ENUM 으로 값 검증
--
-- FK:
-- product_id REFERENCES product_master(product_id)
--    → product_master 적재 완료 후 실행 필요
--
-- 멱등성:
-- CREATE TABLE IF NOT EXISTS + INDEX 동적 SQL
--    → Aurora_MySQL_DB_Create.sql 와 본 파일 둘 다 돌려도 안전
-- ===============================================================


USE lifesync360;


-- ===============================================================
-- 10. 상품 신청 이력
-- ===============================================================

CREATE TABLE IF NOT EXISTS customer_product_application (

    application_id   VARCHAR(40)  PRIMARY KEY,
                                              -- APP-YYYYMMDDHHMMSS-{ls_user_id last 6 char}

    global_id        VARCHAR(50)  NOT NULL,
                                              -- customer_recommend_history / dashboard_log 와 동일 타입
    ls_user_id       VARCHAR(40),

    product_id       BIGINT       NOT NULL,
                                              -- 상품 정보 (code/name 등) 는 product_master JOIN

    status           ENUM('RECEIVED','IN_REVIEW','APPROVED','REJECTED','CANCELED')
                     NOT NULL DEFAULT 'RECEIVED',
                                              -- 신청 처리 단계

    reviewer_id      VARCHAR(40),
                                              -- 검토자 ID (admin)
    reviewed_at      DATETIME,
                                              -- 검토 완료 시각

    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_application_product
    FOREIGN KEY (product_id)
    REFERENCES product_master(product_id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===============================================================
-- INDEX (멱등 처리)
--
-- CREATE INDEX 는 멱등성이 없으므로
-- INFORMATION_SCHEMA 체크 후 동적 SQL 로 처리.
-- ===============================================================

-- idx_application_global
SET @idx_exists = (
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'customer_product_application'
      AND INDEX_NAME   = 'idx_application_global'
);
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_application_global ON customer_product_application(global_id)',
    'SELECT "idx_application_global already exists - SKIP" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- idx_application_product
SET @idx_exists = (
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'customer_product_application'
      AND INDEX_NAME   = 'idx_application_product'
);
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_application_product ON customer_product_application(product_id)',
    'SELECT "idx_application_product already exists - SKIP" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- idx_application_status
SET @idx_exists = (
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'customer_product_application'
      AND INDEX_NAME   = 'idx_application_status'
);
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_application_status ON customer_product_application(status, created_at)',
    'SELECT "idx_application_status already exists - SKIP" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- idx_application_created
SET @idx_exists = (
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'customer_product_application'
      AND INDEX_NAME   = 'idx_application_created'
);
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_application_created ON customer_product_application(created_at)',
    'SELECT "idx_application_created already exists - SKIP" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- ===============================================================
-- 완료
-- ===============================================================

SELECT 'customer_product_application Created Successfully' AS result;

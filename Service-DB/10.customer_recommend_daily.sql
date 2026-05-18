-- ===============================================================
-- STEP 11. customer_recommend_daily — 일별 추천 성과 mart
--
-- 목적:
-- P3 r10 — 일배치 (analytics_aggregator Lambda) 가 매일
-- customer_recommend_history 를 GROUP BY DATE 집계하여 적재.
--
-- 컬럼:
-- recommended / clicked / purchased / ctr / cvr
--
-- 관련 인덱스:
-- customer_recommend_history(recommended_at)
--    → batch GROUP BY 최적화. 존재 여부 체크 후 동적 생성.
--
-- 멱등성:
-- CREATE TABLE IF NOT EXISTS + INDEX 동적 SQL
--    → Aurora_MySQL_DB_Create.sql 와 본 파일 둘 다 돌려도 안전
-- ===============================================================


USE lifesync360;


-- ===============================================================
-- 11. 일별 추천 성과 mart
-- ===============================================================

CREATE TABLE IF NOT EXISTS customer_recommend_daily (

    date           DATE         PRIMARY KEY,

    recommended    INT          NOT NULL DEFAULT 0,
    clicked        INT          NOT NULL DEFAULT 0,
    purchased      INT          NOT NULL DEFAULT 0,

    ctr            DECIMAL(5,2),
    cvr            DECIMAL(5,2),

    created_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME     DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===============================================================
-- INDEX (mart 테이블, 멱등 처리)
-- ===============================================================

-- idx_recommend_daily_date
SET @idx_exists = (
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'customer_recommend_daily'
      AND INDEX_NAME   = 'idx_recommend_daily_date'
);
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_recommend_daily_date ON customer_recommend_daily(date)',
    'SELECT "idx_recommend_daily_date already exists - SKIP" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- ===============================================================
-- INDEX (history 테이블, batch 최적화, 멱등 처리)
-- ===============================================================

-- idx_recommended_at
SET @idx_exists = (
    SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'customer_recommend_history'
      AND INDEX_NAME   = 'idx_recommended_at'
);
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_recommended_at ON customer_recommend_history(recommended_at)',
    'SELECT "idx_recommended_at already exists - SKIP" AS info');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- ===============================================================
-- 완료
-- ===============================================================

SELECT 'customer_recommend_daily Created Successfully' AS result;

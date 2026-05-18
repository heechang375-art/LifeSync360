-- ===============================================================
-- STEP 9. customer_product_application — 상품 신청 내역
-- platform /api/product/<code>/apply POST 결과 적재.
-- ===============================================================

USE lifesync360;

CREATE TABLE IF NOT EXISTS customer_product_application
(
    application_id   VARCHAR(40)  PRIMARY KEY,    -- APP-YYYYMMDDHHMMSS-{ls_user_id 마지막 6자}

    global_id        VARCHAR(20)  NOT NULL,
    ls_user_id       VARCHAR(40),

    product_id       BIGINT       NOT NULL,
    product_code     VARCHAR(50)  NOT NULL,

    applicant_name   VARCHAR(40)  NOT NULL,
    applicant_phone  VARCHAR(20)  NOT NULL,
    applicant_email  VARCHAR(100),

    apply_amount     VARCHAR(100),                -- "100만원" / "보장 5천만원" 등 자유 텍스트
    contact_time     VARCHAR(20)  DEFAULT 'any',  -- any / morning / afternoon / evening
    memo             TEXT,

    agree_marketing  CHAR(1)      DEFAULT 'N',    -- Y / N

    status           VARCHAR(20)  DEFAULT 'RECEIVED',
                                                  -- RECEIVED / IN_REVIEW / APPROVED / REJECTED / CANCELED
    reviewer_id      VARCHAR(40),
    reviewed_at      DATETIME,

    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_global_id     (global_id),
    INDEX idx_product_id    (product_id),
    INDEX idx_status        (status, created_at),
    INDEX idx_created_at    (created_at),

    CONSTRAINT fk_application_product
        FOREIGN KEY (product_id) REFERENCES product_master(product_id)
        ON DELETE RESTRICT ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===============================================================
-- 검증 — 테이블 + 인덱스 + FK
-- ===============================================================
SHOW CREATE TABLE customer_product_application\G

SELECT
    INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'customer_product_application'
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

CREATE DATABASE IF NOT EXISTS lifesync_onprem CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lifesync_onprem;

CREATE TABLE IF NOT EXISTS master_customer (
    global_id            VARCHAR(30)  PRIMARY KEY,
    representative_name  VARCHAR(100) NOT NULL,
    birth_dt             DATE,
    gender               CHAR(1),
    nationality          VARCHAR(10)  DEFAULT 'KR',
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_identity_map (
    id                    BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_id             VARCHAR(30)  NOT NULL,
    company_id            VARCHAR(20)  NOT NULL,
    affiliate_customer_id VARCHAR(50)  NOT NULL,
    linked_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_map (global_id, company_id),
    INDEX idx_affiliate (affiliate_customer_id)
);

CREATE TABLE IF NOT EXISTS customer_pii_secure (
    id            BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_id     VARCHAR(30)  NOT NULL,
    pii_type      VARCHAR(30),
    encrypted_val TEXT,
    token_id      VARCHAR(36),
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_global (global_id)
);

-- SHA256 해시 → UUID 토큰 매핑 (token_service가 관리)
CREATE TABLE IF NOT EXISTS token_map (
    token_id      VARCHAR(36)  NOT NULL PRIMARY KEY,
    field_name    VARCHAR(30)  NOT NULL,
    original_hash VARCHAR(64)  NOT NULL,
    global_id     VARCHAR(30),
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_hash (original_hash),
    INDEX idx_global (global_id)
);

CREATE TABLE IF NOT EXISTS matching_audit_log (
    id            BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_id     VARCHAR(30),
    action_type   VARCHAR(30),
    action_detail JSON,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_global (global_id)
);

CREATE TABLE IF NOT EXISTS customer_360_profile (
    global_id       VARCHAR(30)   PRIMARY KEY,
    grade           VARCHAR(20)   DEFAULT 'BASIC',
    lifesync_score  DECIMAL(5,1),
    updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consent (
    id          BIGINT      AUTO_INCREMENT PRIMARY KEY,
    global_id   VARCHAR(30) NOT NULL,
    consent_key VARCHAR(30) NOT NULL,
    consent_yn  CHAR(1)     DEFAULT 'N',
    updated_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_consent (global_id, consent_key)
);

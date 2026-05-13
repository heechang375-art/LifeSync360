CREATE DATABASE IF NOT EXISTS lifesync_onprem CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lifesync_onprem;

CREATE TABLE IF NOT EXISTS master_customer (
    global_customer_id   VARCHAR(30)  PRIMARY KEY,
    customer_status      VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    vip_grade            VARCHAR(10)  NOT NULL DEFAULT 'NORMAL',
    customer_type        VARCHAR(20)  NOT NULL DEFAULT 'INDIVIDUAL',
    first_created_dt     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    last_updated_dt      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id              BIGINT       AUTO_INCREMENT PRIMARY KEY,
    ls_user_id           VARCHAR(30)  UNIQUE NOT NULL,
    global_customer_id   VARCHAR(30),
    login_email          VARCHAR(200) UNIQUE NOT NULL,
    password_hash        VARCHAR(255) NOT NULL,
    mobile               VARCHAR(20),
    user_status          VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    consent_completed    CHAR(1)      NOT NULL DEFAULT 'N',
    created_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    last_login_dt        TIMESTAMP    NULL,
    INDEX idx_global (global_customer_id),
    CONSTRAINT fk_users_customer FOREIGN KEY (global_customer_id) REFERENCES master_customer(global_customer_id)
);

CREATE TABLE IF NOT EXISTS customer_identity_map (
    id                   BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_customer_id   VARCHAR(30)  NOT NULL,
    domain               VARCHAR(30)  NOT NULL,
    source_customer_id   VARCHAR(50)  NOT NULL,
    match_type           VARCHAR(10)  NOT NULL DEFAULT 'EXACT',
    active_flag          CHAR(1)      NOT NULL DEFAULT 'Y',
    created_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_map (global_customer_id, domain),
    INDEX idx_source (source_customer_id),
    CONSTRAINT fk_identity_customer FOREIGN KEY (global_customer_id) REFERENCES master_customer(global_customer_id)
);

CREATE TABLE IF NOT EXISTS customer_pii_secure (
    pii_token            VARCHAR(36)  NOT NULL PRIMARY KEY,
    global_customer_id   VARCHAR(30)  NOT NULL,
    customer_name_enc    TEXT,
    ssn_enc              TEXT,
    mobile_enc           TEXT,
    email_enc            TEXT,
    address_enc          TEXT,
    created_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_global (global_customer_id),
    CONSTRAINT fk_pii_customer FOREIGN KEY (global_customer_id) REFERENCES master_customer(global_customer_id)
);

CREATE TABLE IF NOT EXISTS customer_360_profile (
    global_customer_id   VARCHAR(30)  PRIMARY KEY,
    gender               CHAR(1),
    age_band             VARCHAR(10),
    region               VARCHAR(50),
    income_grade         VARCHAR(10),
    asset_grade          VARCHAR(10),
    wearable_flag        CHAR(1)      NOT NULL DEFAULT 'N',
    health_score         DECIMAL(5,1),
    finance_score        DECIMAL(5,1),
    asset_score          DECIMAL(5,1),
    lifesync_score       DECIMAL(5,1),
    last_calc_dt         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_360_customer FOREIGN KEY (global_customer_id) REFERENCES master_customer(global_customer_id)
);

CREATE TABLE IF NOT EXISTS consent (
    id                   BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_customer_id   VARCHAR(30)  NOT NULL,
    domain               VARCHAR(30)  NOT NULL,
    consent_flag         CHAR(1)      NOT NULL DEFAULT 'N',
    consent_version      VARCHAR(10)  NOT NULL DEFAULT 'v1.0',
    revoke_dt            TIMESTAMP    NULL,
    created_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_consent (global_customer_id, domain),
    CONSTRAINT fk_consent_customer FOREIGN KEY (global_customer_id) REFERENCES master_customer(global_customer_id)
);

CREATE TABLE IF NOT EXISTS matching_audit_log (
    audit_id                   BIGINT       AUTO_INCREMENT PRIMARY KEY,
    request_id                 VARCHAR(36)  UNIQUE NOT NULL,
    ls_user_id                 VARCHAR(30),
    match_rule                 VARCHAR(50),
    result                     VARCHAR(20),
    matched_global_customer_id VARCHAR(30),
    match_score                DECIMAL(5,1),
    consent_dt                 TIMESTAMP    NULL,
    request_dt                 TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    remarks                    TEXT,
    INDEX idx_ls_user (ls_user_id)
);

CREATE TABLE IF NOT EXISTS token_map (
    token_id             VARCHAR(36)  NOT NULL PRIMARY KEY,
    field_name           VARCHAR(30)  NOT NULL,
    original_hash        VARCHAR(64)  NOT NULL,
    global_customer_id   VARCHAR(30),
    created_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_hash (original_hash),
    INDEX idx_global (global_customer_id)
);

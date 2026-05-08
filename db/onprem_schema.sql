-- LifeSync360 On-Prem MySQL 스키마
-- Local VM (MySQL)에 적용. Ansible playbooks/mysql.yml이 배포 시 실행.
-- 실행: mysql -u root -p < onprem_schema.sql

CREATE DATABASE IF NOT EXISTS lifesync_onprem CHARACTER SET utf8mb4;
USE lifesync_onprem;

CREATE TABLE IF NOT EXISTS users (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    ls_user_id    VARCHAR(30)  UNIQUE NOT NULL,
    email         VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS master_customer (
    global_id            VARCHAR(30) PRIMARY KEY,
    representative_name  VARCHAR(300),
    birth_dt             VARCHAR(200),
    gender               CHAR(1),
    nationality          VARCHAR(10) DEFAULT 'KR',
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_identity_map (
    id                    BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id             VARCHAR(30) NOT NULL,
    company_id            VARCHAR(20) NOT NULL,
    affiliate_customer_id VARCHAR(50) NOT NULL,
    linked_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_map (global_id, company_id),
    INDEX idx_affiliate (affiliate_customer_id)
);

CREATE TABLE IF NOT EXISTS customer_pii_secure (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id     VARCHAR(30) NOT NULL,
    pii_type      VARCHAR(30),
    encrypted_val TEXT,
    token_id      VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_global (global_id)
);

CREATE TABLE IF NOT EXISTS matching_audit_log (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id     VARCHAR(30),
    action_type   VARCHAR(30),
    action_detail JSON,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_global (global_id)
);

CREATE TABLE IF NOT EXISTS customer_360_profile (
    global_id       VARCHAR(30) PRIMARY KEY,
    grade           VARCHAR(20) DEFAULT 'BASIC',
    lifesync_score  DECIMAL(5,1),
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consent (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id   VARCHAR(30) NOT NULL,
    consent_key VARCHAR(30) NOT NULL,
    consent_yn  CHAR(1) DEFAULT 'N',
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_consent (global_id, consent_key)
);

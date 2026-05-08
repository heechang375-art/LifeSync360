-- LifeSync360 Aurora MySQL 스키마
-- 실행: mysql -h <aurora-endpoint> -u admin -p lifesync < aurora_schema.sql

CREATE DATABASE IF NOT EXISTS lifesync CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lifesync;

CREATE TABLE IF NOT EXISTS users (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    ls_user_id    VARCHAR(30)  UNIQUE NOT NULL,
    global_id     VARCHAR(30),
    email         VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL,
    grade         VARCHAR(20)  NOT NULL DEFAULT 'BASIC',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consent (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id   VARCHAR(30) NOT NULL,
    consent_key VARCHAR(30) NOT NULL,
    consent_yn  CHAR(1)     NOT NULL DEFAULT 'N',
    updated_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_consent (global_id, consent_key)
);

CREATE TABLE IF NOT EXISTS company_master (
    company_id   VARCHAR(20)  PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    company_type VARCHAR(30)  NOT NULL,
    is_active    TINYINT      DEFAULT 1,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO company_master (company_id, company_name, company_type) VALUES
    ('bank',               'LS 은행',       'bank'),
    ('card',               'LS 카드',       'card'),
    ('insurance',          'LS 보험',       'insurance'),
    ('internet_insurance', 'LS 온라인보험', 'internet_insurance'),
    ('securities',         'LS 증권',       'securities'),
    ('healthcare',         'LS 헬스케어',   'healthcare'),
    ('hospital',           'LS 병원',       'hospital');

CREATE TABLE IF NOT EXISTS category_master (
    category_id   VARCHAR(50)  PRIMARY KEY,
    company_id    VARCHAR(20)  NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    category_type VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS product_master (
    product_id    VARCHAR(50)  PRIMARY KEY,
    company_id    VARCHAR(20)  NOT NULL,
    category_id   VARCHAR(50),
    product_type  VARCHAR(50),
    product_name  VARCHAR(200) NOT NULL,
    product_desc  TEXT,
    product_tag   VARCHAR(50),
    min_grade     VARCHAR(20)  DEFAULT 'BASIC',
    is_active     TINYINT      DEFAULT 1,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_option (
    option_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id   VARCHAR(50) NOT NULL,
    option_key   VARCHAR(100) DEFAULT 'benefit',
    option_value TEXT,
    sort_order   INT          DEFAULT 0,
    INDEX idx_product (product_id)
);

CREATE TABLE IF NOT EXISTS recommend_rule (
    rule_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id    VARCHAR(50),
    target_grade  VARCHAR(20),
    condition_key VARCHAR(100),
    condition_val TEXT,
    priority      INT DEFAULT 0,
    UNIQUE KEY uq_rule (product_id, condition_key)
);

CREATE TABLE IF NOT EXISTS cross_sell_rule (
    rule_id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_product_id VARCHAR(50),
    target_product_id VARCHAR(50),
    rule_desc         TEXT,
    priority          INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS campaign_master (
    campaign_id   VARCHAR(30)  PRIMARY KEY,
    campaign_name VARCHAR(200) NOT NULL,
    campaign_type VARCHAR(30),
    target_grade  VARCHAR(20),
    start_dt      DATE,
    end_dt        DATE,
    is_active     TINYINT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customer_recommend_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id       VARCHAR(30) NOT NULL,
    product_id      VARCHAR(50) NOT NULL,
    recommended_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    clicked_at      TIMESTAMP   NULL,
    purchased_at    TIMESTAMP   NULL,
    INDEX idx_global  (global_id),
    INDEX idx_product (product_id)
);

CREATE TABLE IF NOT EXISTS customer_dashboard_log (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_id     VARCHAR(30) NOT NULL,
    action_type   VARCHAR(50),
    action_detail JSON,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_global  (global_id),
    INDEX idx_created (created_at)
);

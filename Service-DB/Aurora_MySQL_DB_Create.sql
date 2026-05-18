-- ===============================================================
-- LifeSync360 Aurora MySQL Full Database Create SQL
--
-- 목적:
-- 금융그룹 통합 추천 플랫폼 운영 DB 생성
--
-- 대상:
-- Amazon Aurora MySQL 8.x
--
-- 포함:
-- 1. 회사 마스터
-- 2. 카테고리 마스터
-- 3. 상품 마스터
-- 4. 상품 옵션
-- 5. 추천 규칙
-- 6. 교차판매 규칙
-- 7. 캠페인 마스터
-- 8. 고객 추천 이력
-- 9. 고객 Dashboard 로그
-- 10. 상품 신청 이력             (2026-05-17 ADDED)
-- 11. 일별 추천 성과 mart        (2026-05-17 ADDED)
-- ===============================================================


-- ===============================================================
-- DATABASE
-- ===============================================================
CREATE DATABASE IF NOT EXISTS lifesync360
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE lifesync360;

-- ===============================================================
-- 1. 회사 마스터
-- ===============================================================

CREATE TABLE IF NOT EXISTS company_master (

    company_id       BIGINT AUTO_INCREMENT PRIMARY KEY,

    company_code     VARCHAR(30) NOT NULL UNIQUE,
    company_name     VARCHAR(100) NOT NULL,

    company_type     VARCHAR(30) NOT NULL,

    active_flag      CHAR(1) DEFAULT 'Y',

    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
                  ON UPDATE CURRENT_TIMESTAMP

) ENGINE=InnoDB;


-- ===============================================================
-- 2. 카테고리 마스터
-- ===============================================================

CREATE TABLE IF NOT EXISTS category_master (

    category_id      BIGINT AUTO_INCREMENT PRIMARY KEY,

    category_code    VARCHAR(30) NOT NULL UNIQUE,
    category_name    VARCHAR(100) NOT NULL,

    active_flag      CHAR(1) DEFAULT 'Y',

    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;

-- ===============================================================
-- 120개 상품명을 바로 product_master에 넣는 것이 아니라, 먼저 기준 상품 후보 테이블인 
-- base_product_pool에 등록하는 것입니다. 이후 이 데이터를 Variant로 확장해서 product_master 10,000건을 생성
-- Base Pool 테이블 생성
-- ===============================================================



DROP TABLE IF EXISTS base_product_pool;

CREATE TABLE IF NOT EXISTS base_product_pool
(
    base_product_id     BIGINT AUTO_INCREMENT PRIMARY KEY,

    company_code        VARCHAR(30) NOT NULL,
    category_code       VARCHAR(30) NOT NULL,

    base_product_name   VARCHAR(200) NOT NULL,
    base_description    TEXT,

    base_grade          VARCHAR(20),
    base_min_score      DECIMAL(8,2),
    base_max_score      DECIMAL(8,2),

    base_risk_level     VARCHAR(20),
    product_theme       VARCHAR(100),

    active_flag         CHAR(1) DEFAULT 'Y',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;



-- ===============================================================
-- Variant 테이블 생성
-- ===============================================================
DROP TABLE IF EXISTS product_variant;

CREATE TABLE IF NOT EXISTS product_variant
(
    variant_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    variant_code    VARCHAR(30) NOT NULL,
    variant_name    VARCHAR(100) NOT NULL,
    variant_desc    VARCHAR(300),
    score_bonus     DECIMAL(8,2) DEFAULT 0,
    priority_bonus  INT DEFAULT 0,
    active_flag     CHAR(1) DEFAULT 'Y',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- ===============================================================
-- 3. 상품 마스터 (핵심)
-- ===============================================================

CREATE TABLE product_master (

    product_id          BIGINT AUTO_INCREMENT PRIMARY KEY,

    company_id          BIGINT NOT NULL,
    category_id         BIGINT NOT NULL,

    product_code        VARCHAR(50) NOT NULL UNIQUE,
    product_name        VARCHAR(200) NOT NULL,

    description         TEXT,

    target_grade        VARCHAR(20),
    min_score           DECIMAL(8,2),
    max_score           DECIMAL(8,2),

    risk_level          VARCHAR(20),

    priority_rank       INT DEFAULT 100,

    active_flag         CHAR(1) DEFAULT 'Y',

    start_date          DATE,
    end_date            DATE,

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
                      ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_company
    FOREIGN KEY (company_id)
    REFERENCES company_master(company_id),

    CONSTRAINT fk_product_category
    FOREIGN KEY (category_id)
    REFERENCES category_master(category_id)

) ENGINE=InnoDB;


-- ===============================================================
-- 4. 상품 옵션
-- ===============================================================

CREATE TABLE IF NOT EXISTS product_option (

    option_id          BIGINT AUTO_INCREMENT PRIMARY KEY,

    product_id         BIGINT NOT NULL,

    option_name        VARCHAR(100),
    option_value       VARCHAR(300),

    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_option_product
    FOREIGN KEY (product_id)
    REFERENCES product_master(product_id)

) ENGINE=InnoDB;


-- ===============================================================
-- 5. 추천 규칙
-- ===============================================================

CREATE TABLE IF NOT EXISTS recommend_rule (

    rule_id            BIGINT AUTO_INCREMENT PRIMARY KEY,

    target_grade       VARCHAR(20),
    action_code        VARCHAR(50),

    min_score          DECIMAL(8,2),
    max_score          DECIMAL(8,2),

    vip_required       CHAR(1) DEFAULT 'N',

    health_min_score   DECIMAL(8,2),

    category_code      VARCHAR(30),

    priority_rank      INT DEFAULT 1,

    active_flag        CHAR(1) DEFAULT 'Y',

    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;




-- ===============================================================
-- 6. 교차판매 규칙
-- ===============================================================

CREATE TABLE IF NOT EXISTS cross_sell_rule (

    cross_id           BIGINT AUTO_INCREMENT PRIMARY KEY,

    base_category      VARCHAR(30),
    target_category    VARCHAR(30),

    priority_rank      INT DEFAULT 1,

    active_flag        CHAR(1) DEFAULT 'Y',

    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;


-- ===============================================================
-- 7. 캠페인 마스터
-- ===============================================================

CREATE TABLE IF NOT EXISTS campaign_master (

    campaign_id        BIGINT AUTO_INCREMENT PRIMARY KEY,

    campaign_name      VARCHAR(200),

    target_grade       VARCHAR(20),

    banner_title       VARCHAR(300),
    banner_desc        TEXT,

    start_date         DATE,
    end_date           DATE,

    active_flag        CHAR(1) DEFAULT 'Y',

    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;


-- ===============================================================
-- 8. 고객 추천 이력
-- ===============================================================

CREATE TABLE IF NOT EXISTS customer_recommend_history (

    hist_id            BIGINT AUTO_INCREMENT PRIMARY KEY,

    global_id          VARCHAR(50) NOT NULL,

    product_id         BIGINT,

    dynamic_score      DECIMAL(8,2),
    dynamic_grade      VARCHAR(20),

    action_code        VARCHAR(50),

    recommended_at     DATETIME DEFAULT CURRENT_TIMESTAMP,

    clicked_flag       CHAR(1) DEFAULT 'N',
    purchased_flag     CHAR(1) DEFAULT 'N',

    CONSTRAINT fk_hist_product
    FOREIGN KEY (product_id)
    REFERENCES product_master(product_id)

) ENGINE=InnoDB;


-- ===============================================================
-- 9. 고객 Dashboard 로그
-- ===============================================================

CREATE TABLE IF NOT EXISTS customer_dashboard_log (

    log_id             BIGINT AUTO_INCREMENT PRIMARY KEY,

    global_id          VARCHAR(50),

    page_type          VARCHAR(30) DEFAULT 'MAIN',

    banner_click       CHAR(1) DEFAULT 'N',
    product_click      CHAR(1) DEFAULT 'N',

    click_product_id   BIGINT NULL,

    session_id         VARCHAR(100),

    view_time          DATETIME DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB;


-- ===============================================================
-- 10. 상품 신청 이력  (2026-05-17 ADDED)
-- ===============================================================

CREATE TABLE IF NOT EXISTS customer_product_application (

    application_id     VARCHAR(40)  PRIMARY KEY,

    global_id          VARCHAR(50)  NOT NULL,
    ls_user_id         VARCHAR(40),

    product_id         BIGINT       NOT NULL,

    status             ENUM('RECEIVED','IN_REVIEW','APPROVED','REJECTED','CANCELED')
                       NOT NULL DEFAULT 'RECEIVED',
    reviewer_id        VARCHAR(40),
    reviewed_at        DATETIME,

    created_at         DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME     DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_application_product
    FOREIGN KEY (product_id)
    REFERENCES product_master(product_id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===============================================================
-- 11. 일별 추천 성과 mart  (2026-05-17 ADDED)
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
-- INDEX
-- ===============================================================

CREATE INDEX idx_product_grade
ON product_master(target_grade);

CREATE INDEX idx_product_score
ON product_master(min_score, max_score);

CREATE INDEX idx_product_active
ON product_master(active_flag);

CREATE INDEX idx_product_priority
ON product_master(priority_rank);

CREATE INDEX idx_hist_global
ON customer_recommend_history(global_id);

CREATE INDEX idx_hist_date
ON customer_recommend_history(recommended_at);

CREATE INDEX idx_log_global
ON customer_dashboard_log(global_id);

CREATE INDEX idx_log_viewtime
ON customer_dashboard_log(view_time);

CREATE INDEX idx_rule_grade
ON recommend_rule(target_grade);

CREATE INDEX idx_rule_action
ON recommend_rule(action_code);

-- ─── 2026-05-17 ADDED ───
CREATE INDEX idx_application_global
ON customer_product_application(global_id);

CREATE INDEX idx_application_product
ON customer_product_application(product_id);

CREATE INDEX idx_application_status
ON customer_product_application(status, created_at);

CREATE INDEX idx_application_created
ON customer_product_application(created_at);

CREATE INDEX idx_recommend_daily_date
ON customer_recommend_daily(date);


-- ===============================================================
-- 완료
-- ===============================================================

SELECT 'LifeSync360 Aurora Schema Created Successfully' AS result;

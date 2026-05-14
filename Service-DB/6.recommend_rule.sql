-- ===============================================================
-- STEP 6. recommend_rule 기본 추천 규칙 생성
-- ===============================================================

USE lifesync360;


INSERT INTO recommend_rule
(
    target_grade,
    action_code,
    min_score,
    max_score,
    vip_required,
    health_min_score,
    category_code,
    priority_rank,
    active_flag
)
VALUES
-- ===============================================================
-- VIP 고객 추천 규칙
-- ===============================================================
('VIP', 'RECOMMEND_PB',          90, 100, 'Y', NULL, 'DEPOSIT',     1, 'Y'),
('VIP', 'RECOMMEND_WM',          90, 100, 'Y', NULL, 'WM',          2, 'Y'),
('VIP', 'RECOMMEND_INVEST',      90, 100, 'Y', NULL, 'ETF',         3, 'Y'),
('VIP', 'RECOMMEND_INSURANCE',   90, 100, 'Y', NULL, 'INSURANCE',   4, 'Y'),
('VIP', 'RECOMMEND_CARD',        90, 100, 'Y', NULL, 'CARD',        5, 'Y'),
('VIP', 'RECOMMEND_HEALTH',      90, 100, 'Y', 70,   'HEALTHCARE',  6, 'Y'),

-- ===============================================================
-- GOLD 고객 추천 규칙
-- ===============================================================
('GOLD', 'RECOMMEND_INVEST',     80, 100, 'N', NULL, 'ETF',         1, 'Y'),
('GOLD', 'RECOMMEND_INVEST',     80, 100, 'N', NULL, 'FUND',        2, 'Y'),
('GOLD', 'RECOMMEND_WM',         80, 100, 'N', NULL, 'WM',          3, 'Y'),
('GOLD', 'RECOMMEND_CARD',       80, 100, 'N', NULL, 'CARD',        4, 'Y'),
('GOLD', 'RECOMMEND_INSURANCE',  80, 100, 'N', NULL, 'INSURANCE',   5, 'Y'),
('GOLD', 'RECOMMEND_HEALTH',     80, 100, 'N', 70,   'HEALTHCARE',  6, 'Y'),

-- ===============================================================
-- SILVER 고객 추천 규칙
-- ===============================================================
('SILVER', 'RECOMMEND_SAVING',    70, 100, 'N', NULL, 'SAVING',      1, 'Y'),
('SILVER', 'RECOMMEND_CARD',      70, 100, 'N', NULL, 'CARD',        2, 'Y'),
('SILVER', 'RECOMMEND_CARD',      70, 100, 'N', NULL, 'LIFESTYLE',   3, 'Y'),
('SILVER', 'RECOMMEND_INVEST',    70, 100, 'N', NULL, 'FUND',        4, 'Y'),
('SILVER', 'RECOMMEND_INSURANCE', 70, 100, 'N', NULL, 'INSURANCE',   5, 'Y'),
('SILVER', 'RECOMMEND_HEALTH',    70, 100, 'N', 65,   'WELLNESS',    6, 'Y'),

-- ===============================================================
-- BASIC 고객 추천 규칙
-- ===============================================================
('BASIC', 'RECOMMEND_SAVING',     60, 100, 'N', NULL, 'SAVING',      1, 'Y'),
('BASIC', 'RECOMMEND_CARD',       60, 100, 'N', NULL, 'CARD',        2, 'Y'),
('BASIC', 'RECOMMEND_CARD',       60, 100, 'N', NULL, 'LIFESTYLE',   3, 'Y'),
('BASIC', 'RECOMMEND_DIRECT_INS', 60, 100, 'N', NULL, 'DIRECT_INS',  4, 'Y'),
('BASIC', 'RECOMMEND_LOAN',       60, 100, 'N', NULL, 'LOAN',        5, 'Y'),
('BASIC', 'RECOMMEND_HEALTH',     60, 100, 'N', 60,   'WELLNESS',    6, 'Y'),

-- ===============================================================
-- CARE 고객 추천 규칙
-- ===============================================================
('CARE', 'RECOMMEND_HEALTH',      0, 100, 'N', 0,    'HEALTHCARE',   1, 'Y'),
('CARE', 'RECOMMEND_WELLNESS',    0, 100, 'N', 0,    'WELLNESS',     2, 'Y'),
('CARE', 'RECOMMEND_TELEMED',     0, 100, 'N', 0,    'TELEMED',      3, 'Y'),
('CARE', 'RECOMMEND_INSURANCE',   0, 100, 'N', 50,   'INSURANCE',    4, 'Y'),
('CARE', 'RECOMMEND_DIRECT_INS',  0, 100, 'N', 50,   'DIRECT_INS',   5, 'Y');


-- ===============================================================
-- STEP 6-2. 확장 추천 규칙 생성
-- ===============================================================

INSERT INTO recommend_rule
(
    target_grade,
    action_code,
    min_score,
    max_score,
    vip_required,
    health_min_score,
    category_code,
    priority_rank,
    active_flag
)
VALUES
-- 금융 안정형 고객
('GOLD',   'RECOMMEND_SAVING',      80, 100, 'N', NULL, 'DEPOSIT',    7, 'Y'),
('SILVER', 'RECOMMEND_SAVING',      70, 100, 'N', NULL, 'DEPOSIT',    7, 'Y'),
('BASIC',  'RECOMMEND_SAVING',      60, 100, 'N', NULL, 'DEPOSIT',    7, 'Y'),

-- 연금/노후 준비
('VIP',    'RECOMMEND_PENSION',     90, 100, 'Y', NULL, 'PENSION',    7, 'Y'),
('GOLD',   'RECOMMEND_PENSION',     80, 100, 'N', NULL, 'PENSION',    7, 'Y'),
('SILVER', 'RECOMMEND_PENSION',     70, 100, 'N', NULL, 'PENSION',    7, 'Y'),

-- 포인트/리워드
('GOLD',   'RECOMMEND_CARD',        80, 100, 'N', NULL, 'POINT',      8, 'Y'),
('SILVER', 'RECOMMEND_CARD',        70, 100, 'N', NULL, 'POINT',      8, 'Y'),
('BASIC',  'RECOMMEND_CARD',        60, 100, 'N', NULL, 'POINT',      8, 'Y'),

-- 건강 점수 기반 보험/헬스케어
('VIP',    'RECOMMEND_HEALTH_INS',  90, 100, 'Y', 80,   'INSURANCE',  8, 'Y'),
('GOLD',   'RECOMMEND_HEALTH_INS',  80, 100, 'N', 75,   'INSURANCE',  8, 'Y'),
('SILVER', 'RECOMMEND_HEALTH_INS',  70, 100, 'N', 70,   'INSURANCE',  8, 'Y'),
('CARE',   'RECOMMEND_HEALTH_INS',  0, 100,  'N', 60,   'INSURANCE',  6, 'Y'),

-- 투자 성향 기반 추천
('VIP',    'RECOMMEND_GLOBAL_INV',  90, 100, 'Y', NULL, 'ETF',        9, 'Y'),
('GOLD',   'RECOMMEND_GLOBAL_INV',  80, 100, 'N', NULL, 'ETF',        9, 'Y'),
('GOLD',   'RECOMMEND_FUND',        80, 100, 'N', NULL, 'FUND',       9, 'Y'),

-- 비대면/모바일 성향 고객
('BASIC',  'RECOMMEND_MOBILE_INS',  60, 100, 'N', NULL, 'DIRECT_INS', 9, 'Y'),
('SILVER', 'RECOMMEND_MOBILE_INS',  70, 100, 'N', NULL, 'DIRECT_INS', 9, 'Y'),
('CARE',   'RECOMMEND_MOBILE_CARE', 0, 100,  'N', 0,    'TELEMED',    7, 'Y');


-- 전체 추천 규칙 수 확인 
SELECT COUNT(*) AS recommend_rule_count
FROM recommend_rule;

-- 등급별 규칙 수 확인 
SELECT
    target_grade,
    COUNT(*) AS rule_count
FROM recommend_rule
GROUP BY target_grade
ORDER BY target_grade;

-- category_master와 코드일치 검증 
SELECT DISTINCT r.category_code
FROM recommend_rule r
LEFT JOIN category_master c
       ON r.category_code = c.category_code
WHERE c.category_code IS NULL;


-- 추천 규칙 기반 상품 매칭 테스트 
SELECT
    r.rule_id,
    r.target_grade,
    r.action_code,
    r.category_code,
    r.min_score,
    r.max_score,
    p.product_code,
    p.product_name,
    p.target_grade AS product_grade,
    p.min_score AS product_min_score,
    p.risk_level,
    p.priority_rank
FROM recommend_rule r
JOIN category_master c
  ON r.category_code = c.category_code
JOIN product_master p
  ON p.category_id = c.category_id
 AND p.active_flag = 'Y'
WHERE r.active_flag = 'Y'
  AND r.target_grade = 'GOLD'
  AND 85 BETWEEN r.min_score AND r.max_score
ORDER BY
    r.priority_rank,
    p.priority_rank
LIMIT 30;
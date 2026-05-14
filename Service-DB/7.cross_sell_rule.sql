-- ===============================================================
-- STEP 7. cross_sell_rule 생성
-- 금융 + 헬스 + 보험 교차판매 규칙
-- ===============================================================

USE lifesync360;

INSERT INTO cross_sell_rule
(
    base_category,
    target_category,
    priority_rank,
    active_flag
)
VALUES
-- ===============================================================
-- HEALTHCARE → INSURANCE / DIRECT_INS
-- ===============================================================
('HEALTHCARE', 'INSURANCE',  1, 'Y'),
('HEALTHCARE', 'DIRECT_INS', 2, 'Y'),
('HEALTHCARE', 'WELLNESS',   3, 'Y'),

-- ===============================================================
-- WELLNESS → INSURANCE / HEALTHCARE
-- ===============================================================
('WELLNESS', 'INSURANCE',   1, 'Y'),
('WELLNESS', 'DIRECT_INS',  2, 'Y'),
('WELLNESS', 'HEALTHCARE',  3, 'Y'),

-- ===============================================================
-- TELEMED → DIRECT_INS / HEALTHCARE
-- ===============================================================
('TELEMED', 'DIRECT_INS',   1, 'Y'),
('TELEMED', 'INSURANCE',    2, 'Y'),
('TELEMED', 'HEALTHCARE',   3, 'Y'),

-- ===============================================================
-- INSURANCE → HEALTHCARE / WELLNESS
-- ===============================================================
('INSURANCE', 'HEALTHCARE', 1, 'Y'),
('INSURANCE', 'WELLNESS',   2, 'Y'),
('INSURANCE', 'DIRECT_INS', 3, 'Y'),

-- ===============================================================
-- DIRECT_INS → HEALTHCARE / WELLNESS
-- ===============================================================
('DIRECT_INS', 'HEALTHCARE', 1, 'Y'),
('DIRECT_INS', 'WELLNESS',   2, 'Y'),
('DIRECT_INS', 'INSURANCE',  3, 'Y'),

-- ===============================================================
-- BANK → CARD / SEC / INS
-- ===============================================================
('DEPOSIT', 'CARD',       1, 'Y'),
('DEPOSIT', 'FUND',       2, 'Y'),
('DEPOSIT', 'ETF',        3, 'Y'),
('DEPOSIT', 'PENSION',    4, 'Y'),

('SAVING', 'CARD',        1, 'Y'),
('SAVING', 'POINT',       2, 'Y'),
('SAVING', 'FUND',        3, 'Y'),
('SAVING', 'PENSION',     4, 'Y'),

('LOAN', 'INSURANCE',     1, 'Y'),
('LOAN', 'CARD',          2, 'Y'),
('LOAN', 'DIRECT_INS',    3, 'Y'),

('PENSION', 'INSURANCE',  1, 'Y'),
('PENSION', 'HEALTHCARE', 2, 'Y'),
('PENSION', 'WM',         3, 'Y'),

-- ===============================================================
-- CARD → INSURANCE / HEALTH / POINT
-- ===============================================================
('CARD', 'DIRECT_INS',    1, 'Y'),
('CARD', 'INSURANCE',     2, 'Y'),
('CARD', 'LIFESTYLE',     3, 'Y'),
('CARD', 'POINT',         4, 'Y'),

('POINT', 'CARD',         1, 'Y'),
('POINT', 'LIFESTYLE',    2, 'Y'),
('POINT', 'WELLNESS',     3, 'Y'),

('LIFESTYLE', 'CARD',       1, 'Y'),
('LIFESTYLE', 'DIRECT_INS', 2, 'Y'),
('LIFESTYLE', 'WELLNESS',   3, 'Y'),

-- ===============================================================
-- SEC → BANK / INS / HEALTH
-- ===============================================================
('ETF', 'PENSION',       1, 'Y'),
('ETF', 'WM',            2, 'Y'),
('ETF', 'INSURANCE',     3, 'Y'),
('ETF', 'DEPOSIT',       4, 'Y'),

('FUND', 'PENSION',      1, 'Y'),
('FUND', 'WM',           2, 'Y'),
('FUND', 'INSURANCE',    3, 'Y'),

('WM', 'INSURANCE',      1, 'Y'),
('WM', 'HEALTHCARE',     2, 'Y'),
('WM', 'PENSION',        3, 'Y');


-- 전체 교차판매 규칙 수 확인

SELECT COUNT(*) AS cross_sell_rule_count
FROM cross_sell_rule;

-- 기준 카테고리별 규칙 수 확인

SELECT
    base_category,
    COUNT(*) AS target_count
FROM cross_sell_rule
GROUP BY base_category
ORDER BY base_category;

-- 금융 -> 보험 교차판매 테스트
SELECT
    r.base_category,
    r.target_category,
    p.product_name,
    p.target_grade,
    p.min_score,
    p.risk_level
FROM cross_sell_rule r
JOIN category_master c
  ON r.target_category = c.category_code
JOIN product_master p
  ON p.category_id = c.category_id
WHERE r.base_category = 'LOAN'
  AND r.active_flag = 'Y'
  AND p.active_flag = 'Y'
ORDER BY r.priority_rank, p.priority_rank
LIMIT 30;


-- 헬스 -> 보험 교차판매 테스트
SELECT
    r.base_category,
    r.target_category,
    p.product_name,
    p.target_grade,
    p.risk_level,
    p.priority_rank
FROM cross_sell_rule r
JOIN category_master c
  ON r.target_category = c.category_code
JOIN product_master p
  ON p.category_id = c.category_id
WHERE r.base_category IN ('HEALTHCARE', 'WELLNESS', 'TELEMED')
  AND r.target_category IN ('INSURANCE', 'DIRECT_INS')
  AND r.active_flag = 'Y'
ORDER BY r.base_category, r.priority_rank, p.priority_rank
LIMIT 50;



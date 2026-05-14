USE lifesync360;

INSERT INTO product_variant
(
    variant_code,
    variant_name,
    variant_desc,
    score_bonus,
    priority_bonus
)
VALUES
('STANDARD', 'Standard', '기본형 상품', 0, 0),
('PREMIUM', 'Premium', '프리미엄 고객 대상', 5, -1),
('VIP', 'VIP 전용', 'VIP 고객 전용 상품', 10, -3),
('AI', 'AI 추천형', 'AI 추천 우선 상품', 3, -2),
('YOUTH', '청년 특화형', '청년/신규 고객 대상', 0, 1),
('SENIOR', '시니어 특화형', '시니어 고객 대상', 0, 1),
('FAMILY', '가족 결합형', '가족 단위 고객 대상', 0, 1),
('WELLNESS', '웰니스 연계형', '건강관리 연계 상품', 2, -1),
('ESG', 'ESG 특화형', 'ESG/친환경 투자 성향 대상', 2, 0),
('2026', '2026 Edition', '2026년 캠페인 상품', 1, 0);


INSERT INTO product_master
(
    company_id,
    category_id,
    product_code,
    product_name,
    description,
    target_grade,
    min_score,
    max_score,
    risk_level,
    priority_rank,
    active_flag,
    start_date,
    end_date
)
SELECT
    c.company_id,
    cat.category_id,

    CONCAT(
        b.company_code,
        '-',
        b.category_code,
        '-',
        LPAD(b.base_product_id, 5, '0'),
        '-',
        LPAD(v.variant_id, 2, '0')
    ) AS product_code,

    CASE
        WHEN v.variant_code = 'STANDARD'
        THEN b.base_product_name
        ELSE CONCAT(b.base_product_name, ' ', v.variant_name)
    END AS product_name,

    CONCAT(
        'LifeSync360 AI 추천 플랫폼 상품 - ',
        b.base_product_name,
        ' / ',
        v.variant_desc,
        ' / 테마: ',
        b.product_theme
    ) AS description,

    CASE
        WHEN v.variant_code = 'VIP' THEN 'VIP'
        WHEN v.variant_code = 'PREMIUM'
             AND b.base_grade IN ('GOLD', 'SILVER') THEN 'GOLD'
        WHEN v.variant_code = 'YOUTH' THEN 'BASIC'
        WHEN v.variant_code = 'SENIOR' THEN 'SILVER'
        WHEN v.variant_code = 'WELLNESS'
             AND b.company_code IN ('HLT', 'INS', 'ONINS') THEN 'CARE'
        ELSE b.base_grade
    END AS target_grade,

    CASE
        WHEN v.variant_code = 'VIP' THEN 90
        ELSE LEAST(100, b.base_min_score + v.score_bonus)
    END AS min_score,

    b.base_max_score AS max_score,

    CASE
        WHEN b.company_code = 'SEC'
             AND v.variant_code IN ('AI', 'ESG') THEN 'HIGH'
        WHEN b.company_code IN ('BANK', 'HLT')
             AND b.base_risk_level = 'LOW' THEN 'LOW'
        ELSE b.base_risk_level
    END AS risk_level,

    GREATEST(
        1,
        LEAST(
            20,
            10 + v.priority_bonus + MOD(b.base_product_id, 10)
        )
    ) AS priority_rank,

    'Y' AS active_flag,

    CURDATE() AS start_date,

    DATE_ADD(CURDATE(), INTERVAL 365 DAY) AS end_date

FROM base_product_pool b

JOIN company_master c
  ON b.company_code = c.company_code

JOIN category_master cat
  ON b.category_code = cat.category_code

CROSS JOIN product_variant v

WHERE b.active_flag = 'Y'
  AND v.active_flag = 'Y';


SELECT COUNT(*) AS product_count
FROM product_master;


-- 계열사별 상품 수 확인 

SELECT
    c.company_code,
    c.company_name,
    COUNT(*) AS product_count
FROM product_master p
JOIN company_master c
  ON p.company_id = c.company_id
GROUP BY
    c.company_code,
    c.company_name
ORDER BY c.company_code;


-- 카테고리별 상품 수 확인 

SELECT
    cat.category_code,
    cat.category_name,
    COUNT(*) AS product_count
FROM product_master p
JOIN category_master cat
  ON p.category_id = cat.category_id
GROUP BY
    cat.category_code,
    cat.category_name
ORDER BY cat.category_code;
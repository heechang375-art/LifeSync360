-- ===============================================================
-- STEP 5-1. 상품 옵션 표준 코드 관리 테이블
-- 선택 사항
-- ===============================================================

USE lifesync360;


DROP TABLE IF EXISTS product_option_template;

CREATE TABLE product_option_template
(
    template_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    company_code      VARCHAR(30),
    category_code     VARCHAR(30),
    option_name       VARCHAR(100),
    option_desc       VARCHAR(300),
    active_flag       CHAR(1) DEFAULT 'Y',
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


INSERT INTO product_option_template
(
    company_code,
    category_code,
    option_name,
    option_desc
)
VALUES
-- BANK
('BANK','DEPOSIT','interest_rate','예금 금리'),
('BANK','DEPOSIT','min_deposit_amount','최소 가입금액'),
('BANK','DEPOSIT','term_month','가입기간'),
('BANK','DEPOSIT','preferential_condition','우대조건'),

('BANK','SAVING','interest_rate','적금 금리'),
('BANK','SAVING','monthly_limit','월 납입한도'),
('BANK','SAVING','term_month','가입기간'),
('BANK','SAVING','auto_transfer_required','자동이체 필요 여부'),

('BANK','LOAN','loan_limit','대출한도'),
('BANK','LOAN','loan_rate','대출금리'),
('BANK','LOAN','repayment_type','상환방식'),
('BANK','LOAN','credit_score_required','필요 신용점수'),

-- CARD
('CARD','CARD','annual_fee','연회비'),
('CARD','CARD','cashback_rate','캐시백률'),
('CARD','CARD','mileage_rate','마일리지 적립률'),
('CARD','CARD','main_benefit','주요 혜택'),

('CARD','POINT','point_rate','포인트 적립률'),
('CARD','POINT','point_brand','제휴 브랜드'),
('CARD','LIFESTYLE','discount_rate','할인율'),
('CARD','LIFESTYLE','benefit_category','혜택 카테고리'),

-- SEC
('SEC','ETF','expected_return','예상수익률'),
('SEC','ETF','volatility','변동성'),
('SEC','ETF','investment_region','투자지역'),
('SEC','ETF','asset_type','자산유형'),

('SEC','FUND','expected_return','예상수익률'),
('SEC','FUND','risk_grade','투자위험등급'),
('SEC','FUND','fund_type','펀드유형'),
('SEC','WM','advisor_type','자문유형'),

-- INS
('INS','INSURANCE','monthly_premium','월 보험료'),
('INS','INSURANCE','coverage_type','보장유형'),
('INS','INSURANCE','coverage_amount','보장금액'),
('INS','INSURANCE','join_age_range','가입연령'),

('INS','PENSION','monthly_premium','월 납입금'),
('INS','PENSION','pension_start_age','연금개시연령'),
('INS','PENSION','tax_benefit','세제혜택'),

-- ONLINE INS
('ONINS','DIRECT_INS','monthly_premium','월 보험료'),
('ONINS','DIRECT_INS','mobile_join','모바일 가입 가능'),
('ONINS','DIRECT_INS','simple_underwriting','간편심사 여부'),
('ONINS','DIRECT_INS','coverage_period','보장기간'),

-- HEALTHCARE
('HLT','HEALTHCARE','service_channel','서비스 채널'),
('HLT','HEALTHCARE','health_sync','건강 데이터 연동'),
('HLT','HEALTHCARE','checkup_type','검진유형'),
('HLT','HEALTHCARE','ai_report','AI 리포트 제공 여부'),

('HLT','WELLNESS','coaching_cycle','코칭 주기'),
('HLT','WELLNESS','service_channel','서비스 채널'),
('HLT','WELLNESS','wearable_sync','웨어러블 연동'),
('HLT','WELLNESS','reward_point','건강 리워드 포인트'),

('HLT','TELEMED','consulting_type','상담유형'),
('HLT','TELEMED','service_channel','서비스 채널'),
('HLT','TELEMED','reservation_required','예약 필요 여부');


-- ===============================================================
-- STEP 5-2. product_option 대량 생성
-- 상품별 3~6개 옵션 생성
-- ===============================================================

INSERT INTO product_option
(
    product_id,
    option_name,
    option_value
)
SELECT
    p.product_id,
    t.option_name,

    CASE

        -- =======================================================
        -- BANK
        -- =======================================================
        WHEN t.option_name = 'interest_rate'
            THEN CONCAT(ROUND(2.5 + (RAND(p.product_id) * 2.5), 2), '%')

        WHEN t.option_name = 'min_deposit_amount'
            THEN CONCAT(FLOOR(100000 + (RAND(p.product_id) * 900000)), ' KRW')

        WHEN t.option_name = 'term_month'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5), '6', '12', '24', '36', '60')

        WHEN t.option_name = 'preferential_condition'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '급여이체', '자동이체', '카드사용', '비대면가입', 'VIP고객')

        WHEN t.option_name = 'monthly_limit'
            THEN CONCAT(FLOOR(100000 + RAND(p.product_id) * 1900000), ' KRW')

        WHEN t.option_name = 'auto_transfer_required'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 2), 'Y', 'N')

        WHEN t.option_name = 'loan_limit'
            THEN CONCAT(FLOOR(10000000 + RAND(p.product_id) * 90000000), ' KRW')

        WHEN t.option_name = 'loan_rate'
            THEN CONCAT(ROUND(4.0 + RAND(p.product_id) * 6.0, 2), '%')

        WHEN t.option_name = 'repayment_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 3),
                     '원리금균등', '만기일시', '원금균등')

        WHEN t.option_name = 'credit_score_required'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 4),
                     '600+', '700+', '800+', '900+')

        -- =======================================================
        -- CARD
        -- =======================================================
        WHEN t.option_name = 'annual_fee'
            THEN CONCAT(FLOOR(10000 + RAND(p.product_id) * 190000), ' KRW')

        WHEN t.option_name = 'cashback_rate'
            THEN CONCAT(ROUND(0.5 + RAND(p.product_id) * 4.5, 2), '%')

        WHEN t.option_name = 'mileage_rate'
            THEN CONCAT(ROUND(0.5 + RAND(p.product_id) * 3.0, 2), ' mile/KRW')

        WHEN t.option_name = 'main_benefit'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 6),
                     '여행', '쇼핑', '주유', '배달', '병원', 'OTT')

        WHEN t.option_name = 'point_rate'
            THEN CONCAT(ROUND(0.3 + RAND(p.product_id) * 3.5, 2), '%')

        WHEN t.option_name = 'point_brand'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '온라인몰', '항공사', '대형마트', '편의점', '병원')

        WHEN t.option_name = 'discount_rate'
            THEN CONCAT(ROUND(3 + RAND(p.product_id) * 17, 2), '%')

        WHEN t.option_name = 'benefit_category'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 6),
                     '쇼핑', '교육', '의료', '반려동물', '골프', '모빌리티')

        -- =======================================================
        -- SEC
        -- =======================================================
        WHEN t.option_name = 'expected_return'
            THEN CONCAT(ROUND(3 + RAND(p.product_id) * 12, 2), '%')

        WHEN t.option_name = 'volatility'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 3), 'LOW', 'MID', 'HIGH')

        WHEN t.option_name = 'investment_region'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 6),
                     'KOREA', 'US', 'GLOBAL', 'CHINA', 'INDIA', 'EMERGING')

        WHEN t.option_name = 'asset_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     'EQUITY', 'BOND', 'MIXED', 'REITs', 'COMMODITY')

        WHEN t.option_name = 'risk_grade'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '1_LOW', '2_MID_LOW', '3_MID', '4_MID_HIGH', '5_HIGH')

        WHEN t.option_name = 'fund_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '성장형', '배당형', '채권형', '혼합형', 'ESG형')

        WHEN t.option_name = 'advisor_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 4),
                     'PB', 'RoboAdvisor', 'AI Advisor', 'Hybrid')

        -- =======================================================
        -- INS / ONLINE INS
        -- =======================================================
        WHEN t.option_name = 'monthly_premium'
            THEN CONCAT(FLOOR(10000 + RAND(p.product_id) * 290000), ' KRW')

        WHEN t.option_name = 'coverage_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 6),
                     '암', '실손', '건강', '운전자', '치아', '간병')

        WHEN t.option_name = 'coverage_amount'
            THEN CONCAT(FLOOR(10000000 + RAND(p.product_id) * 190000000), ' KRW')

        WHEN t.option_name = 'join_age_range'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '20-40', '30-50', '40-60', '50-70', 'ALL')

        WHEN t.option_name = 'pension_start_age'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 4), '55', '60', '65', '70')

        WHEN t.option_name = 'tax_benefit'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 2), 'Y', 'N')

        WHEN t.option_name = 'mobile_join'
            THEN 'Y'

        WHEN t.option_name = 'simple_underwriting'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 2), 'Y', 'N')

        WHEN t.option_name = 'coverage_period'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '1일', '7일', '30일', '1년', '10년')

        -- =======================================================
        -- HEALTHCARE
        -- =======================================================
        WHEN t.option_name = 'service_channel'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 4),
                     'APP', 'WEB', 'CENTER', 'HYBRID')

        WHEN t.option_name = 'health_sync'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 3),
                     'wearable', 'hospital', 'manual')

        WHEN t.option_name = 'checkup_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 5),
                     '기본검진', '종합검진', '암검진', '유전자검사', '프리미엄검진')

        WHEN t.option_name = 'ai_report'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 2), 'Y', 'N')

        WHEN t.option_name = 'coaching_cycle'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 4),
                     'DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY')

        WHEN t.option_name = 'wearable_sync'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 2), 'Y', 'N')

        WHEN t.option_name = 'reward_point'
            THEN CONCAT(FLOOR(100 + RAND(p.product_id) * 9900), ' POINT')

        WHEN t.option_name = 'consulting_type'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 4),
                     '의사상담', '영양상담', '운동상담', '심리상담')

        WHEN t.option_name = 'reservation_required'
            THEN ELT(FLOOR(1 + RAND(p.product_id) * 2), 'Y', 'N')

        ELSE 'N/A'
    END AS option_value

FROM product_master p

JOIN company_master c
  ON p.company_id = c.company_id

JOIN category_master cat
  ON p.category_id = cat.category_id

JOIN product_option_template t
  ON c.company_code = t.company_code
 AND cat.category_code = t.category_code

WHERE p.active_flag = 'Y'
  AND t.active_flag = 'Y';


-- 전체 옵션 건수 확인 
SELECT COUNT(*) AS option_count
FROM product_option;

-- 상품별 옵션 개수 확인 
SELECT
    p.product_id,
    p.product_name,
    COUNT(o.option_id) AS option_count
FROM product_master p
LEFT JOIN product_option o
       ON p.product_id = o.product_id
GROUP BY
    p.product_id,
    p.product_name
ORDER BY option_count DESC
LIMIT 20;

-- 옵션이 없는 상품 확인 
SELECT
    p.product_id,
    p.product_code,
    p.product_name
FROM product_master p
LEFT JOIN product_option o
       ON p.product_id = o.product_id
WHERE o.option_id IS NULL;


-- 계열사별 옵션 건수 확인
SELECT
    c.company_code,
    c.company_name,
    COUNT(o.option_id) AS option_count
FROM product_option o
JOIN product_master p
  ON o.product_id = p.product_id
JOIN company_master c
  ON p.company_id = c.company_id
GROUP BY
    c.company_code,
    c.company_name
ORDER BY c.company_code;



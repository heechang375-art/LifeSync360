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
('HLT','TELEMED','reservation_required','예약 필요 여부'),

-- BANK PENSION (IRP)
('BANK','PENSION','monthly_premium','월 납입금'),
('BANK','PENSION','pension_start_age','연금개시연령'),
('BANK','PENSION','tax_benefit','세제혜택'),

-- SEC PENSION (연금저축 펀드) - 기존 SEC/PENSION은 누락되어 있어 추가
('SEC','PENSION','monthly_premium','월 납입금'),
('SEC','PENSION','pension_start_age','연금개시연령'),
('SEC','PENSION','tax_benefit','세제혜택'),

-- HLT POINT (건강 포인트 리워드)
('HLT','POINT','reward_point','건강 리워드 포인트'),
('HLT','POINT','point_brand','제휴 브랜드'),
('HLT','POINT','point_rate','포인트 적립률');


-- ===============================================================
-- STEP 5-2. product_option 대량 생성
-- 등급(target_grade) 기반 결정 로직으로 옵션 값 차등 적용
--
-- 등급별 원칙:
--   VIP    : 최고 한도/최고 혜택 (예적금 금리 최고, 대출 금리 최저, 연회비 높음, 보장 최고)
--   GOLD   : 우대 조건
--   SILVER : 표준
--   BASIC  : 기본/저렴
--   CARE   : 비금융 케어 서비스(헬스/펫) - 등급 외 케어 전용
--
-- 같은 등급/카테고리 내에서 약간의 분산을 주기 위해 product_id 기반 MOD 사용
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
        -- BANK : 예금/적금 금리 (등급 높을수록 우대금리)
        -- =======================================================
        WHEN t.option_name = 'interest_rate' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(ROUND(5.0 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'GOLD'   THEN CONCAT(ROUND(4.2 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'SILVER' THEN CONCAT(ROUND(3.5 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'BASIC'  THEN CONCAT(ROUND(2.8 + MOD(p.product_id, 10) * 0.05, 2), '%')
                ELSE CONCAT(ROUND(3.0 + MOD(p.product_id, 10) * 0.05, 2), '%')
            END

        -- BANK : 최소 가입금액 (등급 높을수록 진입장벽 높음 = 큰 금액)
        WHEN t.option_name = 'min_deposit_amount' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '100,000,000 KRW'
                WHEN 'GOLD'   THEN '10,000,000 KRW'
                WHEN 'SILVER' THEN '1,000,000 KRW'
                WHEN 'BASIC'  THEN '100,000 KRW'
                ELSE '500,000 KRW'
            END

        -- BANK : 가입기간 (등급 높을수록 장기 선호)
        WHEN t.option_name = 'term_month' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN ELT(1 + MOD(p.product_id, 2), '36', '60')
                WHEN 'GOLD'   THEN ELT(1 + MOD(p.product_id, 2), '24', '36')
                WHEN 'SILVER' THEN ELT(1 + MOD(p.product_id, 2), '12', '24')
                WHEN 'BASIC'  THEN ELT(1 + MOD(p.product_id, 2), '6', '12')
                ELSE '12'
            END

        -- BANK : 우대조건
        WHEN t.option_name = 'preferential_condition' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'PB 전담매니저 / 거액예치 / 자산관리 통합실적'
                WHEN 'GOLD'   THEN '급여이체 + 카드사용 100만원 이상'
                WHEN 'SILVER' THEN '자동이체 3건 이상 / 급여이체'
                WHEN 'BASIC'  THEN '비대면 가입'
                ELSE '거래실적 충족'
            END

        -- BANK : 월 납입한도
        WHEN t.option_name = 'monthly_limit' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '5,000,000 KRW'
                WHEN 'GOLD'   THEN '2,000,000 KRW'
                WHEN 'SILVER' THEN '1,000,000 KRW'
                WHEN 'BASIC'  THEN '500,000 KRW'
                ELSE '500,000 KRW'
            END

        -- BANK : 자동이체 필요 여부 (BASIC/SILVER는 필수, VIP는 선택)
        WHEN t.option_name = 'auto_transfer_required' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'N'
                WHEN 'GOLD'   THEN 'N'
                ELSE 'Y'
            END

        -- BANK : 대출한도 (등급 높을수록 한도 큼)
        WHEN t.option_name = 'loan_limit' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '500,000,000 KRW'
                WHEN 'GOLD'   THEN '100,000,000 KRW'
                WHEN 'SILVER' THEN '50,000,000 KRW'
                WHEN 'BASIC'  THEN '20,000,000 KRW'
                ELSE '30,000,000 KRW'
            END

        -- BANK : 대출금리 (등급 높을수록 우대금리, 즉 낮음)
        WHEN t.option_name = 'loan_rate' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(ROUND(3.5 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'GOLD'   THEN CONCAT(ROUND(4.5 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'SILVER' THEN CONCAT(ROUND(6.0 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'BASIC'  THEN CONCAT(ROUND(8.0 + MOD(p.product_id, 10) * 0.05, 2), '%')
                ELSE CONCAT(ROUND(7.0 + MOD(p.product_id, 10) * 0.05, 2), '%')
            END

        -- BANK : 상환방식
        WHEN t.option_name = 'repayment_type' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '만기일시'
                WHEN 'GOLD'   THEN '원금균등'
                ELSE '원리금균등'
            END

        -- BANK : 필요 신용점수 (등급 높을수록 더 높은 신용 필요)
        WHEN t.option_name = 'credit_score_required' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '900+'
                WHEN 'GOLD'   THEN '800+'
                WHEN 'SILVER' THEN '700+'
                WHEN 'BASIC'  THEN '600+'
                ELSE '700+'
            END

        -- =======================================================
        -- CARD : 연회비 (등급 높을수록 비쌈)
        -- =======================================================
        WHEN t.option_name = 'annual_fee' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(FLOOR(500000 + MOD(p.product_id, 10) * 100000), ' KRW')
                WHEN 'GOLD'   THEN CONCAT(FLOOR(100000 + MOD(p.product_id, 10) * 20000), ' KRW')
                WHEN 'SILVER' THEN CONCAT(FLOOR(30000 + MOD(p.product_id, 10) * 5000), ' KRW')
                WHEN 'BASIC'  THEN CONCAT(FLOOR(10000 + MOD(p.product_id, 10) * 2000), ' KRW')
                ELSE '20,000 KRW'
            END

        -- CARD : 캐시백률 (등급 높을수록 적립률 높음)
        WHEN t.option_name = 'cashback_rate' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(ROUND(3.0 + MOD(p.product_id, 10) * 0.1, 2), '%')
                WHEN 'GOLD'   THEN CONCAT(ROUND(2.0 + MOD(p.product_id, 10) * 0.1, 2), '%')
                WHEN 'SILVER' THEN CONCAT(ROUND(1.2 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'BASIC'  THEN CONCAT(ROUND(0.5 + MOD(p.product_id, 10) * 0.05, 2), '%')
                ELSE CONCAT(ROUND(1.0, 2), '%')
            END

        -- CARD : 마일리지 적립률
        WHEN t.option_name = 'mileage_rate' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '1000원당 3 mile'
                WHEN 'GOLD'   THEN '1000원당 2 mile'
                WHEN 'SILVER' THEN '1500원당 1 mile'
                WHEN 'BASIC'  THEN '2000원당 1 mile'
                ELSE '1500원당 1 mile'
            END

        -- CARD : 주요 혜택
        WHEN t.option_name = 'main_benefit' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN ELT(1 + MOD(p.product_id, 4), 'PP라운지/특급호텔/컨시어지', '항공권/호텔 무료숙박', '골프장 라운드', 'VIP 컨시어지')
                WHEN 'GOLD'   THEN ELT(1 + MOD(p.product_id, 4), '여행/마일리지', '항공 라운지', '호텔 우대', '면세점 할인')
                WHEN 'SILVER' THEN ELT(1 + MOD(p.product_id, 4), '쇼핑/외식', '주유/대중교통', '온라인쇼핑', '교육비')
                WHEN 'BASIC'  THEN ELT(1 + MOD(p.product_id, 4), '편의점/카페', '배달/OTT', '마트 할인', '영화/문화')
                ELSE '쇼핑/외식'
            END

        -- CARD : 포인트 적립률
        WHEN t.option_name = 'point_rate' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(ROUND(3.0 + MOD(p.product_id, 10) * 0.1, 2), '%')
                WHEN 'GOLD'   THEN CONCAT(ROUND(2.0 + MOD(p.product_id, 10) * 0.1, 2), '%')
                WHEN 'SILVER' THEN CONCAT(ROUND(1.2 + MOD(p.product_id, 10) * 0.05, 2), '%')
                WHEN 'BASIC'  THEN CONCAT(ROUND(0.5 + MOD(p.product_id, 10) * 0.05, 2), '%')
                ELSE CONCAT(ROUND(1.0, 2), '%')
            END

        -- CARD : 제휴 브랜드
        WHEN t.option_name = 'point_brand' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '대한항공/특급호텔/프리미엄 백화점'
                WHEN 'GOLD'   THEN '항공사/호텔/면세점'
                WHEN 'SILVER' THEN '온라인몰/주유소/대형마트'
                WHEN 'BASIC'  THEN '편의점/카페/배달앱'
                ELSE '온라인몰'
            END

        -- CARD : 할인율
        WHEN t.option_name = 'discount_rate' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(ROUND(15.0 + MOD(p.product_id, 10) * 0.5, 2), '%')
                WHEN 'GOLD'   THEN CONCAT(ROUND(10.0 + MOD(p.product_id, 10) * 0.5, 2), '%')
                WHEN 'SILVER' THEN CONCAT(ROUND(7.0 + MOD(p.product_id, 10) * 0.3, 2), '%')
                WHEN 'BASIC'  THEN CONCAT(ROUND(5.0 + MOD(p.product_id, 10) * 0.2, 2), '%')
                ELSE CONCAT(ROUND(7.0, 2), '%')
            END

        -- CARD : 혜택 카테고리
        WHEN t.option_name = 'benefit_category' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '골프/럭셔리/프리미엄'
                WHEN 'GOLD'   THEN '여행/쇼핑/모빌리티'
                WHEN 'SILVER' THEN '쇼핑/교육/주유'
                WHEN 'BASIC'  THEN '배달/OTT/편의점'
                WHEN 'CARE'   THEN '의료/반려동물/건강'
                ELSE '쇼핑'
            END

        -- =======================================================
        -- SEC : 예상수익률 (등급 높을수록 적극적 운용)
        -- =======================================================
        WHEN t.option_name = 'expected_return' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(ROUND(12.0 + MOD(p.product_id, 10) * 0.5, 2), '%')
                WHEN 'GOLD'   THEN CONCAT(ROUND(9.0 + MOD(p.product_id, 10) * 0.4, 2), '%')
                WHEN 'SILVER' THEN CONCAT(ROUND(6.0 + MOD(p.product_id, 10) * 0.3, 2), '%')
                WHEN 'BASIC'  THEN CONCAT(ROUND(4.0 + MOD(p.product_id, 10) * 0.2, 2), '%')
                ELSE CONCAT(ROUND(6.0, 2), '%')
            END

        -- SEC : 변동성
        WHEN t.option_name = 'volatility' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'HIGH'
                WHEN 'GOLD'   THEN 'HIGH'
                WHEN 'SILVER' THEN 'MID'
                WHEN 'BASIC'  THEN 'LOW'
                ELSE 'MID'
            END

        -- SEC : 투자지역
        WHEN t.option_name = 'investment_region' THEN
            ELT(1 + MOD(p.product_id, 6), 'KOREA', 'US', 'GLOBAL', 'CHINA', 'INDIA', 'EMERGING')

        -- SEC : 자산유형
        WHEN t.option_name = 'asset_type' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN ELT(1 + MOD(p.product_id, 3), 'EQUITY', 'MIXED', 'COMMODITY')
                WHEN 'GOLD'   THEN ELT(1 + MOD(p.product_id, 3), 'EQUITY', 'MIXED', 'REITs')
                WHEN 'SILVER' THEN ELT(1 + MOD(p.product_id, 3), 'MIXED', 'BOND', 'REITs')
                WHEN 'BASIC'  THEN 'BOND'
                ELSE 'MIXED'
            END

        -- SEC : 투자위험등급 (1=낮음, 5=높음)
        WHEN t.option_name = 'risk_grade' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '5_HIGH'
                WHEN 'GOLD'   THEN '4_MID_HIGH'
                WHEN 'SILVER' THEN '3_MID'
                WHEN 'BASIC'  THEN '2_MID_LOW'
                ELSE '3_MID'
            END

        -- SEC : 펀드유형
        WHEN t.option_name = 'fund_type' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '성장형'
                WHEN 'GOLD'   THEN ELT(1 + MOD(p.product_id, 2), '성장형', 'ESG형')
                WHEN 'SILVER' THEN ELT(1 + MOD(p.product_id, 3), '배당형', '혼합형', 'ESG형')
                WHEN 'BASIC'  THEN '채권형'
                ELSE '혼합형'
            END

        -- SEC : 자문유형
        WHEN t.option_name = 'advisor_type' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'PB'
                WHEN 'GOLD'   THEN ELT(1 + MOD(p.product_id, 2), 'Hybrid', 'AI Advisor')
                WHEN 'SILVER' THEN 'RoboAdvisor'
                WHEN 'BASIC'  THEN 'RoboAdvisor'
                ELSE 'AI Advisor'
            END

        -- =======================================================
        -- INS / ONLINE INS : 월 보험료 (등급 높을수록 비쌈, 보장 큼)
        -- =======================================================
        WHEN t.option_name = 'monthly_premium' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(FLOOR(500000 + MOD(p.product_id, 10) * 50000), ' KRW')
                WHEN 'GOLD'   THEN CONCAT(FLOOR(150000 + MOD(p.product_id, 10) * 20000), ' KRW')
                WHEN 'SILVER' THEN CONCAT(FLOOR(50000 + MOD(p.product_id, 10) * 10000), ' KRW')
                WHEN 'BASIC'  THEN CONCAT(FLOOR(10000 + MOD(p.product_id, 10) * 3000), ' KRW')
                WHEN 'CARE'   THEN CONCAT(FLOOR(20000 + MOD(p.product_id, 10) * 5000), ' KRW')
                ELSE CONCAT(FLOOR(30000 + MOD(p.product_id, 10) * 5000), ' KRW')
            END

        -- INS : 보장유형
        WHEN t.option_name = 'coverage_type' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '종신/상속/3대질환'
                WHEN 'GOLD'   THEN '건강/암/뇌혈관'
                WHEN 'SILVER' THEN '암/실손/가족보장'
                WHEN 'BASIC'  THEN ELT(1 + MOD(p.product_id, 4), '실손', '운전자', '치아', '재해')
                WHEN 'CARE'   THEN '펫의료/펫상해'
                ELSE '건강'
            END

        -- INS : 보장금액 (등급 높을수록 큼)
        WHEN t.option_name = 'coverage_amount' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '1,000,000,000 KRW'
                WHEN 'GOLD'   THEN '300,000,000 KRW'
                WHEN 'SILVER' THEN '100,000,000 KRW'
                WHEN 'BASIC'  THEN '50,000,000 KRW'
                WHEN 'CARE'   THEN '20,000,000 KRW'
                ELSE '50,000,000 KRW'
            END

        -- INS : 가입연령
        WHEN t.option_name = 'join_age_range' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '40-70'
                WHEN 'GOLD'   THEN '30-65'
                WHEN 'SILVER' THEN '20-60'
                WHEN 'BASIC'  THEN '0-80'
                ELSE '20-60'
            END

        -- INS : 연금개시연령
        WHEN t.option_name = 'pension_start_age' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '55'
                WHEN 'GOLD'   THEN '60'
                WHEN 'SILVER' THEN '65'
                WHEN 'BASIC'  THEN '65'
                ELSE '60'
            END

        -- INS : 세제혜택
        WHEN t.option_name = 'tax_benefit' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'Y'
                WHEN 'GOLD'   THEN 'Y'
                WHEN 'SILVER' THEN 'Y'
                ELSE 'N'
            END

        -- ONLINE INS : 모바일 가입
        WHEN t.option_name = 'mobile_join' THEN 'Y'

        -- ONLINE INS : 간편심사
        WHEN t.option_name = 'simple_underwriting' THEN
            CASE p.target_grade
                WHEN 'BASIC'  THEN 'Y'
                WHEN 'CARE'   THEN 'Y'
                ELSE 'N'
            END

        -- ONLINE INS : 보장기간
        WHEN t.option_name = 'coverage_period' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '종신'
                WHEN 'GOLD'   THEN '20년'
                WHEN 'SILVER' THEN '10년'
                WHEN 'BASIC'  THEN ELT(1 + MOD(p.product_id, 4), '1일', '7일', '30일', '1년')
                WHEN 'CARE'   THEN '1년'
                ELSE '10년'
            END

        -- =======================================================
        -- HEALTHCARE : 서비스 채널 (등급 높을수록 풀서비스)
        -- =======================================================
        WHEN t.option_name = 'service_channel' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'CENTER'
                WHEN 'GOLD'   THEN 'HYBRID'
                WHEN 'SILVER' THEN 'HYBRID'
                WHEN 'BASIC'  THEN 'APP'
                WHEN 'CARE'   THEN 'APP'
                ELSE 'APP'
            END

        -- HEALTHCARE : 건강데이터 연동
        WHEN t.option_name = 'health_sync' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'hospital'
                WHEN 'GOLD'   THEN 'hospital'
                ELSE 'wearable'
            END

        -- HEALTHCARE : 검진유형 (등급 높을수록 정밀검진)
        WHEN t.option_name = 'checkup_type' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN '프리미엄검진'
                WHEN 'GOLD'   THEN '종합검진'
                WHEN 'SILVER' THEN '암검진'
                WHEN 'BASIC'  THEN '기본검진'
                ELSE '유전자검사'
            END

        -- HEALTHCARE : AI 리포트
        WHEN t.option_name = 'ai_report' THEN
            CASE p.target_grade
                WHEN 'BASIC'  THEN 'N'
                ELSE 'Y'
            END

        -- WELLNESS : 코칭 주기 (등급 높을수록 자주)
        WHEN t.option_name = 'coaching_cycle' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'DAILY'
                WHEN 'GOLD'   THEN 'WEEKLY'
                WHEN 'SILVER' THEN 'WEEKLY'
                WHEN 'BASIC'  THEN 'MONTHLY'
                WHEN 'CARE'   THEN 'WEEKLY'
                ELSE 'WEEKLY'
            END

        -- WELLNESS : 웨어러블 연동
        WHEN t.option_name = 'wearable_sync' THEN 'Y'

        -- WELLNESS : 건강 리워드 포인트
        WHEN t.option_name = 'reward_point' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN CONCAT(FLOOR(10000 + MOD(p.product_id, 10) * 1000), ' POINT')
                WHEN 'GOLD'   THEN CONCAT(FLOOR(5000 + MOD(p.product_id, 10) * 500), ' POINT')
                WHEN 'SILVER' THEN CONCAT(FLOOR(2000 + MOD(p.product_id, 10) * 300), ' POINT')
                WHEN 'BASIC'  THEN CONCAT(FLOOR(500 + MOD(p.product_id, 10) * 100), ' POINT')
                WHEN 'CARE'   THEN CONCAT(FLOOR(3000 + MOD(p.product_id, 10) * 300), ' POINT')
                ELSE '1000 POINT'
            END

        -- TELEMED : 상담유형
        WHEN t.option_name = 'consulting_type' THEN
            ELT(1 + MOD(p.product_id, 4), '의사상담', '영양상담', '운동상담', '심리상담')

        -- TELEMED : 예약 필요 여부
        WHEN t.option_name = 'reservation_required' THEN
            CASE p.target_grade
                WHEN 'VIP'    THEN 'N'
                ELSE 'Y'
            END

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


-- 등급별 카드 연회비 차등 확인 (예시 검증)
SELECT
    p.target_grade,
    o.option_value AS annual_fee,
    COUNT(*) AS cnt
FROM product_option o
JOIN product_master p
  ON o.product_id = p.product_id
WHERE o.option_name = 'annual_fee'
GROUP BY p.target_grade, o.option_value
ORDER BY p.target_grade, o.option_value;

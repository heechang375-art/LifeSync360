-- ===============================================================
-- STEP 8. campaign_master 등급별 캠페인 생성
-- ===============================================================

USE lifesync360;


INSERT INTO campaign_master
(
    campaign_name,
    target_grade,
    banner_title,
    banner_desc,
    start_date,
    end_date,
    active_flag
)
VALUES
-- VIP
(
    'VIP 프리미엄 자산관리 캠페인',
    'VIP',
    'VIP 고객 전용 프리미엄 자산관리',
    'PB 예금, WM, VIP 카드, 상속 보험, 프리미엄 건강검진을 통합 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),
(
    'VIP 라이프케어 통합 캠페인',
    'VIP',
    '금융과 건강을 함께 관리하는 VIP 라이프케어',
    '고액자산가 고객을 위한 금융, 보험, 헬스케어 통합 추천 캠페인입니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),

-- GOLD
(
    'GOLD 투자성향 맞춤 캠페인',
    'GOLD',
    '성장형 고객을 위한 ETF·펀드 추천',
    'ETF, 글로벌 투자, 프리미엄 보험, 여행카드 중심의 맞춤 추천 캠페인입니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),
(
    'GOLD 프리미엄 혜택 캠페인',
    'GOLD',
    '우량 고객을 위한 금융 혜택 패키지',
    '투자상품, 프리미엄 카드, 건강보험을 함께 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),

-- SILVER
(
    'SILVER 생활금융 캠페인',
    'SILVER',
    '생활 속 혜택을 높이는 맞춤 금융 추천',
    '적금, 생활혜택 카드, 배당 ETF, 건강보험을 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),
(
    'SILVER 건강보장 캠페인',
    'SILVER',
    '건강과 생활비를 함께 관리하세요',
    '생활형 금융상품과 건강보험, 웰니스 서비스를 함께 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),

-- BASIC
(
    'BASIC 금융 시작 캠페인',
    'BASIC',
    '처음 시작하는 고객을 위한 금융 패키지',
    '청년 적금, 체크카드, 간편보험, 생활형 금융상품을 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),
(
    'BASIC 생활혜택 캠페인',
    'BASIC',
    '매일 쓰는 소비에 혜택을 더하세요',
    '생활혜택 카드, 적금, 모바일 보험 중심의 추천 캠페인입니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),

-- CARE
(
    'CARE 건강관리 캠페인',
    'CARE',
    '건강 데이터를 기반으로 맞춤 케어를 시작하세요',
    'AI 건강 리포트, 운동 코칭, 식단 관리, 건강보험을 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
),
(
    'CARE 웰니스 보험 연계 캠페인',
    'CARE',
    '건강관리와 보험을 함께 추천합니다',
    '헬스케어 이용 고객에게 실손보험, 간편보험, 웰니스 서비스를 연계 추천합니다.',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 90 DAY),
    'Y'
);

-- 캠페인 Seed 테이블 생성 

DROP TABLE IF EXISTS campaign_seed;

CREATE TABLE campaign_seed
(
    seed_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    target_grade   VARCHAR(20),
    theme_name     VARCHAR(100),
    banner_keyword VARCHAR(100),
    campaign_desc  VARCHAR(300)
) ENGINE=InnoDB;


-- 캠페인 Seed 등록

INSERT INTO campaign_seed
(
    target_grade,
    theme_name,
    banner_keyword,
    campaign_desc
)
VALUES
('VIP', '프리미엄 자산관리', 'PB·WM·상속설계', 'VIP 고객을 위한 프리미엄 금융·보험·헬스케어 캠페인'),
('VIP', 'VIP 라이프케어', '자산관리+건강관리', '고액자산가 고객을 위한 통합 라이프케어 캠페인'),
('VIP', '상속/절세 설계', '상속보험·절세 포트폴리오', '상속과 절세를 고려한 고액자산가 전용 캠페인'),

('GOLD', '글로벌 투자', 'ETF·펀드·달러자산', '우량 고객을 위한 글로벌 투자 추천 캠페인'),
('GOLD', '프리미엄 카드혜택', '여행·마일리지·라운지', '소비 수준이 높은 고객을 위한 카드 혜택 캠페인'),
('GOLD', '프리미엄 건강보장', '건강보험·검진', '건강과 금융을 함께 관리하는 우량 고객 캠페인'),

('SILVER', '생활금융 혜택', '적금·카드·배당ETF', '일상 금융혜택을 높이는 캠페인'),
('SILVER', '건강보장 시작', '건강보험·웰니스', '건강관리와 보장성 상품을 함께 추천하는 캠페인'),
('SILVER', '목적자금 만들기', '적금·예금·카드', '목적자금과 소비혜택을 함께 설계하는 캠페인'),

('BASIC', '금융 시작', '청년적금·체크카드', '신규/일반 고객을 위한 시작형 금융 캠페인'),
('BASIC', '생활비 절약', '캐시백·할인·적금', '생활비 절약 중심의 금융상품 캠페인'),
('BASIC', '간편보험 시작', '모바일보험·원데이보험', '부담 없이 시작하는 간편 보험 캠페인'),

('CARE', 'AI 건강관리', 'AI 리포트·식단·운동', '건강 데이터를 기반으로 맞춤형 건강관리 캠페인'),
('CARE', '웰니스 보험연계', '건강관리+보험', '건강관리 이력을 기반으로 보험상품을 연계하는 캠페인'),
('CARE', '비대면 건강상담', '화상진료·건강상담', '비대면 건강관리 서비스 이용 캠페인');


-- Seed 기반 100 캠페인 생성

INSERT INTO campaign_master
(
    campaign_name,
    target_grade,
    banner_title,
    banner_desc,
    start_date,
    end_date,
    active_flag
)
SELECT
    CONCAT(
        s.target_grade,
        ' ',
        s.theme_name,
        ' 캠페인 ',
        LPAD(seq.num, 2, '0')
    ) AS campaign_name,

    s.target_grade,

    CONCAT(
        s.target_grade,
        ' 고객을 위한 ',
        s.banner_keyword
    ) AS banner_title,

    CONCAT(
        s.campaign_desc,
        ' - LifeSync360 AI 추천 캠페인 ',
        LPAD(seq.num, 2, '0')
    ) AS banner_desc,

    DATE_ADD(CURDATE(), INTERVAL MOD(seq.num, 30) DAY) AS start_date,
    DATE_ADD(CURDATE(), INTERVAL 90 + MOD(seq.num, 60) DAY) AS end_date,

    'Y' AS active_flag

FROM campaign_seed s
JOIN
(
    SELECT 1 AS num UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
    UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
    UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
    UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20
) seq
LIMIT 100;

-- 전체 캠페인 수 확인 

SELECT COUNT(*) AS campaign_count
FROM campaign_master;

-- 특정 등급 캠페인 조회 
SELECT
    campaign_name,
    banner_title,
    banner_desc,
    start_date,
    end_date
FROM campaign_master
WHERE target_grade = 'VIP'
  AND active_flag = 'Y'
ORDER BY campaign_id
LIMIT 10;





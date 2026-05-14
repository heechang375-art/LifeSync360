-- ===============================================================
-- STEP 3-1. 기존 120개 상품명 Base Product Pool 등록
-- ===============================================================

USE lifesync360;

INSERT INTO base_product_pool
(
    company_code,
    category_code,
    base_product_name,
    base_grade,
    base_min_score,
    base_max_score,
    base_risk_level,
    product_theme
)
VALUES
-- ===============================================================
-- BANK: 1~20
-- ===============================================================
('BANK','DEPOSIT','PB 프리미엄 정기예금','VIP',90,100,'LOW','PB/프리미엄 예금'),
('BANK','DEPOSIT','VIP 우대 예금','VIP',90,100,'LOW','VIP 예금'),
('BANK','DEPOSIT','고금리 자유예금','GOLD',80,100,'LOW','고금리 예금'),
('BANK','SAVING','스마트 적금 플랜','SILVER',70,100,'LOW','디지털 적금'),
('BANK','SAVING','청년 희망 적금','BASIC',60,100,'LOW','청년 금융'),
('BANK','DEPOSIT','직장인 급여통장','BASIC',60,100,'LOW','급여통장'),
('BANK','PENSION','은퇴연금 IRP','GOLD',80,100,'MID','은퇴/연금'),
('BANK','SAVING','주택청약 종합저축','BASIC',60,100,'LOW','주거/청약'),
('BANK','DEPOSIT','외화 예금 달러형','GOLD',80,100,'MID','외화자산'),
('BANK','SAVING','자녀 교육 적금','SILVER',70,100,'LOW','교육자금'),
('BANK','DEPOSIT','PB 자산관리 예금','VIP',90,100,'LOW','PB 자산관리'),
('BANK','DEPOSIT','VIP MMF 예치형','VIP',90,100,'MID','MMF 예치'),
('BANK','DEPOSIT','프리미엄 CMA','GOLD',80,100,'MID','CMA'),
('BANK','SAVING','자동 목돈 만들기 적금','SILVER',70,100,'LOW','목돈마련'),
('BANK','SAVING','생활비 절약 적금','BASIC',60,100,'LOW','생활비 관리'),
('BANK','SAVING','여행 목적 적금','BASIC',60,100,'LOW','목적자금'),
('BANK','DEPOSIT','커플 공동통장','BASIC',60,100,'LOW','공동자금'),
('BANK','DEPOSIT','시니어 안심 예금','SILVER',70,100,'LOW','시니어 금융'),
('BANK','DEPOSIT','소상공인 운영통장','SILVER',70,100,'LOW','사업자 금융'),
('BANK','LOAN','우대 신용대출','GOLD',80,100,'MID','신용대출'),

-- ===============================================================
-- CARD: 21~40
-- ===============================================================
('CARD','CARD','Black Signature Card','VIP',90,100,'MID','프리미엄 카드'),
('CARD','CARD','Travel Platinum Card','GOLD',80,100,'MID','여행/마일리지'),
('CARD','CARD','Daily Cashback Card','SILVER',70,100,'LOW','캐시백'),
('CARD','CARD','Starter Check Card','BASIC',60,100,'LOW','체크카드'),
('CARD','LIFESTYLE','VIP Lounge Card','VIP',90,100,'MID','공항라운지'),
('CARD','CARD','Mileage Air Card','GOLD',80,100,'MID','항공 마일리지'),
('CARD','CARD','Luxury Shopping Card','VIP',90,100,'MID','럭셔리 쇼핑'),
('CARD','LIFESTYLE','마트 할인 카드','BASIC',60,100,'LOW','마트 할인'),
('CARD','LIFESTYLE','주유 특화 카드','SILVER',70,100,'LOW','주유 할인'),
('CARD','LIFESTYLE','배달 할인 카드','BASIC',60,100,'LOW','배달 할인'),
('CARD','LIFESTYLE','온라인 쇼핑 카드','SILVER',70,100,'LOW','온라인 쇼핑'),
('CARD','LIFESTYLE','OTT 할인 카드','BASIC',60,100,'LOW','구독/OTT'),
('CARD','LIFESTYLE','골프 멤버십 카드','VIP',90,100,'MID','골프 멤버십'),
('CARD','CARD','프리미엄 가족 카드','GOLD',80,100,'MID','가족 카드'),
('CARD','CARD','청년 체크 카드','BASIC',60,100,'LOW','청년 체크'),
('CARD','LIFESTYLE','반려동물 카드','CARE',0,100,'LOW','펫 라이프'),
('CARD','LIFESTYLE','병원 할인 카드','CARE',0,100,'LOW','의료 할인'),
('CARD','LIFESTYLE','교육비 할인 카드','SILVER',70,100,'LOW','교육비 할인'),
('CARD','POINT','리워드 포인트 카드','SILVER',70,100,'LOW','포인트 리워드'),
('CARD','CARD','VIP Infinite Card','VIP',90,100,'MID','VIP 카드'),

-- ===============================================================
-- SEC: 41~60
-- ===============================================================
('SEC','ETF','Global ETF Portfolio','GOLD',80,100,'HIGH','글로벌 ETF'),
('SEC','FUND','AI 성장형 펀드','GOLD',80,100,'HIGH','AI 투자'),
('SEC','ETF','배당 ETF 패키지','SILVER',70,100,'MID','배당 ETF'),
('SEC','FUND','적립식 펀드 플랜','BASIC',60,100,'MID','적립식 투자'),
('SEC','ETF','미국 기술주 ETF','GOLD',80,100,'HIGH','미국 기술주'),
('SEC','ETF','반도체 ETF','GOLD',80,100,'HIGH','반도체 투자'),
('SEC','ETF','2차전지 ETF','GOLD',80,100,'HIGH','2차전지 투자'),
('SEC','FUND','채권 안정형 펀드','SILVER',70,100,'MID','채권 안정형'),
('SEC','PENSION','연금저축 펀드','SILVER',70,100,'MID','연금저축'),
('SEC','WM','로보어드바이저 랩','GOLD',80,100,'MID','로보어드바이저'),
('SEC','FUND','ESG 펀드','SILVER',70,100,'MID','ESG 투자'),
('SEC','ETF','글로벌 채권 ETF','SILVER',70,100,'MID','글로벌 채권'),
('SEC','ETF','중국 소비 ETF','GOLD',80,100,'HIGH','중국 시장'),
('SEC','ETF','인도 성장 ETF','GOLD',80,100,'HIGH','인도 성장'),
('SEC','ETF','원자재 ETF','GOLD',80,100,'HIGH','원자재 투자'),
('SEC','ETF','달러 자산 ETF','GOLD',80,100,'MID','달러 자산'),
('SEC','WM','배당주 랩어카운트','GOLD',80,100,'MID','배당주 랩'),
('SEC','WM','고액자산가 WM','VIP',90,100,'MID','고액자산가 관리'),
('SEC','WM','세금 절세 포트폴리오','GOLD',80,100,'MID','절세 포트폴리오'),
('SEC','WM','VIP PB 증권랩','VIP',90,100,'MID','VIP PB 랩'),

-- ===============================================================
-- INS: 61~80
-- ===============================================================
('INS','INSURANCE','VIP 종신보험','VIP',90,100,'MID','종신/상속'),
('INS','INSURANCE','프리미엄 건강보험','GOLD',80,100,'MID','건강보장'),
('INS','INSURANCE','실손 의료보험','BASIC',60,100,'LOW','실손의료'),
('INS','INSURANCE','가족 보장 보험','SILVER',70,100,'MID','가족보장'),
('INS','INSURANCE','암보험 플러스','SILVER',70,100,'MID','암보장'),
('INS','INSURANCE','치매 대비 보험','SILVER',70,100,'MID','치매보장'),
('INS','INSURANCE','운전자 보험','BASIC',60,100,'LOW','운전자 보장'),
('INS','INSURANCE','어린이 보험','BASIC',60,100,'LOW','어린이 보장'),
('INS','INSURANCE','태아 보험','BASIC',60,100,'LOW','태아 보장'),
('INS','INSURANCE','입원비 보장 보험','BASIC',60,100,'LOW','입원비 보장'),
('INS','INSURANCE','간병 보험','SILVER',70,100,'MID','간병 보장'),
('INS','INSURANCE','수술비 특약 보험','SILVER',70,100,'MID','수술비 특약'),
('INS','INSURANCE','생활질환 보험','BASIC',60,100,'LOW','생활질환'),
('INS','INSURANCE','장기요양 보험','SILVER',70,100,'MID','장기요양'),
('INS','INSURANCE','여성 특화 보험','SILVER',70,100,'LOW','여성 건강'),
('INS','INSURANCE','남성 건강 보험','SILVER',70,100,'LOW','남성 건강'),
('INS','PENSION','은퇴 생활 보험','GOLD',80,100,'MID','은퇴 생활'),
('INS','INSURANCE','재해 보장 보험','BASIC',60,100,'LOW','재해 보장'),
('INS','INSURANCE','VIP 상속 보험','VIP',90,100,'MID','상속 설계'),
('INS','INSURANCE','고액자산가 절세 보험','VIP',90,100,'MID','절세 보험'),

-- ===============================================================
-- ONLINE INS: 81~100
-- ===============================================================
('ONINS','DIRECT_INS','모바일 간편 암보험','BASIC',60,100,'LOW','모바일 암보험'),
('ONINS','DIRECT_INS','반려동물 보험','CARE',0,100,'LOW','펫보험'),
('ONINS','DIRECT_INS','여행자 보험','BASIC',60,100,'LOW','여행보험'),
('ONINS','DIRECT_INS','휴대폰 파손 보험','BASIC',60,100,'LOW','생활밀착보험'),
('ONINS','DIRECT_INS','자전거 보험','BASIC',60,100,'LOW','생활레저보험'),
('ONINS','DIRECT_INS','렌터카 보험','BASIC',60,100,'LOW','렌터카보험'),
('ONINS','DIRECT_INS','골프 보험','SILVER',70,100,'LOW','골프보험'),
('ONINS','DIRECT_INS','배달 라이더 보험','BASIC',60,100,'LOW','라이더보험'),
('ONINS','DIRECT_INS','해외 유학생 보험','BASIC',60,100,'LOW','유학생보험'),
('ONINS','DIRECT_INS','원데이 자동차 보험','BASIC',60,100,'LOW','원데이 자동차'),
('ONINS','DIRECT_INS','모바일 실손보험','BASIC',60,100,'LOW','모바일 실손'),
('ONINS','DIRECT_INS','간편 치아보험','BASIC',60,100,'LOW','치아보험'),
('ONINS','DIRECT_INS','간편 운전자보험','BASIC',60,100,'LOW','운전자보험'),
('ONINS','DIRECT_INS','간편 주택보험','BASIC',60,100,'LOW','주택보험'),
('ONINS','DIRECT_INS','간편 재해보험','BASIC',60,100,'LOW','재해보험'),
('ONINS','DIRECT_INS','출장자 보험','BASIC',60,100,'LOW','출장보험'),
('ONINS','DIRECT_INS','해외 출장 보험','BASIC',60,100,'LOW','해외출장'),
('ONINS','DIRECT_INS','액티비티 보험','BASIC',60,100,'LOW','액티비티'),
('ONINS','DIRECT_INS','캠핑 보험','BASIC',60,100,'LOW','캠핑보험'),
('ONINS','DIRECT_INS','펫 프리미엄 보험','CARE',0,100,'LOW','프리미엄 펫보험'),

-- ===============================================================
-- HEALTHCARE: 101~120
-- ===============================================================
('HLT','HEALTHCARE','VIP 종합 건강검진','VIP',90,100,'LOW','프리미엄 검진'),
('HLT','HEALTHCARE','AI 건강 리포트','CARE',0,100,'LOW','AI 건강분석'),
('HLT','WELLNESS','운동 코칭 프로그램','CARE',0,100,'LOW','운동관리'),
('HLT','WELLNESS','스트레스 관리 프로그램','CARE',0,100,'LOW','마음건강'),
('HLT','WELLNESS','식단 관리 서비스','CARE',0,100,'LOW','식단관리'),
('HLT','HEALTHCARE','당뇨 관리 프로그램','CARE',0,100,'LOW','당뇨관리'),
('HLT','HEALTHCARE','혈압 관리 프로그램','CARE',0,100,'LOW','혈압관리'),
('HLT','WELLNESS','수면 개선 프로그램','CARE',0,100,'LOW','수면관리'),
('HLT','WELLNESS','금연 코칭 서비스','CARE',0,100,'LOW','금연관리'),
('HLT','WELLNESS','체중 감량 챌린지','CARE',0,100,'LOW','체중관리'),
('HLT','HEALTHCARE','프리미엄 검진 예약','GOLD',80,100,'LOW','검진예약'),
('HLT','HEALTHCARE','유전자 검사 서비스','GOLD',80,100,'LOW','유전자검사'),
('HLT','TELEMED','건강상담 화상진료','CARE',0,100,'LOW','비대면 상담'),
('HLT','HEALTHCARE','시니어 건강 패키지','SILVER',70,100,'LOW','시니어 헬스'),
('HLT','HEALTHCARE','여성 건강 패키지','SILVER',70,100,'LOW','여성 헬스'),
('HLT','HEALTHCARE','남성 건강 패키지','SILVER',70,100,'LOW','남성 헬스'),
('HLT','WELLNESS','마음건강 상담','CARE',0,100,'LOW','심리상담'),
('HLT','WELLNESS','운동센터 멤버십','BASIC',60,100,'LOW','운동 멤버십'),
('HLT','POINT','건강 포인트 리워드','CARE',0,100,'LOW','건강 리워드'),
('HLT','HEALTHCARE','VIP 라이프케어','VIP',90,100,'LOW','VIP 라이프케어');


SELECT
    category_code,
    COUNT(*) AS cnt
FROM base_product_pool
GROUP BY category_code
ORDER BY category_code;
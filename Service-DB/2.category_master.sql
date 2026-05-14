-- ===============================================================
-- STEP 2. category_master Sample Data
-- LifeSync360 AI Recommendation Category Master
-- ===============================================================

USE lifesync360;

INSERT INTO category_master
(
    category_code,
    category_name,
    active_flag
)
VALUES
('DEPOSIT',     '예금',              'Y'),
('SAVING',      '적금',              'Y'),
('LOAN',        '대출',              'Y'),
('PENSION',     '연금/IRP',          'Y'),

('CARD',        '카드',              'Y'),
('POINT',       '포인트/리워드',      'Y'),
('LIFESTYLE',   '생활혜택',          'Y'),

('ETF',         'ETF',               'Y'),
('FUND',        '펀드',              'Y'),
('WM',          '자산관리',          'Y'),

('INSURANCE',   '보험',              'Y'),
('DIRECT_INS',  '온라인보험',        'Y'),

('HEALTHCARE',  '헬스케어',          'Y'),
('WELLNESS',    '건강관리/웰니스',    'Y'),
('TELEMED',     '화상진료/건강상담',  'Y');


SELECT
    category_id,
    category_code,
    category_name,
    active_flag,
    created_at
FROM category_master
ORDER BY category_id;
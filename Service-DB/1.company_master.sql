-- ===============================================================
-- company_master Sample Data
-- ===============================================================
USE lifesync360;


INSERT INTO company_master
(
    company_code,
    company_name,
    company_type,
    active_flag
)

VALUES

(
    'BANK',
    'LifeSync Bank',
    'BANK',
    'Y'
),

(
    'CARD',
    'LifeSync Card',
    'CARD',
    'Y'
),

(
    'SEC',
    'LifeSync Securities',
    'SEC',
    'Y'
),

(
    'INS',
    'LifeSync Insurance',
    'INSURANCE',
    'Y'
),

(
    'ONINS',
    'LifeSync Direct Insurance',
    'ONLINE_INS',
    'Y'
),

(
    'HLT',
    'LifeSync Healthcare',
    'HEALTHCARE',
    'Y'
);
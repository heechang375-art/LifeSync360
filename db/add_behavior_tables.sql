-- Aurora MySQL: 추천 이력 테이블
CREATE TABLE IF NOT EXISTS customer_recommend_history (
    id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_id      VARCHAR(30)  NOT NULL,
    product_name   VARCHAR(100) NOT NULL,
    product_code   VARCHAR(50),
    affiliate_id   VARCHAR(20),
    recommended_at DATETIME     NOT NULL,
    clicked_at     DATETIME,
    purchased_at   DATETIME,
    INDEX idx_global (global_id),
    INDEX idx_recommended_at (recommended_at)
);

-- Aurora MySQL: 행동 이벤트 로그 (Level 2 상품 탐색)
-- event_type: 'product_view' | 'tab_click' | 'product_compare' | 'affiliate_explore'
-- event_target: 상품명 또는 탭명
CREATE TABLE IF NOT EXISTS customer_event_log (
    id           BIGINT       AUTO_INCREMENT PRIMARY KEY,
    global_id    VARCHAR(30)  NOT NULL,
    event_type   VARCHAR(30)  NOT NULL,
    event_target VARCHAR(100),
    occurred_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_global_id (global_id),
    INDEX idx_occurred_at (occurred_at),
    INDEX idx_event_type (event_type)
);

"""
Lifesync360_UI_설계서_V1.pptx 기반 Admin Dashboard wireframe.
4 화면: Executive / Customer 360 / AI 추천 / Network & Connectivity
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT_DIR = Path(__file__).parent
FONT_REG = "C:/Windows/Fonts/malgun.ttf"
FONT_BLD = "C:/Windows/Fonts/malgunbd.ttf"

BG       = (248, 250, 252)
SIDEBAR  = (15, 23, 42)
SB_ITEM  = (203, 213, 225)
SB_HILT  = (99, 102, 241)
SB_SUB   = (148, 163, 184)
CARD     = (255, 255, 255)
BORDER   = (226, 232, 240)
TEXT     = (30, 41, 59)
MUTED    = (100, 116, 139)
HEADER   = (15, 23, 42)
ACCENT   = (99, 102, 241)
GOOD     = (22, 163, 74)
WARN     = (245, 158, 11)
BAD      = (220, 38, 38)
BLUE     = (59, 130, 246)
PURPLE   = (139, 92, 246)
TEAL     = (20, 184, 166)
ORANGE   = (249, 115, 22)
PINK     = (236, 72, 153)


def f(size, bold=False):
    return ImageFont.truetype(FONT_BLD if bold else FONT_REG, size)


def sidebar(d, active_idx, sub_items=None):
    d.rectangle([0, 0, 220, 800], fill=SIDEBAR)
    d.text((24, 28), "LifeSync360", font=f(18, True), fill=(255, 255, 255))
    d.text((24, 52), "Admin Console", font=f(11), fill=SB_SUB)
    items = [
        ("Executive Dashboard",     "전체 현황"),
        ("Customer 360",            "고객 통합 프로필"),
        ("AI 추천",                 "BigQuery + Vertex AI"),
        ("Network & Connectivity", "멀티클라우드 / VM"),
    ]
    y = 100
    for i, (label, sub) in enumerate(items):
        if i == active_idx:
            d.rectangle([12, y - 6, 208, y + 36], fill=SB_HILT)
            d.text((24, y), label, font=f(13, True), fill=(255, 255, 255))
            d.text((24, y + 18), sub, font=f(10), fill=(224, 231, 255))
        else:
            d.text((24, y), label, font=f(13), fill=SB_ITEM)
            d.text((24, y + 18), sub, font=f(10), fill=SB_SUB)
        y += 56

        # Executive 활성 시 하위 메뉴 노출
        if i == 0 and active_idx == 0 and sub_items:
            for s in sub_items:
                d.text((36, y), "·  " + s, font=f(11), fill=SB_SUB)
                y += 26
            y += 8

    d.text((24, 758), "USE_MOCK: OFF", font=f(10), fill=MUTED)


def topbar(d, title):
    d.rectangle([220, 0, 1400, 60], fill=CARD, outline=BORDER, width=1)
    d.text((240, 18), title, font=f(18, True), fill=HEADER)
    d.text((1280, 22), "admin@lifesync", font=f(12), fill=MUTED)


def card(d, x, y, w, h, title=None, sub=None):
    d.rectangle([x, y, x + w, y + h], fill=CARD, outline=BORDER, width=1)
    if title:
        d.text((x + 16, y + 14), title, font=f(13, True), fill=TEXT)
    if sub:
        d.text((x + 16, y + 34), sub, font=f(10), fill=MUTED)


def kpi(d, x, y, w, h, label, value, color=ACCENT, sub=None):
    card(d, x, y, w, h)
    d.text((x + 16, y + 14), label, font=f(11), fill=MUTED)
    d.text((x + 16, y + 36), value, font=f(28, True), fill=color)
    if sub:
        d.text((x + 16, y + h - 22), sub, font=f(10), fill=MUTED)


def bar(d, x, y, w, pct, color=ACCENT, bg=(241, 245, 249), h=10):
    d.rectangle([x, y, x + w, y + h], fill=bg)
    fw = int(w * min(max(pct, 0), 100) / 100)
    if fw > 0:
        d.rectangle([x, y, x + fw, y + h], fill=color)


def th(d, x, y, w, cols):
    d.line([x, y + 24, x + w, y + 24], fill=BORDER, width=1)
    cw = w // len(cols)
    for i, c in enumerate(cols):
        d.text((x + i * cw + 8, y + 6), c, font=f(11, True), fill=MUTED)


def tr(d, x, y, w, cells, row_h=28):
    cw = w // len(cells)
    for i, c in enumerate(cells):
        d.text((x + i * cw + 8, y + 6), str(c), font=f(11), fill=TEXT)
    d.line([x, y + row_h, x + w, y + row_h], fill=(241, 245, 249), width=1)


def status_dot(d, x, y, color):
    d.ellipse([x, y, x + 10, y + 10], fill=color)


# ===================== 사이드바 비교 =====================
def sidebar_compare():
    img = Image.new("RGB", (1400, 600), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 24), "Admin 사이드바 — UI 설계서 V1 기준 4메뉴", font=f(20, True), fill=HEADER)
    d.text((40, 54), "Lifesync360_UI_설계서_V1.pptx · slide 1~4", font=f(11), fill=MUTED)

    # 사이드바 묘사
    d.rectangle([60, 100, 320, 560], fill=SIDEBAR)
    d.text((76, 116), "LifeSync360", font=f(16, True), fill=(255, 255, 255))
    d.text((76, 138), "Admin Console", font=f(10), fill=SB_SUB)

    menus = [
        ("Executive Dashboard",     "전체 현황 요약",  ACCENT,
         ["추천 현황", "고객 현황", "AI 추천 현황", "AWS 운영 상태", "GCP 상태"]),
        ("Customer 360",            "고객 통합 프로필",  None, []),
        ("AI 추천",                 "BigQuery + Vertex AI", None, []),
        ("Network & Connectivity", "멀티클라우드 / VM",  None, []),
    ]
    y = 180
    for label, sub, hi, kids in menus:
        if hi:
            d.rectangle([72, y - 4, 308, y + 36], fill=hi)
            d.text((84, y), label, font=f(12, True), fill=(255, 255, 255))
            d.text((84, y + 18), sub, font=f(9), fill=(224, 231, 255))
        else:
            d.text((84, y), label, font=f(12, True), fill=SB_ITEM)
            d.text((84, y + 18), sub, font=f(9), fill=SB_SUB)
        y += 48
        for kid in kids:
            d.text((100, y), "·  " + kid, font=f(10), fill=SB_SUB)
            y += 22

    # 우측 설명
    d.text((380, 100), "설계서 의도 (V1)", font=f(15, True), fill=HEADER)
    lines = [
        ("Slide 1", "Executive Dashboard",
         "KPI Cards(고객 100K/추천 1M+/CTR/CVR) + S3 적재 + Cloud Status (AWS Aurora·Redis / GCP BigQuery / Vertex AI)"),
        ("Slide 2", "Customer 360",
         "global_id 검색 → Customer Profile + Personalized Recommendation(Redis) + Recent Activity(행동/구매)"),
        ("Slide 3", "AI 추천",
         "BigQuery 분석(CTR/CVR/TOP10/세그먼트) + Vertex AI(Accuracy·Precision/Recall·Feature 분포)"),
        ("Slide 4", "Network & Connectivity",
         "Transit Gateway · AWS↔GCP VPN · Group/Wearable VM · Local Lab(VirtualBox/Docker/K8s)"),
    ]
    sy = 140
    for tag, title, desc in lines:
        d.rectangle([380, sy, 420, sy + 24], fill=ACCENT)
        d.text((388, sy + 4), tag, font=f(11, True), fill=(255, 255, 255))
        d.text((434, sy + 2), title, font=f(13, True), fill=HEADER)
        d.text((434, sy + 26), desc, font=f(11), fill=TEXT)
        sy += 70

    img.save(OUT_DIR / "00_sidebar.png", optimize=True)
    print("saved 00_sidebar.png")


# ===================== Slide 1: Executive Dashboard =====================
def screen_executive():
    img = Image.new("RGB", (1400, 850), BG)
    d = ImageDraw.Draw(img)
    sidebar(d, 0, sub_items=["추천 현황", "고객 현황", "AI 추천 현황", "AWS 운영 상태", "GCP 상태"])
    topbar(d, "Executive Dashboard  ·  전체 현황 요약")

    # KPI Cards (4)
    kpi(d, 240, 80,  270, 110, "총 고객 수",       "100,000",   ACCENT, "Aurora customer master")
    kpi(d, 520, 80,  270, 110, "총 추천 건수",     "1,234,890", BLUE,   "customer_recommend_history")
    kpi(d, 800, 80,  270, 110, "클릭률 (CTR)",     "23.4%",     WARN,   "dashboard_log 기준")
    kpi(d, 1080,80,  270, 110, "구매 전환율 (CVR)","4.8%",      GOOD,   "지난주 대비 +0.7p")

    # 2열: Redis 추천 Cache
    kpi(d, 240, 210, 540, 100, "Redis 추천 Cache 수", "98,420 keys",  PURPLE,
        "TTL 평균 6h · hit-rate 87.3%")
    kpi(d, 800, 210, 555, 100, "실시간 추천 호출",     "412 req/sec", TEAL,
        "마지막 1분 평균 · p95 138ms")

    # S3 Data Ingestion
    card(d, 240, 330, 540, 280, "S3 Data Ingestion",
         "Raw Bucket · 오늘 적재 · IoT · CSV/JSON 업로드")
    th(d, 240, 380, 540, ["항목", "값", "상태"])
    rows = [
        ("Raw Bucket 파일 수",   "84,290",       "정상"),
        ("오늘 적재 건수",       "12,438",       "+8% vs 어제"),
        ("IoT 웨어러블 건수",    "284,113",      "실시간"),
        ("최근 CSV/JSON 업로드", "09:14 · 2.3MB", "OK"),
        ("처리 실패",            "0건",          "정상"),
    ]
    ry = 408
    for r in rows:
        tr(d, 240, ry, 540, r, row_h=32)
        ry += 36

    # Cloud Status
    card(d, 800, 330, 555, 280, "Cloud Status",
         "AWS · GCP · Vertex AI")
    cy = 380
    cloud_rows = [
        ("AWS Aurora",          "● UP",   "writer 1 · reader 2", GOOD),
        ("AWS Redis (Elasti)",  "● UP",   "cluster · 3 nodes",   GOOD),
        ("AWS S3",              "● UP",   "6 buckets",            GOOD),
        ("GCP BigQuery",        "● UP",   "dataset: lifesync_dwh", GOOD),
        ("GCP Vertex AI",       "● UP",   "endpoint: nba-v2.3.1",  GOOD),
    ]
    th(d, 800, 380, 555, ["서비스", "상태", "비고"])
    cy = 410
    for name, st, note, col in cloud_rows:
        d.text((808, cy + 6), name, font=f(11, True), fill=TEXT)
        d.text((1000, cy + 6), st, font=f(11, True), fill=col)
        d.text((1100, cy + 6), note, font=f(11), fill=MUTED)
        d.line([800, cy + 32, 1355, cy + 32], fill=(241, 245, 249), width=1)
        cy += 36

    # 하단: API 엔드포인트
    card(d, 240, 630, 1115, 200, "API 엔드포인트")
    th(d, 240, 670, 1115, ["엔드포인트", "설명", "샘플 응답"])
    ar = [
        ("/api/dashboard/summary",  "KPI 요약",         "{ total_customers: 100000, total_recommend: 1234890, ctr: 0.234 }"),
        ("/api/s3/status",          "S3 적재 현황",     "{ raw_files: 84290, today_ingested: 12438, iot_count: 284113 }"),
        ("/api/cloud/status",       "AWS/GCP/Vertex 상태", "{ aws: UP, gcp: UP, vertex: UP }"),
    ]
    ay = 700
    for r in ar:
        tr(d, 240, ay, 1115, r, row_h=36)
        ay += 40

    img.save(OUT_DIR / "01_executive.png", optimize=True)
    print("saved 01_executive.png")


# ===================== Slide 2: Customer 360 =====================
def screen_customer360():
    img = Image.new("RGB", (1400, 850), BG)
    d = ImageDraw.Draw(img)
    sidebar(d, 1)
    topbar(d, "Customer 360  ·  고객 통합 프로필 및 추천 현황")

    # 검색 바
    card(d, 240, 80, 1115, 60)
    d.text((256, 100), "global_id 검색:", font=f(12, True), fill=TEXT)
    d.rectangle([380, 95, 1100, 125], outline=BORDER, width=1)
    d.text((392, 100), "GID-78421",  font=f(12), fill=TEXT)
    d.rectangle([1110, 92, 1200, 128], fill=ACCENT)
    d.text((1133, 100), "조회", font=f(12, True), fill=(255, 255, 255))
    d.text((1210, 100), "  Aurora · Redis · BigQuery 통합 조회", font=f(11), fill=MUTED)

    # 좌: Customer Profile
    card(d, 240, 160, 380, 300, "Customer Profile",
         "데이터 소스: Aurora customer 마스터")
    d.ellipse([260, 215, 320, 275], fill=ACCENT)
    d.text((275, 232), "82", font=f(20, True), fill=(255, 255, 255))
    d.text((340, 218), "홍길동", font=f(15, True), fill=TEXT)
    d.text((340, 240), "GID-78421  ·  VIP", font=f(11), fill=MUTED)

    px, py = 260, 300
    rows = [("고객 ID",   "GID-78421"),
            ("고객 등급", "VIP"),
            ("AI Score", "82 / 100"),
            ("건강 점수", "78  (Wearable: Apple Watch)"),
            ("연령/성별", "42세 / 남"),
            ("지역",     "서울 강남")]
    for k, v in rows:
        d.text((px, py), f"{k}:", font=f(11), fill=MUTED)
        d.text((px + 80, py), v, font=f(11, True), fill=TEXT)
        py += 22

    # 중: Personalized Recommendation (Redis)
    card(d, 640, 160, 380, 300, "Personalized Recommendation",
         "데이터 소스: Redis cache")
    d.text((660, 210), "Top 3 추천", font=f(11, True), fill=MUTED)
    recs = [
        ("PB 예금 패키지",  "은행",     "AI 0.92", PURPLE),
        ("VIP 신용카드",    "카드",     "AI 0.88", BLUE),
        ("건강검진 패키지", "헬스케어", "AI 0.85", TEAL),
    ]
    ry = 240
    for name, cat, score, col in recs:
        d.rectangle([660, ry, 1000, ry + 56], outline=BORDER, width=1)
        d.text((672, ry + 8), name, font=f(13, True), fill=TEXT)
        d.text((672, ry + 30), cat, font=f(11), fill=MUTED)
        d.rectangle([900, ry + 18, 988, ry + 38], fill=col)
        d.text((912, ry + 22), score, font=f(11, True), fill=(255, 255, 255))
        ry += 64

    d.text((660, 440), "교차판매: 보험·헬스 추천 풀 12건",
           font=f(11), fill=ORANGE)

    # 우: Recent Activity
    card(d, 1040, 160, 315, 300, "Recent Activity",
         "데이터 소스: dashboard_log")
    th(d, 1040, 200, 315, ["시각", "타입", "대상"])
    ar = [
        ("09:12", "구매",     "VIP 카드"),
        ("08:48", "클릭",     "건강검진"),
        ("어제",  "캠페인",   "VIP 헬스"),
        ("어제",  "클릭",     "PB 예금"),
        ("3일전", "구매",     "암보험 라이트"),
        ("3일전", "클릭",     "ELS 상품"),
        ("주말",  "캠페인",   "골드 적금"),
    ]
    ay = 230
    for r in ar:
        tr(d, 1040, ay, 315, r, row_h=28)
        ay += 30

    # 하단: 추천 이력 (Aurora customer_recommend_history)
    card(d, 240, 480, 1115, 350, "추천 이력 · customer_recommend_history (Aurora)")
    th(d, 240, 520, 1115, ["상품명", "카테고리", "추천 시각", "클릭", "구매", "AI Score"])
    hr = [
        ("VIP 신용카드",         "카드",     "2026-05-15 09:12", "✓", "✓", "0.88"),
        ("건강검진 패키지",      "헬스케어", "2026-05-14 18:30", "✓", "×", "0.85"),
        ("PB 예금 패키지",       "은행",     "2026-05-13 10:05", "✓", "×", "0.92"),
        ("암보험 라이트",        "보험",     "2026-05-10 14:22", "✓", "✓", "0.79"),
        ("ISA 절세 상품",        "증권",     "2026-05-08 11:18", "×", "×", "0.71"),
        ("청년 적금 Plus",       "은행",     "2026-05-06 09:40", "×", "×", "0.68"),
        ("자동차 보험 비교",     "보험",     "2026-05-03 16:00", "✓", "×", "0.74"),
        ("VIP 헬스케어 라이프",  "헬스케어", "2026-04-28 13:50", "✓", "✓", "0.90"),
    ]
    hy = 552
    for r in hr:
        tr(d, 240, hy, 1115, r, row_h=32)
        hy += 34

    img.save(OUT_DIR / "02_customer360.png", optimize=True)
    print("saved 02_customer360.png")


# ===================== Slide 3: AI 추천 =====================
def screen_ai():
    img = Image.new("RGB", (1400, 850), BG)
    d = ImageDraw.Draw(img)
    sidebar(d, 2)
    topbar(d, "AI 추천  ·  BigQuery + Vertex AI 기반 분석")

    # 상단 Recommendation KPI
    kpi(d, 240, 80,  270, 110, "전체 CTR",   "23.4%",  WARN,  "BigQuery 7일 평균")
    kpi(d, 520, 80,  270, 110, "전체 CVR",   "4.8%",   GOOD,  "구매 전환")
    kpi(d, 800, 80,  270, 110, "AI Accuracy","87.4%",  ACCENT,"Vertex AI nba-v2.3.1")
    kpi(d, 1080,80,  270, 110, "Precision/Recall","0.82 / 0.79", PURPLE, "validation set")

    # BigQuery Analytics — TOP10 + 카테고리
    card(d, 240, 210, 730, 290, "BigQuery Analytics  ·  추천 상품 TOP 10")
    th(d, 240, 250, 730, ["순위", "상품명", "카테고리", "추천수", "CTR", "CVR"])
    top10 = [
        ("1",  "VIP 신용카드",          "카드",    "12,840", "31.2%", "8.7%"),
        ("2",  "PB 예금 패키지",        "은행",    "11,205", "28.4%", "9.1%"),
        ("3",  "건강검진 패키지",       "헬스",    " 9,012", "25.8%", "6.2%"),
        ("4",  "암보험 라이트",         "보험",    " 7,892", "22.4%", "5.5%"),
        ("5",  "ISA 절세 상품",         "증권",    " 6,521", "21.1%", "4.8%"),
        ("6",  "VIP 헬스케어 라이프",   "헬스",    " 5,914", "26.3%", "7.1%"),
        ("7",  "자동차 보험 비교",      "보험",    " 4,820", "18.5%", "3.4%"),
    ]
    ty = 280
    for r in top10:
        tr(d, 240, ty, 730, r, row_h=30)
        ty += 30

    # 카테고리별 / 등급별
    card(d, 990, 210, 365, 290, "카테고리별 · 등급별 분포")
    d.text((1006, 250), "카테고리별 CTR", font=f(11, True), fill=MUTED)
    cats = [("카드", 31.2, BLUE), ("은행", 28.4, ACCENT), ("헬스", 25.8, TEAL),
            ("보험", 19.1, ORANGE), ("증권", 22.4, PURPLE)]
    cy = 274
    for name, val, col in cats:
        d.text((1006, cy), name, font=f(10), fill=TEXT)
        bar(d, 1056, cy + 6, 230, val * 3, color=col)
        d.text((1296, cy), f"{val}%", font=f(10), fill=MUTED)
        cy += 22

    d.text((1006, 392), "등급별 CVR", font=f(11, True), fill=MUTED)
    grades = [("VIP", 12.4, PURPLE), ("PLAT", 8.7, BLUE), ("GOLD", 5.2, WARN),
              ("SILVER", 3.9, ACCENT)]
    gy = 416
    for name, val, col in grades:
        d.text((1006, gy), name, font=f(10), fill=TEXT)
        bar(d, 1056, gy + 6, 230, val * 8, color=col)
        d.text((1296, gy), f"{val}%", font=f(10), fill=MUTED)
        gy += 22

    # Vertex AI — Accuracy/Feature
    card(d, 240, 520, 540, 310, "Vertex AI  ·  모델 성능")
    th(d, 240, 560, 540, ["메트릭", "값", "기준"])
    vr = [
        ("Model",            "nba-v2.3.1", "endpoint"),
        ("AUC",              "0.847",      "↑ 0.84 baseline"),
        ("Accuracy",         "87.4%",      "validation"),
        ("Precision",        "0.82",       ""),
        ("Recall",           "0.79",       ""),
        ("학습 일자",         "2026-04-28", "weekly retrain"),
    ]
    vy = 590
    for r in vr:
        tr(d, 240, vy, 540, r, row_h=32)
        vy += 34

    # Feature Importance
    card(d, 800, 520, 555, 310, "Feature Importance (Top 8)")
    feats = [("age",                0.182),
             ("ai_score_prev",      0.156),
             ("wearable_avg_hr",    0.124),
             ("income_band",        0.108),
             ("recent_purchase",    0.094),
             ("session_count_7d",   0.076),
             ("city_tier",          0.062),
             ("campaign_response",  0.048)]
    fy = 560
    for name, val in feats:
        d.text((816, fy), name, font=f(11), fill=TEXT)
        bar(d, 980, fy + 6, 280, val * 400, color=PURPLE)
        d.text((1280, fy), f"{val:.3f}", font=f(11), fill=MUTED)
        fy += 30

    img.save(OUT_DIR / "03_ai.png", optimize=True)
    print("saved 03_ai.png")


# ===================== Slide 4: Network & Connectivity =====================
def screen_network():
    img = Image.new("RGB", (1400, 850), BG)
    d = ImageDraw.Draw(img)
    sidebar(d, 3)
    topbar(d, "Network & Connectivity  ·  멀티클라우드 + VM 상태")

    # 상단 4 KPI
    kpi(d, 240, 80,  270, 110, "Transit Gateway", "● UP", GOOD, "tgw-0a3b... · 3 attachments")
    kpi(d, 520, 80,  270, 110, "AWS↔GCP VPN",     "● UP", GOOD, "Tunnel1: UP / Tunnel2: UP")
    kpi(d, 800, 80,  270, 110, "VM 가동",         "8/8",  GOOD, "Group 4 / Wearable 2 / Local 2")
    kpi(d, 1080,80,  270, 110, "이상 이벤트(24h)","2건",  WARN, "Wearable: 심박 alert 2")

    # AWS Connectivity 다이어그램 (간이)
    card(d, 240, 210, 540, 290, "AWS Connectivity",
         "Transit Gateway · Site-to-Site VPN · VPC peering")
    # AWS box
    d.rectangle([260, 270, 380, 340], fill=(255, 244, 230), outline=ORANGE, width=2)
    d.text((290, 290), "AWS VPC",  font=f(12, True), fill=ORANGE)
    d.text((280, 312), "Aurora · Redis", font=f(10), fill=MUTED)
    # TGW
    d.rectangle([420, 280, 530, 330], fill=ACCENT, outline=None)
    d.text((442, 295), "TGW", font=f(13, True), fill=(255, 255, 255))
    # GCP box
    d.rectangle([570, 270, 690, 340], fill=(229, 244, 255), outline=BLUE, width=2)
    d.text((597, 290), "GCP VPC",  font=f(12, True), fill=BLUE)
    d.text((580, 312), "BigQuery·Vertex", font=f(10), fill=MUTED)
    # arrows
    d.line([380, 305, 420, 305], fill=ORANGE, width=2)
    d.line([530, 305, 570, 305], fill=BLUE, width=2)
    d.text((380, 250), "VPN Tunnel  ↓",  font=f(10), fill=MUTED)

    # Routing / Traffic
    th(d, 240, 360, 540, ["구간", "상태", "Traffic 5m"])
    rr = [
        ("TGW Routing",                "● UP",    "—"),
        ("Tunnel 1 (AWS→GCP)",         "● UP",    "12.4 Mbps"),
        ("Tunnel 2 (AWS→GCP)",         "● UP",    "11.8 Mbps"),
        ("VPC Peering (AWS Aurora ↔ App)", "● UP", "8.2 Mbps"),
    ]
    ry = 390
    for r in rr:
        tr(d, 240, ry, 540, r, row_h=28)
        ry += 28

    # VM Status (Group / Wearable)
    card(d, 800, 210, 555, 290, "VM Status  ·  Group / Wearable")
    th(d, 800, 250, 555, ["VM", "상태", "CPU", "Mem", "API"])
    vrows = [
        ("group-vm-1",     "Running", "32%", "58%", "● Health"),
        ("group-vm-2",     "Running", "28%", "61%", "● Health"),
        ("group-vm-3",     "Running", "41%", "70%", "● Health"),
        ("group-vm-4",     "Running", "19%", "44%", "● Health"),
        ("wearable-vm-1",  "Running", "55%", "72%", "⚠ slow"),
        ("wearable-vm-2",  "Running", "47%", "65%", "● Health"),
    ]
    vy = 280
    for r in vrows:
        tr(d, 800, vy, 555, r, row_h=32)
        vy += 34

    # Wearable 실시간 메트릭
    card(d, 240, 520, 540, 310, "Wearable VM  ·  실시간 메트릭")
    th(d, 240, 560, 540, ["메트릭", "현재", "범위", "상태"])
    wr = [
        ("심박수",       "78 bpm",  "60~100",  "● 정상"),
        ("혈압",         "118/76",  "120↓",    "● 정상"),
        ("산소포화도",   "98%",     "95↑",     "● 정상"),
        ("운동량(steps)","6,420",   "—",       "● 정상"),
        ("이상 이벤트",  "alert 2", "24h",     "⚠ Warn"),
        ("데이터 송신",  "412/min", "—",       "● 정상"),
    ]
    wy = 590
    for r in wr:
        tr(d, 240, wy, 540, r, row_h=32)
        wy += 34

    # Local Lab
    card(d, 800, 520, 555, 310, "Local Lab  ·  VirtualBox / Docker / Kubernetes")
    th(d, 800, 560, 555, ["환경", "상태", "비고"])
    lr = [
        ("VirtualBox · VM1",      "● Running",  "Redis Local · 6379"),
        ("VirtualBox · VM2",      "● Running",  "Local MySQL · 3306"),
        ("Docker · flask-api",    "● Running",  "ports 5000/5001"),
        ("Docker · fastapi-api",  "● Running",  "ports 8000/8080"),
        ("K8s · cluster-dev",     "● Ready",    "nodes 3 / pods 12"),
        ("K8s · ingress-nginx",   "● Ready",    "loadbalancer up"),
    ]
    ly = 590
    for r in lr:
        tr(d, 800, ly, 555, r, row_h=32)
        ly += 34

    img.save(OUT_DIR / "04_network.png", optimize=True)
    print("saved 04_network.png")


if __name__ == "__main__":
    sidebar_compare()
    screen_executive()
    screen_customer360()
    screen_ai()
    screen_network()
    print("done")

# Admin Dashboard API 명세

설계서 V4 ↔ `admin-platform/app.py` 실제 라우트 정합 + 응답 JSON 폼 + 화면 표시 방법.

- **Base**: `admin-platform/app.py` Flask 라우트
- **인증**: `@login_required` 세션 cookie (admin 운영자 로그인 후)
- **USE_MOCK=true** (시연/로컬): mockup 반환. **USE_MOCK=false** (운영): 실 데이터 호출
- **응답**: `application/json` (Flask `jsonify`)
- **기준 일자**: 2026-05-18

---

## 0. 정합 매트릭스 — 설계서 V4 16 API + admin 내부 7 API = **23 API**

| 페이지 | # | Method | 설계서 V4 정의 | admin 실제 라우트 | 정합 |
|---|---|---|---|---|---|
| P1 | 1 | GET | `/api/dashboard/summary` | `/api/dashboard/summary` | ✅ |
| P1 | 2 | GET | `/api/s3/status` | `/api/s3/status` | ✅ |
| P1 | 3 | GET | `/api/cloud/status` | `/api/cloud/status` | ✅ |
| P2 | 4 | GET | `/api/customer/profile/{global_id}` | `/api/customer/profile/<global_id>` | ✅ |
| P2 | 5 | GET | `/api/customer/ai-result/{global_id}` | `/api/customer/ai-result/<global_id>` | ✅ |
| P2 | 6 | GET | `/api/customer/recommend/{global_id}` | `/api/customer/recommend/<global_id>` | ✅ |
| P2 | 7 | GET | `/api/customer/history/{global_id}` | `/api/customer/history/<global_id>` | ✅ |
| P2 | 8 | GET | `/api/customer/activity/{global_id}` | `/api/customer/activity/<global_id>` | ✅ |
| P3 | 9 | GET | `/api/ai/recommend-stats` | `/api/ai/recommend-stats` | ✅ |
| P3 | 10 | GET | `/api/bigquery/analytics` | `/api/bigquery/analytics` | ✅ |
| P3 | 11 | GET | `/api/ai/summary` | `/api/ai/summary` | ✅ |
| P4 | 12 | GET | `/api/network/tgw` | `/api/network/tgw` | ✅ |
| P4 | 13 | GET | `/api/network/vpn` | `/api/network/vpn` | ✅ |
| P4 | 14 | GET | `/api/vm/group` | `/api/vm/group` | ✅ |
| P4 | 15 | GET | `/api/vm/wearable` | `/api/vm/wearable` | ✅ |
| P4 | 16 | GET | `/api/local/status` | `/api/local/status` (+ `/api/admin/local-lab-status` alias) | ✅ |
| 보너스 P3 | 17 | GET | (V3 r10) | `/api/admin/recommend-trend` | admin 내부 |
| 보너스 P3 | 18 | GET | (V3 r12) | `/api/admin/segment-performance?dim=X` | admin 내부 |
| 보너스 P3 | 19 | GET | (V3 r13) | `/api/admin/demographic-summary?dim=X` | admin 내부 |
| 보너스 P1/P4 | 20 | GET | (V3 r23/r15) | `/api/kinesis/status` | admin 내부 |
| 보너스 P4 | 21 | GET | (V3 r13) | `/api/emr/status` | admin 내부 |
| 보너스 (관리) | 22 | GET | — | `/api/admin/applications?status&gid&limit&offset` | admin 내부 |
| 보너스 P4 | 23 | GET | — | `/api/admin/local-lab-status` (alias of 16) | admin 내부 |

→ **V4 16 API 100% 정합**, 추가로 admin 내부 운영용 7 API.

---

## 1. 페이지별 API 상세

### P1 — 전체 현황 (`/dashboard`)

#### 1.1 `GET /api/dashboard/summary` — KPI 카드 9종

**Backend**: `_stub_aurora_summary()` (`app.py:1139`)

**데이터 소스**:
- 시연 (USE_MOCK=true): `MOCKUP_KPI_TOP` + `MOCKUP_KPI_MID`
- 운영 (USE_MOCK=false): On-Prem Lambda `count_master_customer` / `count_users` / `count_users_consented`

**응답 JSON (운영 형식)**:
```json
{
  "master_customer": {"status": "ACTIVE", "count": 1000000},
  "users_active":    {"status": "ACTIVE", "count": 300000},
  "users_consented": {"count": 60000}
}
```
> ⚠ 시연 mockup 응답은 `{kpi_top, kpi_mid}` 9 카드 list 구조 — **운영 응답과 스키마 불일치**. 프론트엔드는 USE_MOCK 분기 또는 백엔드에서 통일 필요. 권장: 백엔드가 항상 `MOCKUP_DASH_KPI` 9 카드 list 형태로 반환하도록 변경.

**화면 표시**:
- `templates/dashboard.html` 9 KPI 카드 (3×3 그리드 `grid-3`)
- 각 카드: `{label, value, sub, accent, is_status}` → `.kpi` 클래스 + 좌측 border accent

#### 1.2 `GET /api/s3/status` — S3 적재 현황 5 카드

**Backend**: `_ping_s3_ingestion()` (운영) / `MOCKUP_S3_INGESTION_BOX` (시연)

**응답 JSON**:
```json
[
  {"label": "Raw Bucket 파일 수",    "value": "84,290",  "note": "s3://lifesync-raw"},
  {"label": "오늘 적재 건수",        "value": "12,438",  "note": "+8% vs 어제"},
  {"label": "웨어러블 / IoT 적재량", "value": "284,113", "note": "kinesis 5min sum"},
  {"label": "처리 실패",             "value": "0",       "note": "오류 없음"},
  {"label": "최근 업로드",           "value": "09:14",   "note": "wearable_2026-05-16.csv 2.3MB"}
]
```

**화면 표시**:
- `dashboard.html` "📦 S3 INGESTION" 섹션, `grid-5` 5 카드
- 각 카드: `{icon, label, value, note}` (현재 `MOCKUP_DASH_S3_5` 형식)
- 운영 응답 형식 통일 권장 (5 카드 list)

#### 1.3 `GET /api/cloud/status` — AWS/GCP 헬스

**Backend**: `_ping_cloud_status()` + `_stub_gcp_status()` (운영) / `MOCKUP_*_DETAIL` (시연)

**응답 JSON**:
```json
{
  "aws": [
    {"service": "Aurora MySQL",      "state": "UP", "metric": "writer 1 · reader 2",       "detail": "conn 12% · P95 8ms"},
    {"service": "DynamoDB",          "state": "UP", "metric": "4 tables · 1.2M items",     "detail": "RCU 24 · WCU 8"},
    {"service": "ElastiCache Redis", "state": "UP", "metric": "cluster · 3 nodes",         "detail": "0.2ms · 99% hit"},
    {"service": "ECS",               "state": "UP", "metric": "2/2 running",               "detail": "CPU 32% · Mem 48%"},
    {"service": "ALB",               "state": "UP", "metric": "2/2 healthy targets",       "detail": "24h 5xx 0.02%"},
    {"service": "S3",                "state": "UP", "metric": "6 buckets",                 "detail": "today 12.4K objs"}
  ],
  "gcp": [
    {"service": "BigQuery",  "state": "UP", "metric": "lifesync_dwh",          "detail": "7d 142 jobs · 0 err"},
    {"service": "Vertex AI", "state": "UP", "metric": "nba-recommender v2.3.1","detail": "24h 996K infer"}
  ]
}
```

**화면 표시**:
- `dashboard.html` "☁️ CLOUD STATUS" — 3 카드 (`MOCKUP_DASH_CLOUD3` 별도 mockup으로 단순화)
- 운영: `/api/cloud/status` 호출 결과를 `MOCKUP_DASH_CLOUD3` 형태로 가공해서 표시 (카운트 집계)

---

### P2 — Customer 360 (`/users`)

#### 2.1 `GET /api/customer/profile/{global_id}` — 통합 프로필

**Backend**: `_call_onprem('get_all', global_id=...)` (운영) / `MOCK_USERS.get(gid, {})` (시연)

**응답 JSON (운영)**:
```json
{
  "global_id": "G000297409",
  "customer": {
    "global_id": "G000297409",
    "customer_status": "ACTIVE",
    "vip_grade": "VIP",
    "customer_type": "INDIVIDUAL",
    "first_created_dt": "2023-01-15T10:00:00",
    "last_updated_dt":  "2026-05-15T14:25:00",
    "identities": [
      {"domain": "BANK", "source_customer_id": "BNK-00000001", "created_dt": "2023-01-15T10:00:00"}
    ],
    "profile": {
      "lifesync_score": 85.4,
      "health_score":   72.3,
      "finance_score":  78.0,
      "asset_score":    75.0,
      "last_calc_dt":   "2026-05-15T04:00:00"
    }
  },
  "consents": [
    {"domain": "BANK", "consent_flag": "Y", "consent_version": "v1.0", "revoke_dt": null, "created_dt": "2023-01-15T10:00:00"}
  ]
}
```

⚠ **시연 응답 (`MOCK_USERS.get`)은 단순 `{ls_user_id, global_id, name, email, grade}` dict** — 운영 응답과 스키마 다름. 프론트엔드 분기 또는 시연 응답을 운영 구조로 통일 권장.

**화면 표시**:
- `templates/users.html` 프로필 헤더 + 가입/상태/동의/보유 박스
- 프로필: `customer.profile.lifesync_score` / `health_score` → AI 종합 / AI 건강 카드
- 가입/상태: `customer.first_created_dt` / `users.created_dt` / `last_login_dt` / `user_status` / `customer_status`
- 동의 8 도메인: `consents` 배열 필터 (consent_flag='Y' AND revoke_dt IS NULL) → pill badge
- 보유 계열사: `customer.identities` 배열 → pill badge

#### 2.2 `GET /api/customer/ai-result/{global_id}` — DDB AI 점수

**Backend**: `get_dynamo_table().get_item(Key={'global_id': gid})` (운영) / `MOCK_SCORES.get(gid, {})` (시연)

**응답 JSON** (lifesync_customer_result 11 컬럼):
```json
{
  "global_id":         "G000297409",
  "update_time":       "2026-05-17T04:30:00Z",
  "dynamic_grade":     "VIP",
  "dynamic_score":     "85.4",
  "health_score":      "72.3",
  "next_best_action":  "INSURANCE_UPSELL",
  "rec_prob":          "0.84",
  "signup_prob":       "0.81",
  "vip_prob":          "0.94",
  "source":            "GCP_lifesync",
  "ttl":               1779420557
}
```

**화면 표시**:
- AI 분석 결과 카드 (우측):
  - `next_best_action` → NBA 큰 텍스트
  - `vip_prob` / `signup_prob` / `rec_prob` → AI 예측 박스 + 추천 반응 가능성 progress bar
  - `update_time` → "데이터 갱신: ..." 우하단 텍스트

#### 2.3 `GET /api/customer/recommend/{global_id}` — Redis Top-N

**Backend**: `_stub_redis_personalized(global_id)` (운영, Redis ZREVRANGE) / `MOCKUP_REDIS_PERSONALIZED` (시연)

**응답 JSON**:
```json
{
  "top3": [
    {"rank": 1, "product": "PB 예금 패키지",  "category": "은행",     "ai_score": 0.92, "color": "#8b5cf6"},
    {"rank": 2, "product": "VIP 신용카드",    "category": "카드",     "ai_score": 0.88, "color": "#3b82f6"},
    {"rank": 3, "product": "건강검진 패키지", "category": "헬스케어", "ai_score": 0.85, "color": "#14b8a6"}
  ],
  "crosssell_count": 12,
  "crosssell_note":  "보험·헬스 추천 풀 12건",
  "source":          "redis",
  "ttl_minutes":     360
}
```

**화면 표시**:
- "🔥 PERSONALIZED 추천 (REDIS TOP-N)" 카드, `topn-row` 4건 (rank/product/score)
- 별도 "🔗 교차판매 추천" 카드 (cross_sell_rule + product_master JOIN — 별도 mockup `MOCKUP_CROSSSELL_LIST`)

#### 2.4 `GET /api/customer/history/{global_id}` — 추천 이력

**Backend**: `_stub_aurora_history(gid)` (`app.py:1150`)

**응답 JSON**:
```json
[
  {"product_name": "VIP 종합 건강검진", "recommended_at": "2026-05-04 10:00:00", "clicked_flag": "Y", "purchased_flag": "Y"},
  {"product_name": "VIP 자산관리 서비스","recommended_at": "2026-05-03 09:00:00", "clicked_flag": "Y", "purchased_flag": "N"}
]
```

**화면 표시**:
- "📊 최근 추천 활동" 카드, `topn-row` 4건
- 각 행: `recommended_at` (마지막 8자) / `product_name` / 상태 pill (PURCHASED/CLICKED/SHOWN 매핑)

#### 2.5 `GET /api/customer/activity/{global_id}` — 행동 로그

**Backend**: `_stub_aurora_activity(gid)` (`app.py:1168`)

**응답 JSON**:
```json
[
  {"view_time": "2026-05-15 14:25:00", "page_type": "MAIN",   "banner_click": "N", "product_click": "N", "click_product_id": null,  "session_id": "S-abc-001"},
  {"view_time": "2026-05-15 14:22:00", "page_type": "DETAIL", "banner_click": "N", "product_click": "Y", "click_product_id": 12345, "session_id": "S-abc-001"}
]
```

**화면 표시**:
- "📈 최근 행동 로그" 카드, `topn-row` 3건
- 각 행: `view_time` / `page_type` + click_product_id / pill (VIEW/CLICK/BANNER)

---

### P3 — AI 추천 (`/ai`)

#### 3.1 `GET /api/ai/recommend-stats` — 추천 성과

**Backend**: `_stub_recommend_stats()` (`app.py:1185`)

**응답 JSON**:
```json
{
  "kpi": {
    "ctr_7d":      23.4,
    "cvr_7d":       4.8,
    "accuracy":    87.4,
    "precision":    0.82,
    "recall":       0.79,
    "pr_combined": "0.82 / 0.79"
  },
  "trend_7day": [
    {"date": "05-09", "recommended": 142521, "ctr": 21.4, "cvr": 4.2},
    {"date": "05-10", "recommended": 148302, "ctr": 22.8, "cvr": 4.5}
  ],
  "segment_today": [
    {"snapshot_date": "2026-05-17", "segment_key": "gender#M",   "recommended": 8500, "clicked": 1200, "purchased": 110, "ctr": "14.1", "cvr": "9.2"}
  ],
  "prob_distribution": {
    "vip_prob_avg":    0.32,
    "signup_prob_avg": 0.45,
    "rec_prob_avg":    0.51,
    "histogram":       [342, 4281, 18512, 21204, 18661, 9412, 2188]
  }
}
```

**화면 표시**:
- "💎 핵심 추천 지표" 4 KPI 카드 (`MOCKUP_AI_KPI4` 별도 — CTR/CVR/예측적중/분석대상)
- "📈 7일 추이" SVG 차트 (막대 = recommended, 선 = ctr/cvr) — `trend_7day`
- "📊 연령대별 추천 성과" 막대 차트 — `segment_today` filter by `age_band#`

#### 3.2 `GET /api/bigquery/analytics?kind=X` — BigQuery 마트

**Backend**: `_stub_bigquery_analytics(kind)` (`app.py:1286`)
**Query**: `kind=recommendation_mart|customer_summary|prediction_result`

**응답 JSON** (kind=recommendation_mart):
```json
[
  {"recommendation_name": "PB_PRODUCT", "count": 14281},
  {"recommendation_name": "CARD_VIP",   "count":  8902}
]
```

**응답 JSON** (kind=customer_summary):
```json
[
  {"segment": "고소득+고자산", "count": 42189, "note": "VIP 후보"},
  {"segment": "의료비 가입",   "count":  8420, "note": "의료 가입 비율"}
]
```

**응답 JSON** (kind=prediction_result):
```json
[
  {"model_name": "VIP 예측 모델",  "eval_date": "2026-05-17", "precision_score": 66.7, "recall_score": 80.9},
  {"model_name": "추천 반응 모델", "eval_date": "2026-05-17", "precision_score": 81.2, "recall_score": 75.4}
]
```

**화면 표시**:
- "🔬 BIGQUERY 분석" 3 카드:
  - Feature 분포 (`MOCKUP_AI_FEATURE_DIST`) — Feature Importance 막대
  - 추천 데이터 (`?kind=recommendation_mart`) — name + count list
  - 고객 인사이트 (`?kind=customer_summary`) — segment + count list
- "🎯 Precision/Recall" — `?kind=prediction_result` 결과

#### 3.3 `GET /api/ai/summary` — AI 점수 분포

**Backend**: `_stub_ai_summary()` (`app.py:1195`)

**응답 JSON**:
```json
{
  "ai_kpi": {
    "ctr_7d":    23.4,
    "cvr_7d":     4.8,
    "accuracy": 87.4,
    "precision":  0.82,
    "recall":     0.79
  },
  "vertex_metrics": {
    "model_id":   "nba-recommender",
    "version":    "v2.3.1",
    "auc":        0.847,
    "trained_at": "2026-04-28 04:00:00"
  },
  "score_dist": [
    {"bucket": "0-20",   "count":    342},
    {"bucket": "20-40",  "count":  4281},
    {"bucket": "40-60",  "count": 18512},
    {"bucket": "60-80",  "count": 48204},
    {"bucket": "80-100", "count": 28661}
  ]
}
```

**화면 표시**:
- "📊 AI 예측 출현 분포 (DYNAMODB)" SVG 히스토그램 — `score_dist`
- "🤖 Vertex AI 모델 메타" — `vertex_metrics`

#### 3.4 (보너스) `GET /api/admin/recommend-trend` — 7일 추이 단독

**Backend**: `_aurora_recommend_trend_7day()` (`app.py:1097`)
→ `_stub_recommend_stats().trend_7day` 와 동일 내용 단독 반환

#### 3.5 (보너스) `GET /api/admin/segment-performance?dim=X` — DDB 세그먼트

**Backend**: `_ddb_query_today(DDB_SEGMENT_TABLE, sk_prefix='dim#')` (`app.py:1105`)
**Query**: `dim=gender|age_band|region|income|asset` (선택)

**응답 JSON**:
```json
[
  {"snapshot_date": "2026-05-17", "segment_key": "gender#M", "recommended": 8500, "clicked": 1200, "purchased": 110, "ctr": "14.1", "cvr": "9.2"},
  {"snapshot_date": "2026-05-17", "segment_key": "gender#F", "recommended": 7800, "clicked": 1080, "purchased":  98, "ctr": "13.8", "cvr": "9.1"}
]
```

#### 3.6 (보너스) `GET /api/admin/demographic-summary?dim=X` — DDB 인구분포

**Backend**: `_ddb_query_today(DDB_DEMOGRAPHIC_TABLE, sk_prefix='dim#')` (`app.py:1115`)

**응답 JSON**:
```json
[
  {"snapshot_date": "2026-05-17", "segment_key": "age_band#40s", "count": 27810, "pct": "27.81", "total": 1000000}
]
```

**화면 표시 (3.5 + 3.6)**:
- "👥 고객 등급 분포 (분석대상 60K)" → 3.6 호출 결과 (등급별 비율) → `MOCKUP_AI_GRADE_DIST` 형태
- "📊 연령대별 추천 성과" → 3.5 + 3.6 결합 (CTR × 비율)

---

### P4 — Network (`/ops`)

#### 4.1 `GET /api/network/tgw` — TGW 상태

**Backend**: `_ping_tgw()` (`app.py:1294`)

**응답 JSON**:
```json
{
  "id":          "tgw-0a3b8c2d1e4f5g6h7",
  "state":       "available",
  "attachments": 3,
  "note":        "AWS Aurora VPC ↔ GCP VPN ↔ On-prem"
}
```

**화면 표시**:
- "AWS Connectivity" 카드 (`MOCKUP_NET_AWS_CONNECTIVITY`) Transit Gateway row 채움

#### 4.2 `GET /api/network/vpn` — VPN 터널

**Backend**: `_ping_vpn()` (`app.py:1301`)

**응답 JSON**:
```json
{
  "tunnels": [
    {"id": "tun-aws-gcp-1",  "status": "UP", "bgp_asn": 65000, "traffic_in_mbps": 12.4, "traffic_out_mbps": 8.2, "peer": "GCP Cloud VPN"},
    {"id": "tun-aws-onprem", "status": "UP", "bgp_asn": 65100, "traffic_in_mbps":  2.1, "traffic_out_mbps": 0.9, "peer": "On-prem strongSwan"}
  ]
}
```

**화면 표시**:
- AWS Connectivity 카드 Site-to-Site VPN row — `2 tunnels · BGP 65000` 같은 요약

#### 4.3 `GET /api/vm/group` — Group VM EC2

**Backend**: `_ping_vm_status()` → filter (`app.py:1308`)

**응답 JSON**:
```json
[
  {"affiliate": "은행",      "cpu_pct": 32, "mem_pct": 58, "api_state": "UP",   "last_ping": "11:24:30"},
  {"affiliate": "카드",      "cpu_pct": 28, "mem_pct": 61, "api_state": "UP",   "last_ping": "11:24:25"}
]
```

**화면 표시**:
- "AWS Group VM VPC" 카드 (`MOCKUP_NET_AWS_GROUPVM`) — 8 row (BANK/CARD/SEC/INS/ONINS/HLT/HOS + Wearable EC2)

#### 4.4 `GET /api/vm/wearable` — Wearable 실시간

**Backend**: `_ping_wearable_metrics()` (`app.py:1318`)

**응답 JSON**:
```json
{
  "instances": [
    {"vm_id": "i-0a1b...04", "name": "wearable-vm-1 (agent)", "state": "running", "cpu_pct": 55, "mem_pct": 72}
  ],
  "metrics": [
    {"icon": "❤", "label": "심박수",       "value": "72",       "sub": "bpm"},
    {"icon": "🩺","label": "혈압",         "value": "118 / 76", "sub": "mmHg"},
    {"icon": "🫁","label": "산소 포화도",  "value": "98",       "sub": "%"},
    {"icon": "🚶","label": "운동량",       "value": "7,428",    "sub": "steps"},
    {"icon": "🚨","label": "이상 이벤트",  "value": "2",        "sub": "24h Alert · SNS"},
    {"icon": "📡","label": "데이터 송신",  "value": "100%",     "sub": "Kinesis PutRecord"}
  ]
}
```

**화면 표시**:
- "❤ WEARABLE 실시간 데이터 (KINESIS)" — `grid-6` 6 카드 (이상 이벤트 포함)

#### 4.5 `GET /api/local/status` — 온프레 종합 헬스

**Backend**: `_call_onprem('local_lab_status')` (`app.py:1125`)
**Alias**: `/api/admin/local-lab-status`

**응답 JSON** (PrivateAPI `/internal/health/local-lab` 응답 그대로):
```json
{
  "status": "pass",
  "time":   "2026-05-18T03:00:00Z",
  "environments": [
    {"env": "VirtualBox · ls-db",    "state": "Running", "note": "192.168.56.11:3306"},
    {"env": "VirtualBox · ls-token", "state": "Running", "note": "192.168.56.12:8000"},
    {"env": "VirtualBox · ls-api",   "state": "Running", "note": "192.168.56.13:80"}
  ],
  "checks": {
    "vm:ls-db":             [{"status":"pass","componentType":"system","observedValue":"192.168.56.11:3306","time":"..."}],
    "vm:ls-token":          [...],
    "vm:ls-api":            [...],
    "service:mysql":        [{"status":"pass","componentType":"datastore","observedValue":"8 tables","time":"..."}],
    "service:tokenization": [{"status":"pass","componentType":"component","observedValue":"http://192.168.56.12:8000/health","time":"..."}]
  }
}
```

**화면 표시**:
- "On-Prem VirtualBox" 카드 (`MOCKUP_NET_ONPREM`) 4 row 채움 (VirtualBox VM / Local MySQL / Tokenization / PrivateAPI)
- environments 배열을 그대로 토폴로지 / VPC 카드에 그림

#### 4.6 (보너스) `GET /api/kinesis/status` — Kinesis stream

**Backend**: `_ping_kinesis()` (`app.py:1328`)

**응답 JSON**:
```json
{
  "stream_name": "lifesync-wearable-stream",
  "status":      "ACTIVE",
  "shards":      4,
  "incoming_records_5min": 2059
}
```

#### 4.7 (보너스) `GET /api/emr/status` — EMR Cluster

**Backend**: `_ping_emr()` (`app.py:1335`)

**응답 JSON**:
```json
[
  {"id": "j-XXXX", "name": "Customer360 EMR", "state": "WAITING", "instance_count": 3}
]
```

---

### 관리 — Application (보너스)

#### 5.1 `GET /api/admin/applications?status&gid&limit&offset` — 신청 내역

**Backend**: `app.py:1342`
**Query**:
- `status` (선택): `RECEIVED|IN_REVIEW|APPROVED|REJECTED|CANCELED`
- `gid` (선택): 특정 global_id
- `limit` (default 50, max 200)
- `offset` (default 0)

**응답 JSON** (Service-DB v3 9컬럼 + JOIN 정보):
```json
{
  "total": 142,
  "limit": 50,
  "offset": 0,
  "rows": [
    {
      "application_id":   "APP-20260517143020-A3F8C1",
      "global_id":        "G000297409",
      "ls_user_id":       "LS-AABBCC11-000001",
      "product_code":     "INS-INSURANCE-00045-02",
      "product_name":     "프리미엄 실손 보험",
      "company_name":     "LS 보험",
      "category_name":    "보험",
      "status":           "IN_REVIEW",
      "reviewer_id":      null,
      "reviewed_at":      null,
      "created_at":       "2026-05-17 14:30:20",
      "updated_at":       "2026-05-17 14:30:20"
    }
  ]
}
```

**화면 표시**:
- admin 별도 신청 관리 화면 (현재 4 페이지 UI 외, 향후 추가 라우트)

---

## 2. 화면 데이터 흐름 (Backend → Frontend)

### 흐름 A — **SSR (Server-Side Render)** : 현재 4 페이지 기본

```
사용자 브라우저 → GET /dashboard (또는 /users, /ai, /ops)
   ↓
admin Flask 라우트 (e.g. dashboard(), users(), ai(), ops())
   ↓ mockup_data 또는 _stub_* 호출
   ↓ render_template('dashboard.html', kpi=..., cloud3=..., ...)
   ↓
HTML 응답 (서버에서 데이터 박혀 나옴, Jinja {% for %})
   ↓
브라우저가 그대로 표시 (JS 추가 호출 없음)
```

→ **현재 4 페이지는 이 방식**. 페이지 새로고침 = 새 데이터.

### 흐름 B — **AJAX** : 향후 실시간 갱신 시

```
사용자 브라우저 → GET /dashboard (SSR로 초기 렌더)
   ↓
JS setInterval 또는 버튼 클릭
   ↓ fetch('/api/dashboard/summary')
   ↓
JSON 응답
   ↓
JS가 DOM 갱신 (innerHTML 또는 React/Vue)
```

→ **현재 미적용**. 실시간 갱신 필요한 영역(KPI 9 / Cloud Status / S3 / Wearable 5)에 적용 권장.

### 흐름 C — **하이브리드**: SSR 초기 + AJAX 갱신

```
초기 페이지 로드: SSR (mockup 또는 운영 데이터)
   ↓
JS: 5 ~ 30초 polling 으로 /api/* 호출 → 카드 값만 갱신
```

→ **권장 패턴** — admin 대시보드 운영 모니터링에 적합.

---

## 3. API 응답 통일 권장 — 시연 vs 운영 스키마 정합

현재 USE_MOCK=true / false 분기에서 응답 구조가 다른 API 4건:

| API | 시연 응답 | 운영 응답 | 권장 |
|---|---|---|---|
| `/api/dashboard/summary` | `{kpi_top: [], kpi_mid: []}` 9 카드 list | `{master_customer, users_active, users_consented}` 카운트 dict | 운영도 9 카드 list 로 통일 (또는 별개 응답 필드) |
| `/api/customer/profile/{gid}` | `MOCK_USERS` 단순 dict (5필드) | `{customer, consents}` JOIN 합성 | 시연도 운영 구조로 통일 |
| `/api/customer/history/{gid}` | `MOCK_RECOMMEND_HISTORY` 기존 mockup | Aurora 쿼리 결과 — 컬럼명 동일 | ✅ 정합 |
| `/api/s3/status` | `MOCKUP_S3_INGESTION_BOX` 5 카드 list | `_ping_s3_ingestion()` dict (raw_bucket_files / today_ingested 등) | 운영도 5 카드 list 로 통일 |

→ 응답 통일 작업이 필요한 영역. 별도 라운드로 진행 권장.

---

## 4. 운영 전환 체크리스트 (USE_MOCK=true → false)

| # | 항목 | 영향 받는 API |
|---|---|---|
| 1 | PrivateAPI 재배포 (DBUtils + 10 신규 엔드포인트) | 1.1, 2.1, 4.5 |
| 2 | Lambda 재배포 (onprem_customer_query 18 action) | 1.1, 2.1, 4.5 |
| 3 | DDB `analytics_segment_daily` / `analytics_demographic_daily` 배포 (23 stack) | 3.1, 3.5, 3.6 |
| 4 | Aurora 마이그레이션 v3 (`customer_product_application` 9컬럼 + `customer_recommend_daily`) | 3.1, 3.4, 5.1 |
| 5 | Redis ElastiCache cluster + REDIS_HOST env 주입 | 2.3 |
| 6 | DynamoDB `lifesync_customer_result` 테이블 + IAM | 2.2, 3.3 |
| 7 | BigQuery PSC Endpoint + GCP 자격증명 | 3.2 |
| 8 | Vertex AI / Cloud Monitoring (GCP stub 미구현) | 1.3 (gcp 부분) |

---

## 5. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-18 | 설계서 V4 16 API ↔ admin 23 API 정합 매트릭스 + 응답 JSON 폼 + 화면 표시 방법 정리 (신규) |

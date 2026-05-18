# Admin Dashboard — 데이터 흐름 (Read API ↔ Write 적재)

각 API 가 어디서 데이터를 읽는지 + 그 데이터가 어떻게 쌓이는지 매핑.
`docs/admin-api.md` 의 read 측 명세 + 본 문서의 write 측 적재 흐름 = 운영 정합 완성.

- **기준 일자**: 2026-05-18
- **상호참조**: `docs/admin-api.md` (응답 JSON 폼) / `docs/private-api.md` (PrivateAPI 21 라우트) / `Service-DB/Aurora_MySQL_DB_Create.sql` (Aurora DDL) / `schema_reference.md` (On-Prem DDL) / `Aurora_Schema_Reference.md` (Aurora 12 테이블)

---

## 0. 전체 아키텍처 한눈

```
사용자(앱)
   │ register/login/consent/event/apply/recommendation
   ▼
Platform (ECS Fargate · ALB)
   ├─→ Aurora customer_recommend_history / customer_dashboard_log / customer_product_application
   ├─→ Redis rec:{global_id}  (TTL 6h)
   ├─→ DynamoDB lifesync_customer_result   (read · GetItem)
   └─→ PrivateAPI (Lambda 경유)
         └─→ On-Prem MySQL users/master_customer/customer_pii_secure/customer_360_profile/consent/customer_identity_map

계열사 Daily Batch (외부)
   └─→ S3 lifesync-raw/{domain}/dt=YYYY-MM-DD/

Wearable EC2 Agent (wearable_sender.py)
   └─→ Kinesis Data Streams (wearable-stream)
         └─→ S3 lifesync-raw/wearable/
         └─→ wearable-stream-lambda (실시간 처리)

GCP Vertex AI (일배치 KST 04:00)
   └─→ Cloud Run (lifesync-result-bridge)
         └─→ DynamoDB lifesync_customer_result  (PutItem)

EMR / Glue (일배치)
   ├─→ S3 lifesync-curated/
   └─→ BigQuery lifesync_curated.recommendation_mart / ai_feature_table

analytics_aggregator Lambda (KST 03:00)
   ├─→ Aurora customer_recommend_daily  (UPSERT)
   ├─→ DynamoDB analytics_segment_daily  (PutItem · batch_writer)
   └─→ DynamoDB analytics_demographic_daily  (PutItem · batch_writer)

Admin (Private Subnet EC2 — VPN/SSM 접근)
   └─→ 위 모든 저장소를 read (16 + 7 = 23 API)
```

---

## 1. 저장소별 Write 흐름 (적재 주체 / 빈도 / 책임)

### 1.1 Aurora MySQL `lifesync360` (AWS)

| 테이블 | Write 주체 | 빈도 / 트리거 | INSERT/UPDATE 호출 위치 |
|---|---|---|---|
| **company_master** | 마스터 적재 스크립트 | 일회성 (배포 시) | `Service-DB/1.company_master.sql` |
| **category_master** | 동일 | 일회성 | `Service-DB/2.category_master.sql` |
| **base_product_pool** | 동일 | 일회성 | `Service-DB/3.base_product_pool.sql` |
| **product_variant** | 동일 | 일회성 (Aurora_Create) | (마스터 DDL) |
| **product_master** | 동일 | 일회성 (10,000 행) | `Service-DB/4.product_master.sql` |
| **product_option** | 동일 | 일회성 | `Service-DB/5.product_option.sql` |
| **recommend_rule** | 동일 | 일회성 | `Service-DB/6.recommend_rule.sql` |
| **cross_sell_rule** | 동일 | 일회성 | `Service-DB/7.cross_sell_rule.sql` |
| **campaign_master** | 동일 | 일회성 | `Service-DB/8.campaign_master.sql` |
| **customer_recommend_history** | platform `api_recommendations` | **실시간** (사용자 추천 호출 시) | `lifesync360-platform/app.py` `_enrich_and_record` (`INSERT INTO ... VALUES (gid, product_id, dynamic_score, dynamic_grade, action_code, NOW())`) |
| | platform `api_event` | **실시간** (apply_submitted/purchased 이벤트) | `UPDATE customer_recommend_history SET clicked_flag='Y' WHERE ...` / `SET purchased_flag='Y' WHERE ...` |
| | platform `api_product_apply` | **실시간** (신청 제출 시) | `UPDATE ... SET purchased_flag='Y' ...` |
| **customer_dashboard_log** | platform `api_event` | **실시간** | `INSERT INTO customer_dashboard_log (global_id, page_type, banner_click, product_click, click_product_id, session_id, view_time)` |
| | platform `api_product_apply` | **실시간** (신청 시 자동 기록) | 동일 INSERT |
| **customer_product_application** ⭐신규 | platform `api_product_apply` | **실시간** | `INSERT INTO customer_product_application (application_id, global_id, ls_user_id, product_id)` (v3 4 컬럼) |
| | admin 심사 (향후) | 운영자 액션 | `UPDATE ... SET status, reviewer_id, reviewed_at` |
| **customer_recommend_daily** ⭐신규 (mart) | **analytics_aggregator Lambda** | **일배치 KST 03:00** | `INSERT ... SELECT GROUP BY DATE(recommended_at) ... ON DUPLICATE KEY UPDATE` (어제 1일치) |
| **model_performance_history** ⭐미정의 | (BigQuery lifesync_ml → Aurora sync 배치) | 일배치 | 미구현 — 별도 적재 Lambda 필요 |

### 1.2 On-Prem MySQL `lifesync_onprem` (192.168.56.11)

| 테이블 | Write 주체 | 빈도 / 트리거 | 호출 위치 |
|---|---|---|---|
| **users** | PrivateAPI `auth_register` | **실시간** (가입 시) | `onprem-prod-repo/.../app.py` `auth_register` INSERT |
| | PrivateAPI `auth_login` | (last_login_dt UPDATE — 현재 미구현) | TODO |
| **master_customer** | PrivateAPI `auth_register` | **실시간** | INSERT (`global_id` 단독) |
| | Matching 배치 (계열사 통합) | 일배치 | 외부 시스템 |
| **customer_pii_secure** | PrivateAPI `auth_register` | **실시간** | INSERT (AES-256-GCM 암호화 5컬럼) |
| **customer_360_profile** | 초기 dummy 적재 (1M 행) | 일회성 | `db/onprem_schema.sql` 또는 별도 seed |
| | (운영 시 인구통계 일배치 update — 미구현) | 일배치 | TODO |
| **customer_identity_map** | PrivateAPI `match_identity` | 매칭 시 | INSERT ON DUPLICATE KEY UPDATE |
| | 일배치 매칭 | 일배치 | 외부 |
| **consent** | PrivateAPI `auth_save_consent` | **실시간** (동의 변경 시) | UPSERT 8 도메인 |
| **matching_audit_log** | PrivateAPI `match_identity` | 매칭 시 | INSERT |
| **token_map** | tokenize batch | 일배치 또는 register 시 | TODO |

### 1.3 DynamoDB (AWS)

| 테이블 | Write 주체 | 빈도 / 트리거 | 흐름 |
|---|---|---|---|
| **lifesync_customer_result** (= lifesync-scores) | **Cloud Run lifesync-result-bridge** | **일배치 KST 04:00** | GCP Vertex AI 예측 결과 → Cloud Run → AWS DynamoDB `PutItem` (11컬럼 — results.csv 형식) |
| **analytics_segment_daily** ⭐신규 | **analytics_aggregator Lambda** | **일배치 KST 03:00** | Aurora history JOIN On-Prem profile_map → batch_writer 30~50 row |
| **analytics_demographic_daily** ⭐신규 | **analytics_aggregator Lambda** | **일배치 KST 03:00** | On-Prem profile_map (1M) → 5 차원 분포 → batch_writer 20~30 row |

### 1.4 Redis (AWS ElastiCache)

| 키 패턴 | Write 주체 | 빈도 / 트리거 | TTL |
|---|---|---|---|
| **rec:{global_id}** | platform `api_recommendations` | **실시간** (사용자 추천 호출 시) | 6h (`setex 21600 ...`) |

### 1.5 S3 `lifesync-raw` (AWS)

| Prefix | Write 주체 | 빈도 / 트리거 | 형식 |
|---|---|---|---|
| **{domain}/dt=YYYY-MM-DD/** (BANK/CARD/INS/ONINS/SEC/HLT/HOS) | 계열사 Daily Batch (외부) | **일배치** | CSV / JSON |
| **wearable/** | Kinesis Data Streams (Firehose) | **실시간** (5분 buffer) | JSON Lines |
| **consent/** ⭐신규 (1번 결정) | **동의 스냅샷 Lambda** (미구현) | 일배치 또는 PrivateAPI consent_save 시 trigger | JSON (`{global_id, domain, consent_flag, snapshot_dt}`) |

### 1.6 BigQuery (GCP)

| 테이블 / 뷰 | Write 주체 | 빈도 | 흐름 |
|---|---|---|---|
| **lifesync_curated.recommendation_mart** | EMR (Spark) | 일배치 | S3 lifesync-raw 적재 데이터 → EMR job → S3 lifesync-curated → BQ Load |
| **lifesync_curated.ai_feature_table** | EMR | 일배치 | 동일 |
| **lifesync_serving.v_customer_summary** | **VIEW** (write X) | 정의만 | SELECT JOIN customer_360_profile + score_mart + health_mart |
| **lifesync_ml.*_prediction_result** | Vertex AI Batch Prediction | 일배치 | Vertex AI → BQ 자동 출력 |

### 1.7 GCS (GCP)

| 객체 | Write 주체 | 빈도 |
|---|---|---|
| **gs://lifesync-models/feature_importance.json** | Vertex AI training export | 모델 재학습 시 (월 1회 미만) |

---

## 2. API ↔ Read Source ↔ Write 흐름 (23 API)

### P1 — 전체 현황

#### 2.1 `GET /api/dashboard/summary` — KPI 9 카드

| KPI | Read 소스 | Write 흐름 |
|---|---|---|
| 통합 고객 수 (1M) | On-Prem `master_customer COUNT(*) WHERE customer_status='ACTIVE'` (PrivateAPI `count_master_customer`) | platform register 시 `auth_register` INSERT (실시간) |
| 플랫폼 가입자 (300K) | On-Prem `users COUNT WHERE user_status='ACTIVE'` (PrivateAPI `count_users`) | 동일 (실시간) |
| 분석 대상 고객 (60K) | On-Prem `users JOIN consent ... consent_flag='Y' AND revoke_dt IS NULL` (PrivateAPI `count_users_consented`) | platform `consent_save` 시 consent UPSERT (실시간) |
| 누적 추천 이력 (487K) | Aurora `customer_recommend_history COUNT(*)` | platform `api_recommendations` INSERT (실시간) |
| 누적 활동 로그 (12.8M) | Aurora `customer_dashboard_log COUNT(*)` | platform `api_event` INSERT (실시간) |
| Redis Cache 수 (54K) | Redis `DBSIZE` (또는 `KEYS rec:* | wc`) | platform `api_recommendations` `setex` (TTL 6h 자동 만료) |
| 추천 CTR (14.2%) | Aurora `SUM(clicked='Y') / COUNT(*)` | clicked_flag 는 platform `api_event` `recommendation_click` 시 `UPDATE ... clicked_flag='Y'` |
| 구매 CVR (9.8%) | Aurora `SUM(purchased='Y') / NULLIF(SUM(clicked='Y'),0)` | purchased_flag 는 platform `api_event` `apply_submitted/purchased` 또는 `api_product_apply` 시 UPDATE |
| AI 추천 상태 (Vertex AI) | DDB `lifesync_customer_result.update_time` (전체 평균 또는 최신) | Cloud Run lifesync-result-bridge 일배치 KST 04:00 PutItem |

#### 2.2 `GET /api/s3/status` — S3 적재 5 카드

| KPI | Read 소스 | Write 흐름 |
|---|---|---|
| Raw Bucket 총 파일 | `boto3 s3.list_objects_v2 Bucket=lifesync-raw` | 계열사 Daily Batch (외부) + Wearable Firehose |
| 금일 적재 건수 | `Prefix={domain}/dt=YYYY-MM-DD/` 객체 수 | 동일 |
| 페이로드 (웨어러블) | Kinesis IncomingRecords 5분 합산 | wearable-sender (Wearable EC2 Agent) → Kinesis PutRecord |
| 그룹사 적재량 | `s3 list_objects_v2` 객체 size 합산 | 동일 |
| 최근 업로드 | LastModified 최신 5개 | 동일 |

#### 2.3 `GET /api/cloud/status` — AWS/GCP/On-Prem 헬스

| 서비스 | Read 소스 | Write 흐름 |
|---|---|---|
| AWS Aurora | `rds.describe_db_clusters` | AWS RDS 자체 (사용자 X) |
| AWS DynamoDB | `dynamodb.list_tables` | 위 1.3 참조 |
| AWS ElastiCache | `elasticache.describe_cache_clusters` | 위 1.4 참조 |
| AWS ECS/ALB/S3 | 각 describe API | AWS 인프라 |
| GCP BigQuery | (stub) GCP Monitoring | 위 1.6 |
| GCP Vertex AI | (stub) | Vertex AI 학습/예측 |
| On-Prem | PrivateAPI `/internal/health/local-lab` 종합 | VM 헬스 — 자동 응답 (사용자 적재 X) |

---

### P2 — Customer 360

#### 2.4 `GET /api/customer/profile/{global_id}` — 통합 프로필

| 필드 | Read 소스 | Write 흐름 |
|---|---|---|
| `customer.customer_status / vip_grade` | On-Prem `master_customer` | platform register `auth_register` INSERT |
| `customer.identities[]` | On-Prem `customer_identity_map` | Matching 배치 (외부) 또는 `match_identity` API |
| `customer.profile.lifesync_score / health_score` | On-Prem `customer_360_profile` | **초기 dummy 적재** (1M) + 운영 시 인구통계 batch update (TODO) |
| `customer.profile.finance/asset/risk_score` | 동일 | 정적 룰 기반 적재 (초기 dummy + 룰 추정 — 미구현) |
| `customer.profile (PII)` (이름/연락처) | On-Prem `customer_pii_secure` (복호화 + 마스킹) | `auth_register` AES 암호화 INSERT |
| `consents[]` | On-Prem `consent` 또는 S3 동의 스냅샷 ⭐신규 | platform `auth_save_consent` UPSERT (실시간) + 동의 스냅샷 Lambda → S3 (미구현) |

> **1번 결정사항 반영** — admin 의 consent 읽기를 PrivateAPI 직접 호출 → S3 ingest 결과 조회로 변경 예정. 동의 스냅샷 적재 Lambda 신설 필요 (TODO).

#### 2.5 `GET /api/customer/ai-result/{global_id}` — DDB AI 점수

| 필드 | Read | Write |
|---|---|---|
| `dynamic_grade / dynamic_score / health_score / vip_prob / signup_prob / rec_prob / next_best_action / update_time` | DDB `lifesync_customer_result.get_item(global_id)` | Cloud Run lifesync-result-bridge **일배치 KST 04:00** (Vertex AI → DDB PutItem) |

#### 2.6 `GET /api/customer/recommend/{global_id}` — Redis Top-N

| 필드 | Read | Write |
|---|---|---|
| `top3 / crosssell_count / source / ttl_minutes` | Redis `ZREVRANGE rec:{gid} 0 N WITHSCORES` (또는 GET + JSON decode) | platform `api_recommendations` `setex 21600` (TTL 6h, 실시간) — miss 시 Aurora fallback |

#### 2.7 `GET /api/customer/history/{global_id}` — 추천 이력

| 필드 | Read | Write |
|---|---|---|
| `product_name / recommended_at / clicked_flag / purchased_flag` | Aurora `customer_recommend_history WHERE global_id=? ORDER BY recommended_at DESC LIMIT N` | platform `api_recommendations` INSERT (실시간) + clicked/purchased UPDATE (이벤트) |

#### 2.8 `GET /api/customer/activity/{global_id}` — 행동 로그

| 필드 | Read | Write |
|---|---|---|
| `view_time / page_type / banner_click / product_click / click_product_id / session_id` | Aurora `customer_dashboard_log WHERE global_id=? ORDER BY view_time DESC LIMIT N` | platform `api_event` INSERT (실시간, 모든 사용자 액션) |

---

### P3 — AI 추천

#### 2.9 `GET /api/ai/recommend-stats` — 추천 성과 종합

| 필드 | Read | Write |
|---|---|---|
| `kpi.ctr_7d / cvr_7d` | Aurora `customer_recommend_history` SUM 집계 (7일) | platform 실시간 (history INSERT) |
| `trend_7day[]` | Aurora `customer_recommend_daily` 최근 7일 SELECT | **analytics_aggregator Lambda** 일배치 KST 03:00 UPSERT |
| `segment_today[]` | DDB `analytics_segment_daily` Query (PK=today) | **analytics_aggregator Lambda** 일배치 KST 03:00 batch_writer |
| `prob_distribution` | DDB `lifesync_customer_result` Scan + 집계 | Cloud Run 일배치 PutItem (위 2.5) |

#### 2.10 `GET /api/bigquery/analytics?kind=X` — BQ 마트

| kind | Read 소스 | Write |
|---|---|---|
| `recommendation_mart` | BQ `lifesync_curated.recommendation_mart` | EMR 일배치 (S3 → BQ Load) |
| `customer_summary` | BQ `lifesync_serving.v_customer_summary` (VIEW) | VIEW JOIN (write X) |
| `prediction_result` | BQ `lifesync_ml.*_prediction_result` | Vertex AI Batch Prediction 일배치 |

#### 2.11 `GET /api/ai/summary` — AI 점수 분포

| 필드 | Read | Write |
|---|---|---|
| `ai_kpi` | DDB Scan 평균 (vip_prob/signup/rec) | Cloud Run 일배치 |
| `vertex_metrics` | Vertex AI Model metadata API (stub) | Vertex AI 학습 시 |
| `score_dist[]` | DDB Scan + bucket 집계 (dynamic_score 0~100) | Cloud Run 일배치 |

#### 2.12 (보너스) `GET /api/admin/recommend-trend` — 7일 추이 단독

→ 2.9 `trend_7day` 부분과 동일 소스 (Aurora `customer_recommend_daily`)

#### 2.13 (보너스) `GET /api/admin/segment-performance?dim=X` — 세그먼트

→ DDB `analytics_segment_daily` Query (`SK begins_with 'dim#'`). analytics_aggregator Lambda 일배치.

#### 2.14 (보너스) `GET /api/admin/demographic-summary?dim=X` — 인구분포

→ DDB `analytics_demographic_daily` Query. 동일 Lambda.

---

### P4 — Network

#### 2.15 `GET /api/network/tgw` — TGW 상태

→ `boto3 ec2.describe_transit_gateways` (read only, AWS 자체 적재)

#### 2.16 `GET /api/network/vpn` — VPN 터널

→ `boto3 ec2.describe_vpn_connections` + CloudWatch metric

#### 2.17 `GET /api/vm/group` — Group VM EC2

→ `boto3 ec2.describe_instances` + CloudWatch agent metric (계열사 7 EC2)

#### 2.18 `GET /api/vm/wearable` — Wearable 6 지표

| 필드 | Read 소스 | Write 흐름 |
|---|---|---|
| instances | `boto3 ec2.describe_instances` (Wearable EC2) | AWS |
| metrics.심박수/혈압/SpO2/운동량 | CloudWatch custom metric `LifeSync/Wearable` 또는 Kinesis 통계 | Wearable EC2 Agent (`wearable_sender.py`) `PutMetricData` 또는 Kinesis PutRecord |
| 이상 이벤트 | CloudWatch metric / SNS topic count | wearable-stream-lambda (임계치 초과 시 SNS publish) |
| 데이터 송신 상태 | CloudWatch `IncomingRecords` 성공률 | Wearable EC2 Agent |

#### 2.19 `GET /api/local/status` — 온프레 종합

→ Lambda `onprem_customer_query` → PrivateAPI `/internal/health/local-lab` (실시간 헬스체크 시)

→ **별도 적재 없음** — admin 호출 시 PrivateAPI 가 ICMP/TCP/HTTP 검사 실시간 응답

#### 2.20 (보너스) `GET /api/kinesis/status` — Kinesis stream

→ `boto3 kinesis.describe_stream_summary`

#### 2.21 (보너스) `GET /api/emr/status` — EMR Cluster

→ `boto3 emr.list_clusters`

---

### 관리

#### 2.22 `GET /api/admin/applications?status&gid&limit&offset` — 신청 내역

→ Aurora `customer_product_application` (v3 9컬럼) + product/company/category JOIN
→ Write: platform `api_product_apply` 실시간 INSERT (status default RECEIVED) + admin 심사 시 UPDATE

---

## 3. 결정 사항 / 미정 / TODO

### ✅ 결정 사항

| # | 항목 | 처리 |
|---|---|---|
| 1 | DDB 분석 테이블명 | `analytics_segment_daily` / `analytics_demographic_daily` (설계서 V4 정합) |
| 2 | CVR 정의 | `purchased / NULLIF(SUM(clicked='Y'), 0) × 100` (마케팅 표준) |
| 3 | DDB `lifesync_customer_result` 컬럼 | results.csv 11 컬럼 정합 |
| 4 | 동의 스냅샷 → S3 | **결정** (설계서 V4 row 21-22 반영). admin 의 consent 조회를 PrivateAPI → S3 prefix 로 변경 예정 |
| 5 | admin 인스턴스 | **Private Subnet EC2 1대** (ECS 공개 admin X) |
| 6 | PII/인구통계 화면 | admin Private EC2 만, platform 사용자 본인 화면에 별도 표시 |

### ⏳ 미구현 / TODO

| # | 항목 | 영향 | 작업 |
|---|---|---|---|
| 1 | **동의 스냅샷 Lambda + S3 적재** | `/api/customer/profile/{gid}` 의 consents 부분 | Lambda 신설 — consent_save trigger 또는 일배치, S3 `lifesync-raw/consent/{gid}.json` 또는 `dt=YYYY-MM-DD/{gid}.json` |
| 2 | **admin consent 조회 S3 전환** | admin app.py | `_call_onprem('get_consent')` → S3 GetObject + JSON decode |
| 3 | `customer_360_profile` 운영 batch update | admin AI 분석 화면 정확도 | 인구통계 일배치 update Lambda 또는 EMR job |
| 4 | `model_performance_history` 적재 | P3 Precision/Recall | BigQuery lifesync_ml → Aurora sync Lambda |
| 5 | `lifesync-result-bridge` Cloud Run | DDB `lifesync_customer_result` 적재 | GCP Cloud Run 배포 (Vertex AI 결과 → DDB PutItem) |
| 6 | `users.last_login_dt` UPDATE | admin "최근 로그인" 정확도 | PrivateAPI `auth_login` 끝에 UPDATE 추가 |
| 7 | `users.consent_completed` sync | admin 분석대상 카운트 (옵션 A 경로) | `auth_save_consent` 시 users 도 UPDATE — **현재 B (consent JOIN) 유지 결정** |

### ⚠ 응답 스키마 시연 vs 운영 불일치 (별도 라운드)

| API | 시연 응답 | 운영 응답 | 처리 |
|---|---|---|---|
| `/api/dashboard/summary` | `{kpi_top, kpi_mid}` 9 카드 list | `{master_customer, users_active, users_consented}` 카운트 dict | 운영도 9 카드 list 통일 권장 |
| `/api/customer/profile/{gid}` | `MOCK_USERS` 단순 dict | `{customer, consents}` 합성 | 시연 → 운영 구조 통일 |
| `/api/s3/status` | 5 카드 list | `_ping_s3_ingestion()` dict | 운영도 list 통일 |

---

## 4. 운영 정합 체크리스트 (USE_MOCK=true → false 전환 시)

### 4.1 인프라
- [ ] Aurora 마이그레이션 — `bash Service-DB/service-db-execution.sh` (v3 9컬럼 + customer_recommend_daily)
- [ ] DynamoDB 2 테이블 신규 — `23-analytics-batch.yaml` deploy (`analytics_segment_daily` / `analytics_demographic_daily`)
- [ ] Redis ElastiCache cluster 생성 + REDIS_HOST env 주입
- [ ] PrivateAPI 재배포 — DBUtils pool + 10 신규 엔드포인트
- [ ] Lambda `onprem_customer_query` 재배포 — 18 action (list_profile_page 포함)
- [ ] Lambda `analytics_aggregator` 배포 — 23 stack
- [ ] EventBridge cron ENABLE (03:00 KST 일배치)

### 4.2 신규 적재 흐름 활성
- [ ] **Cloud Run `lifesync-result-bridge` 배포** — Vertex AI → DDB `lifesync_customer_result`
- [ ] **동의 스냅샷 Lambda 신설** — consent_save trigger 또는 일배치, S3 `consent/` 적재
- [ ] **EMR job** — S3 → BQ `lifesync_curated.recommendation_mart` / `ai_feature_table`
- [ ] **`model_performance_history` sync Lambda** — BigQuery → Aurora

### 4.3 코드 변경 (USE_MOCK=false 전환 후)
- [ ] admin `_call_onprem('get_consent')` → S3 GetObject 로 변경 (`get_consent_from_s3`)
- [ ] admin 응답 스키마 시연 ↔ 운영 통일 (위 ⚠ 3건)
- [ ] platform `auth_login` 끝에 `UPDATE users SET last_login_dt=NOW()` 추가
- [ ] PrivateAPI `/internal/pii` 마스킹 + RRN 기본 응답 제외 (보안)

### 4.4 admin 인스턴스 분리 (사용자 결정)
- [ ] 24-stack EC2 (Private Subnet) 작성 + SSM Session Manager 활성
- [ ] 21-stack admin ECS service / target group 폐기
- [ ] admin CI/CD — ECR push + SSM run-command 로 EC2 docker pull/restart

### 4.5 platform 사용자 본인 화면
- [ ] platform `/settings/consent` 보강 — 본인 동의 상태 표시 + 갱신 + audit log

---

## 5. 상호참조

| 문서 | 내용 |
|---|---|
| `docs/admin-api.md` | 23 API 의 응답 JSON 폼 + UI 매핑 |
| `docs/private-api.md` | PrivateAPI 21 라우트 명세 (호출 흐름) |
| `Service-DB/Aurora_MySQL_DB_Create.sql` | Aurora 12 테이블 DDL |
| `Service-DB/CHANGELOG.md` | Service-DB v3 변경 이력 |
| `schema_reference.md` | On-Prem `lifesync_onprem` 8 테이블 DDL |
| `Aurora_Schema_Reference.md` | Aurora 12 테이블 명세 (갱신 필요) |
| `Service-DB/NEW_TABLES_GUIDE.md` | `customer_product_application` + `customer_recommend_daily` 상세 |
| `lambda/analytics_aggregator/handler.py` | 일배치 적재 로직 (3 stage) |

---

## 6. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-18 | 23 API ↔ read source ↔ write 적재 흐름 매핑 + 결정/TODO + 운영 체크리스트 정리 (신규) |

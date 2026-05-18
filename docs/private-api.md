# PrivateAPI 엔드포인트 명세

- **위치**: `ls-api` (192.168.56.13) systemd `private-api.service`, nginx 80
- **코드**: `onprem-prod-repo/ansible/roles/private_api/files/app.py` (FastAPI)
- **DB 접속**: `lifesync_onprem` 스키마, DBUtils `PooledDB` (mincached=2 / maxconnections=10 / ping=1)
- **호출 경로**: ECS(admin/platform) → AWS Lambda `lifesync-onprem-customer-query` → urllib HTTP → 본 API
- **인증**: `/internal/*` 무인증 (VPN 내부 신뢰 모델). `/internal/deploy` 만 `X-Deploy-Token` 헤더
- **기준 일자**: 2026-05-18

---

## 1. 전체 라우트 (총 21개)

| # | Method | Path | 라운드 | 호출자 |
|---|---|---|---|---|
| 1 | GET  | `/health` | 기본 | (ALB/콘솔 헬스체크) |
| 2 | GET  | `/internal/customer/{global_id}` | 기존 | Lambda `get_profile` / `get_all` |
| 3 | GET  | `/internal/consent/{global_id}` | 기존 | Lambda `get_consent` / `get_all` |
| 4 | GET  | `/internal/identity/{source_customer_id}?domain=X` | 기존 | (계열사 매칭) |
| 5 | POST | `/internal/auth/login` | 기존 | Lambda `login` |
| 6 | POST | `/internal/auth/register` | 기존 | Lambda `register` |
| 7 | GET  | `/internal/pii/{global_id}` | 기존 | Lambda `get_pii` |
| 8 | GET  | `/internal/auth/user/{ls_user_id}` | 기존 | Lambda `get_user` |
| 9 | POST | `/internal/auth/consent` | 기존 | Lambda `save_consent` |
| 10 | POST | `/internal/deploy` | 기존 | 외부 webhook (`X-Deploy-Token` 인증) |
| 11 | POST | `/internal/match` | 기존 | (배치 매칭) |
| **12** | GET | **`/internal/profile/list-all?page=N&size=10000`** | 신규 | Lambda `list_profile_page` → analytics_aggregator |
| **13** | GET | **`/internal/count/master_customer?status=ACTIVE`** | 신규 | Lambda `count_master_customer` → admin |
| **14** | GET | **`/internal/count/users?status=ACTIVE`** | 신규 | Lambda `count_users` → admin |
| **15** | GET | **`/internal/count/users_consented`** | 신규 | Lambda `count_users_consented` → admin |
| **16** | GET | **`/internal/master_customer/{global_id}`** | 신규 | Lambda `get_master_customer` (예약) |
| **17** | GET | **`/internal/identity_map/{global_id}`** | 신규 | Lambda `get_identity_map` → admin user_detail |
| **18** | GET | **`/internal/health/vm/{vm_id}`** | 신규 | Lambda `vm_health` (예약) |
| **19** | GET | **`/internal/health/mysql`** | 신규 | Lambda `mysql_health` (예약) |
| **20** | GET | **`/internal/health/tokenization`** | 신규 | Lambda `tokenization_health` (예약) |
| **21** | GET | **`/internal/health/local-lab`** | 신규 | Lambda `local_lab_status` → admin ops |

---

## 2. 신규 10개 엔드포인트 상세

### 2.1 `GET /internal/profile/list-all` — analytics 배치용 페이지 조회

> 1M 행을 sync invoke 6MB 응답 제한에 맞추기 위해 page/size 페이지네이션.

**파라미터**

| 이름 | 타입 | 기본 | 검증 |
|---|---|---|---|
| `page` | int | 0 | ≥ 0 (밖이면 400) |
| `size` | int | 10000 | 1~50000 (밖이면 400) |

**SQL**

```sql
SELECT global_id, gender, age_band, region, income_grade, asset_grade
FROM customer_360_profile
ORDER BY global_id
LIMIT ? OFFSET (page * size)
```

**응답**

```json
{
  "page": 0,
  "size": 10000,
  "count": 10000,
  "items": [
    {"global_id":"G000000001","gender":"M","age_band":"40s","region":"SEOUL","income_grade":"HIGH","asset_grade":"HIGH"}
  ]
}
```

`count < size` 이면 마지막 페이지. `analytics_aggregator` 가 페이지 루프로 호출 (1M → 100회).

---

### 2.2 `GET /internal/count/master_customer?status=ACTIVE` — 통합 고객 수

**SQL**

```sql
SELECT COUNT(*) AS cnt FROM master_customer WHERE customer_status = ?
```

**응답**: `{"status": "ACTIVE", "count": 1000000}`
**용도**: admin P1 KPI "통합 고객 수"

### 2.3 `GET /internal/count/users?status=ACTIVE` — 플랫폼 가입자 수

**SQL**

```sql
SELECT COUNT(*) AS cnt FROM users WHERE user_status = ?
```

**응답**: `{"status": "ACTIVE", "count": 300000}`
**용도**: admin P1 KPI "플랫폼 가입자"

### 2.4 `GET /internal/count/users_consented` — 분석 대상 고객 수

> active 회원 중 1개 도메인 이상 현재 동의 상태(Y + revoke_dt IS NULL) 인 distinct count.

**SQL**

```sql
SELECT COUNT(DISTINCT u.ls_user_id) AS cnt
FROM users u JOIN consent c ON u.global_id = c.global_id
WHERE u.user_status = 'ACTIVE'
  AND c.consent_flag = 'Y'
  AND c.revoke_dt IS NULL
```

**응답**: `{"count": 60000}`
**용도**: admin P1 KPI "분석 대상 고객"

---

### 2.5 `GET /internal/master_customer/{global_id}` — 단건 조회

**SQL**

```sql
SELECT * FROM master_customer WHERE global_id = ?
```

**응답**: master_customer 한 행 (404 if missing)
**용도**: admin Customer 360 헤더 / reviewer 식별

### 2.6 `GET /internal/identity_map/{global_id}` — 계열사 매핑

**SQL**

```sql
SELECT domain, source_customer_id, created_dt
FROM customer_identity_map
WHERE global_id = ? AND active_flag = 'Y'
ORDER BY domain
```

**응답**

```json
{
  "global_id": "G000297409",
  "identities": [
    {"domain":"BANK","source_customer_id":"BNK-00000001","created_dt":"2023-01-15T10:00:00"},
    {"domain":"CARD","source_customer_id":"CRD-00000123","created_dt":"2023-03-22T11:00:00"}
  ]
}
```

**용도**: admin user_detail "계열사 매핑" 박스 (Lambda action `get_identity_map` 경유)

---

### 2.7 `GET /internal/health/vm/{vm_id}` — 단일 VM TCP liveness

**vm_id 매핑** (env override 가능)

| vm_id | host (기본) | port (기본) | env override |
|---|---|---|---|
| `ls-db` | 192.168.56.11 | 3306 | `VM_LS_DB_HOST` / `VM_LS_DB_PORT` |
| `ls-token` | 192.168.56.12 | 8000 | `VM_LS_TOKEN_HOST` / `VM_LS_TOKEN_PORT` |
| `ls-api` | 192.168.56.13 | 80 | `VM_LS_API_HOST` / `VM_LS_API_PORT` |

**체크**: `socket.create_connection((host, port), timeout=1.5)`

**응답**

```json
{
  "vm_id":  "ls-db",
  "host":   "192.168.56.11",
  "port":   3306,
  "status": "pass",
  "time":   "2026-05-18T03:00:00Z"
}
```

unknown vm_id → 404

### 2.8 `GET /internal/health/mysql` — local MySQL 8 테이블 존재 확인

**SQL**: `SHOW TABLES` → 8 테이블 (`users`, `master_customer`, `customer_pii_secure`, `customer_360_profile`, `customer_identity_map`, `consent`, `matching_audit_log`, `token_map`) 비교

**응답**

```json
{
  "status":  "pass",
  "time":    "2026-05-18T03:00:00Z",
  "tables":  ["consent","customer_360_profile","customer_identity_map","customer_pii_secure","master_customer","matching_audit_log","token_map","users"],
  "missing": []
}
```

- 8개 다 있으면 `pass`
- 일부 누락 `warn`
- DB 자체 실패 (connect fail 등) `fail` + `error` 필드

### 2.9 `GET /internal/health/tokenization` — Tokenization Service HTTP /health

**env**: `TOKENIZATION_HEALTH_URL` (기본 `http://192.168.56.12:8000/health`)
**체크**: `urllib.urlopen(url, timeout=2.0)` → 2xx 응답이면 pass

**응답**

```json
{
  "status":   "pass",
  "time":     "2026-05-18T03:00:00Z",
  "endpoint": "http://192.168.56.12:8000/health"
}
```

### 2.10 `GET /internal/health/local-lab` — 종합 헬스 (admin ops 페이지)

3 VM TCP + MySQL + Tokenization 결과를 한 응답으로 결합. RFC draft `api-health-check-06` 부분 호환.

**응답**

```json
{
  "environments": [
    {"env": "VirtualBox · ls-db",    "state": "Running", "note": "192.168.56.11:3306"},
    {"env": "VirtualBox · ls-token", "state": "Running", "note": "192.168.56.12:8000"},
    {"env": "VirtualBox · ls-api",   "state": "Running", "note": "192.168.56.13:80"}
  ],
  "checks": {
    "vm:ls-db":             [{"status":"pass","componentType":"system",    "observedValue":"192.168.56.11:3306","time":"..."}],
    "vm:ls-token":          [{"status":"pass","componentType":"system",    "observedValue":"192.168.56.12:8000","time":"..."}],
    "vm:ls-api":            [{"status":"pass","componentType":"system",    "observedValue":"192.168.56.13:80",  "time":"..."}],
    "service:mysql":        [{"status":"pass","componentType":"datastore", "observedValue":"8 tables",          "time":"..."}],
    "service:tokenization": [{"status":"pass","componentType":"component", "observedValue":"http://192.168.56.12:8000/health","time":"..."}]
  }
}
```

---

## 3. 새로 추가된 헬퍼

| 함수 | 시그니처 | 역할 |
|---|---|---|
| `_now_iso()` | → `str` | UTC ISO 8601 (`2026-05-18T03:00:00Z`) 시각 |
| `_tcp_check(host, port, timeout=1.5)` | → `bool` | socket.create_connection 단순 liveness |
| `_http_check(url, timeout=2.0)` | → `bool` | urllib.urlopen, 2xx OK |

---

## 4. 환경변수 전체

| Env | 기본값 | 설명 |
|---|---|---|
| `DEPLOY_TOKEN` | (필수) | `/internal/deploy` 인증 |
| `DB_HOST` / `DB_USER` / `DB_PASS` | (필수) | MySQL 접속 |
| `TOKEN_AES_KEY_B64` | (선택 — Secrets Manager fallback) | AES-256-GCM 키 (base64) |
| `DB_POOL_MIN` | `2` | pool warm 유지 connection 수 |
| `DB_POOL_MAX` | `10` | pool 최대 동시 connection |
| `DB_POOL_MAXIDLE` | `5` | pool idle 최대 보관 |
| `VM_LS_DB_HOST` | `192.168.56.11` | health/vm 매핑 |
| `VM_LS_DB_PORT` | `3306` | |
| `VM_LS_TOKEN_HOST` | `192.168.56.12` | |
| `VM_LS_TOKEN_PORT` | `8000` | |
| `VM_LS_API_HOST` | `192.168.56.13` | |
| `VM_LS_API_PORT` | `80` | |
| `TOKENIZATION_HEALTH_URL` | `http://192.168.56.12:8000/health` | health/tokenization 대상 |

---

## 5. Lambda action ↔ PrivateAPI endpoint 매핑 (18 action 전체)

| Lambda action | PrivateAPI | 호출자 |
|---|---|---|
| `login` | POST /internal/auth/login | (회원 로그인) |
| `register` | POST /internal/auth/register | (회원가입) |
| `get_user` | GET /internal/auth/user/{id} | platform `api_product_apply` |
| `get_consent` | GET /internal/consent/{gid} | admin / platform |
| `save_consent` | POST /internal/auth/consent | platform consent_save |
| `get_profile` | GET /internal/customer/{gid} | (get_all로 흡수) |
| `get_pii` | GET /internal/pii/{gid} | platform user PII |
| `get_all` | /customer + /consent 합성 | admin / platform |
| `local_lab_status` | GET /internal/health/local-lab | admin |
| `count_master_customer` | GET /internal/count/master_customer | admin |
| `count_users` | GET /internal/count/users | admin |
| `count_users_consented` | GET /internal/count/users_consented | admin |
| `get_master_customer` | GET /internal/master_customer/{gid} | (예약) |
| `get_identity_map` | GET /internal/identity_map/{gid} | admin user_detail |
| `vm_health` | GET /internal/health/vm/{vm_id} | (예약) |
| `mysql_health` | GET /internal/health/mysql | (예약) |
| `tokenization_health` | GET /internal/health/tokenization | (예약) |
| `list_profile_page` | GET /internal/profile/list-all | analytics_aggregator |

---

## 6. pip 의존성 (변경분)

`onprem-prod-repo/ansible/roles/private_api/tasks/main.yml` 의 `Install Python dependencies`:

```yaml
- fastapi
- uvicorn
- boto3
- pymysql
- cryptography
- DBUtils            # 신규 — connection pool
```

---

## 7. 재배포 절차

```bash
# Option A — 콘솔/SSH 로 ls-api 진입 후 직접 적용
cd /opt/private-api
sudo systemctl restart private-api

# Option B — ansible playbook 재실행 (DBUtils 등 신규 의존성 같이)
ansible-playbook -i hosts.yml site.yml

# Option C — webhook 트리거 (POST /internal/deploy)
curl -X POST -H "X-Deploy-Token: <TOKEN>" http://192.168.56.13/internal/deploy
```

배포 후 빠른 검증:

```bash
# 신규 엔드포인트 1개씩 호출 (무인증)
curl -s "http://192.168.56.13/internal/count/master_customer?status=ACTIVE" | jq .
curl -s "http://192.168.56.13/internal/count/users?status=ACTIVE"          | jq .
curl -s  "http://192.168.56.13/internal/count/users_consented"             | jq .
curl -s  "http://192.168.56.13/internal/health/mysql"                      | jq .
curl -s  "http://192.168.56.13/internal/health/tokenization"               | jq .
curl -s  "http://192.168.56.13/internal/health/local-lab"                  | jq .
curl -s  "http://192.168.56.13/internal/health/vm/ls-db"                   | jq .
curl -s  "http://192.168.56.13/internal/profile/list-all?page=0&size=5"    | jq .
curl -s  "http://192.168.56.13/internal/identity_map/G000297409"           | jq .
curl -s  "http://192.168.56.13/internal/master_customer/G000297409"        | jq .
```

---

## 8. 인증 / 보안 추가 검토 (운영 정책 시)

현재 무인증 + 평문 HTTP. 운영 정책상 강화 필요 시:

| 항목 | 옵션 |
|---|---|
| 헤더 인증 | `X-Internal-Token` (Tokenization service 패턴) — 모든 `/internal/*` 에 Depends |
| TLS | nginx 80 → 443 + Let's Encrypt 또는 사내 CA |
| 호출 제한 | nginx `limit_req_zone` 또는 FastAPI middleware |
| 감사 로깅 | matching_audit_log 패턴 확장 — request_id + endpoint + caller |

---

## 9. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-18 | 신규 10 엔드포인트 추가 (`/internal/count/*` 3, `/internal/master_customer/{gid}`, `/internal/identity_map/{gid}`, `/internal/health/*` 4, `/internal/profile/list-all`) + DBUtils pool 도입 + ls-vpngw 제거 (테스트용 미사용) |

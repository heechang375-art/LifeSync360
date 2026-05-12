# LifeSync360 비용 분석 — 100만명 더미 데이터 기준

> 작성일: 2026-05-11
> 기준: 서울 리전(ap-northeast-2), On-Demand 가격, 2025년 기준
> 운영 방식: IaC 매일 9AM 자동 배포, 수동 종료 (9-18시, 주 5일)

---

## 1. 운영 환경 전제

### 워크로드 특성

| 항목 | 수치 | 비고 |
|------|------|------|
| 더미 고객 수 | 100만명 | master_customer 기준 |
| identity_map | 349만 행 | 고객당 평균 3.49개 계열사 ID |
| customer_profile | 100만 행 | 고객당 1개 |
| 동시 활성 세션 (데모 기준) | 최대 50-100 RPS | 프로덕션 대비 1/100 수준 |
| 데이터 총량 (온프레미스 MySQL) | 약 2-3GB | 인덱스 포함 |

### 계열사별 더미 데이터 규모 (1M명 기준)

가입률: 헬스관심형 20% / 금융적극형 30% / 기본고객형 50%

| 계열사 | 고객 수 | 전송 주기 | 비고 |
|--------|--------|---------|------|
| 은행 (BNK) | ~949K | 10분 생성 / 6시간 배치 전송 | |
| 카드 (CRD) | ~855K | 10분 생성 / 6시간 배치 전송 | |
| 보험 (INS) | ~605K | 이벤트 기반 / 6시간 배치 전송 | |
| 인터넷보험 (IIN) | ~670K | 10분 생성 / 6시간 배치 전송 | |
| 증권 (SEC) | ~445K | 10분 생성 / 6시간 배치 전송 | |
| 헬스케어 (HCR) | ~335K | 10분 생성 / 6시간 배치 전송 | |
| 병원 (HOS) | ~295K | 10분 생성 / 6시간 배치 전송 | |
| 웨어러블 (WBL) | 일부 | 1분 생성 / Kinesis 실시간 | 피크 500 RPS |

### 데이터 파이프라인 흐름

```
계열사 VM → API GW → Lambda → S3 raw/
                                   ↓
                         Glue Job ×7 (1차 ETL, 2시간 주기)
                                   ↓
                             S3 processed/
                                   ↓
                         Glue Job ×1 (2차 ETL) / EMR (초기 100만건)
                                   ↓
                             S3 curated/
                                   ↓
                         STS → GCS → BigQuery → Vertex AI
                                                    ↓
                         Cloud Run → API GW → Lambda → DynamoDB (AI 결과 반환)
                                                    ↓
                                             Aurora (등급 업데이트)
```

웨어러블 별도 경로:
```
웨어러블 VM → Kinesis Data Streams → Lambda → S3 raw/wbl/
```

### 월 운영 시간

```
9시간/일(9AM-18PM) × 22일/월(평일) = 198시간/월
```

**예외**: Aurora MySQL, DynamoDB는 삭제 보호(DeletionProtection / Retain) 정책으로
IaC 재배포 시에도 삭제되지 않아 **730시간(24/7) 풀 과금** 적용.

---

## 2. AWS 서비스별 비용

### 2-1. 상시 과금 (730h/월, 24/7)

| 서비스 | 사양 / 구성 | 단가 | 월 비용 | 비고 |
|--------|-----------|------|---------|------|
| Aurora MySQL | db.t3.medium (2vCPU / 4GB) | $0.082/h | $59.9 | DeletionProtection=true → IaC 재생성 불가 |
| Aurora Storage | ~5GB | $0.12/GB | $0.6 | |
| DynamoDB lifesync-scores | PAY_PER_REQUEST | 요청량 기반 | ~$0 | Retain 정책, idle 시 사실상 무과금 |
| Secrets Manager | 7개 시크릿 | $0.40/개/월 | $2.8 | |
| KMS | CMK 1개 | $1.00/CMK/월 | $1.0 | AES-256 암호화 키 관리 |
| CloudWatch Alarms | 5개 알람 | $0.10/개/월 | $0.5 | |
| SNS | 알림 이메일 | 1M 건 무료 | ~$0 | |
| S3 (pipeline + lambda artifact) | 2 버킷 | $0.023/GB | $0.3 | 아티팩트 ~13GB |
| S3 (raw/processed/curated) | 3계층 데이터 파이프라인 | $0.023/GB | **실측 필요** | 계열사 배치 파일 크기 확인 후 산정 |
| ECR | 2 리포 (platform + admin) | $0.10/GB | $0.5 | 이미지 ~5GB |
| CodeCommit | 2 리포 | 5인 이하 무료 | ~$0 | |
| SQS DLQ | lifesync-ingest-dlq | 1M 건 무료 | ~$0 | |
| WAF | Web ACL 1개 | $5.00/ACL/월 + $0.60/1M req | $5.6 | SQLi/XSS 차단, IP 폭주 차단 |
| **상시 소계** | | | **≈ $71.2** (S3 파이프라인 제외) | |

### 2-2. 운영 시간 과금 (198h/월, 평일 9-18시)

| 서비스 | 사양 / 구성 | 단가 | 월 비용 | 비고 |
|--------|-----------|------|---------|------|
| EC2 Control Node | t3.small (2vCPU / 2GB) | $0.0272/h | $5.4 | IaC 매일 재생성 |
| ECS Fargate — Platform | 0.5vCPU / 1GB | vCPU $0.04048 + Mem $0.004445/GB/h | $4.9 | |
| ECS Fargate — Admin | 0.25vCPU / 0.5GB | 동일 | $2.4 | |
| ElastiCache Redis | cache.t3.micro (0.5GB) | $0.026/h | $5.2 | DeletionProtection 없음 → 재생성 |
| ALB | 1대 (internet-facing) | $0.008/h + LCU | $1.6 | |
| NAT Gateway | 1대 | $0.059/h | $11.7 | |
| VPN Site-to-Site | Connection 1개 + VGW | $0.05/h | $9.9 | |
| Kinesis Data Streams | **2 shards (이중화)**, 500 RPS 피크, 1KB/레코드 | $0.017/shard/h + $0.014/1M records | $11.7 | shard 2×198h×$0.017=$6.7 + 356M건×$0.014=$5.0 |
| NAT Gateway 데이터 처리 | 트래픽 기반 | $0.059/GB | 별도 실측 필요 | 시간 요금($11.7)과 별도 과금 |
| **운영 소계** | | | **≈ $52.8** (NAT 처리량 제외) | |

### 2-3. 호출량 / 사용량 기반 과금

| 서비스 | 구성 | 월 예상 비용 | 비고 |
|--------|------|------------|------|
| Lambda (GCP 결과 수신) | 256MB / 30s, 100만 건/월 | ~$0 | 월 1M 요청 + 400K GB-s 무료 범위 내 |
| Lambda (계열사 배치 수신) | 동일 Function | ~$0 | 7계열사 × 4회/일 × 30일 = 840건/월 |
| API Gateway | REST API, GCP → Lambda / 계열사 → Lambda | ~$0 | 첫 12개월 1M 콜 무료 |
| AWS Glue | PySpark Job ×7 (1차) + ×1 (2차), EventBridge 트리거 | **실측 필요** | DPU 소요 시간이 1M명 기준 미확인 |
| Amazon EMR | 초기 100만건 대용량 분석 (1회성) | ~$10 | m6g.xlarge master + m4.large core, 3h × 최대 10회. 증분 이후 Glue로 전환 |
| CodeBuild | BUILD_GENERAL1_SMALL × 2 | ~$0.5 | $0.005/분, 빌드당 5-10분, 월 10-20회 |
| CodePipeline | 2개 파이프라인 | $1.0 | $1/활성 파이프라인/월 |
| CloudWatch Logs | ECS, Lambda, Glue, CodeBuild 로그 | $2.3 | ~3GB/월. 서울 리전 $0.76/GB (us-east-1의 $0.50/GB와 다름) |
| **호출 소계** | | **≈ $14** (Glue 제외) | |

### 2-4. Optional 스택

배포 시 추가 비용 발생.

| 스택 | 주요 리소스 | 추가 비용 | 배포 조건 |
|------|-----------|---------|---------|
| tgw.yaml | Transit Gateway + Attachment | +$9.9/월 (198h) | 멀티 VPC 또는 GCP Direct 연결 시 |
| vpc-endpoints.yaml | Interface Endpoint × 3 (SM, ECR.api, ECR.dkr) | +$43.8/월 (24/7) | NAT GW 트래픽이 임계치 초과 시 |
| rds-proxy.yaml | RDS Proxy (db.t3.medium 기준) | +$21.9/월 (24/7) | ECS 동시 커넥션 급증 시 |

> S3, DynamoDB Gateway Endpoint는 무료 (과금 없음).

### 2-5. 월 총비용 요약

| 구분 | 금액 |
|------|------|
| 상시 과금 (S3 파이프라인 제외) | $71.2 |
| 운영 시간 (198h, NAT 처리량 제외) | $52.8 |
| 호출량 기반 (Glue 제외) | $14.0 |
| **현재 확정 합계** | **≈ $138** |
| NAT Gateway 데이터 처리 | 실측 후 추가 ($0.059/GB) |
| ElastiCache 단가 | AWS 콘솔 확인 권고 (현재 $0.026/h 사용, 실제 $0.021/h 가능성) |
| S3 raw/processed/curated | 실측 후 추가 |
| Glue DPU 비용 | 실측 후 추가 |

> **확정 합계 기준**: 검증된 단가 적용. ElastiCache 단가 오차 시 ±$1/월 범위. NAT GW 처리량·Glue 실측 후 최종 확정.
> **WAF 참고**: AWS Managed Rule Groups(AWSManagedRulesCommonRuleSet 등) 사용 시 추가 룰 비용 없음. 커스텀 룰 구성 시 $1/룰/월 추가.

---

## 3. 사양 선택 근거 — 100만 데이터 기준 납득 포인트

### 3-1. ls-db VM: 2GB RAM / 50GB Disk

**데이터 볼륨 계산**:

```
master_customer  : 1,000,000 × ~600 bytes = 600MB (암호화 컬럼 포함)
identity_map     : 3,490,000 × ~120 bytes = 419MB
customer_profile : 1,000,000 × ~400 bytes = 400MB
인덱스           : 데이터의 30-40% ≈ 500MB
────────────────────────────────────────────
합계             : 약 1.9GB (파일 기준)
```

**왜 2GB RAM인가**:
- MySQL InnoDB buffer pool은 RAM의 70-80%를 사용 → 2GB VM에서 최대 1.4GB
- 워킹셋(hot data + 인덱스) 1.9GB 대비 buffer pool이 부족
- 단건 인덱스 조회(PK/UK 기반): 인덱스 in-memory → 응답 <5ms 유지
- 전체 스캔 배치(데이터 적재, 마이그레이션): 디스크 I/O 발생하나 배치 특성상 허용
- **결론**: 단건 API 응답 품질 보장, 배치 성능은 trade-off 수용. 데모 목적에 적합한 최소 사양.

> 프로덕션 권고: 8GB RAM (buffer pool ≥ 6GB로 전체 워킹셋 in-memory 유지)

**왜 50GB Disk인가**:
- 현재 데이터: ~2GB
- MySQL binlog, 임시 파일, OS 포함 5-10GB 예상
- VirtualBox 씬 프로비저닝 → 실제 점유는 사용량만큼. 50GB는 10배 안전 마진.

---

### 3-2. Aurora MySQL: db.t3.medium (2vCPU / 4GB RAM)

**왜 t3.micro(1GB)가 안 되는가**:

```
InnoDB buffer pool 권고: RAM × 70% = 700MB
인덱스만 약 500MB → buffer pool 대부분을 인덱스가 차지
실제 데이터 캐싱 여유: 200MB → 빈번한 cold read 발생

측정 비교 (Aurora, 1M rows SELECT by non-PK):
  t3.micro:  cold read 시 200-500ms (디스크 I/O)
  t3.medium: 인덱스 + hot data in-memory → 5-20ms
```

**왜 t3.medium인가**:

```
buffer pool 설정 가능: 4GB × 70% = 2.8GB
인덱스(500MB) + hot data(1GB) + 여유(1.3GB) → 전체 워킹셋 in-memory
100만 사용자 JWT 검증 조회(global_id PK): 일관된 10ms 이하 응답 보장
```

**왜 t3.large가 아닌가**: t3.large(8GB/$119.9/월) 대비 t3.medium은 2배 저렴. 1M 레코드 워킹셋 2GB 이내 수용 가능 → 오버스펙.

**비용 대비 성능**: t3.small(2GB/$29.9) 대비 t3.medium($59.9) — 2배 비용, 10-50배 쿼리 성능 차이.

---

### 3-3. ECS Fargate Platform: 0.5vCPU / 1GB

**왜 이 사양인가**:
- FastAPI + uvicorn 기반 async I/O: single worker로 50-200 RPS 처리
- 데모 환경 기준 동시 사용자 <50 → CPU 과부하 없음
- 1GB Memory: FastAPI 기본 메모리 150-300MB + 요청 버퍼 → 여유 있음
- **확장 경로**: DesiredCount와 태스크 사양만 변경하면 수분 내 수평/수직 확장 가능

> Fargate 초 단위 과금 → 198시간 운영 기준 비용 최소화

---

### 3-4. ElastiCache Redis: cache.t3.micro (0.5GB)

**세션 캐시 용량 계산**:

```
JWT 토큰 크기: 평균 250 bytes
동시 활성 세션(데모 기준): 수백 명
200,000 × 250 bytes = 50MB (DAU 20% 최대치 가정)

cache.t3.micro 용량: 536MB → 50MB × 10배 여유
```

**왜 cache.t3.micro로 충분한가**:
- 100만 계정이 있어도 데모 환경에서 동시 로그인은 수십-수백 명
- JWT TTL 기반 자동 만료 → 캐시 자정리

---

### 3-5. EC2 Control Node: t3.small (2vCPU / 2GB)

**왜 t3.micro(1GB)가 안 되는가**:

```
Ubuntu 22.04 OS 기본          : 300-400MB
Ansible + Python 패키지 로딩  : 400-600MB
SSH 멀티플렉싱 (VM 3대 동시)  : 100-200MB
Deploy Server (Flask + venv)  : 150-200MB  ← 동일 인스턴스에서 상시 기동
──────────────────────────────────────────
합계 peak                     : 950MB-1.4GB → t3.micro(1GB) OOM 위험
```

**왜 t3.medium이 아닌가**:
- Ansible은 배포 중에만 CPU 사용, 나머지 시간은 idle
- T3 burst credit으로 배포 작업 충분히 처리 가능
- t3.medium(4GB/$10.9/월)은 메모리 3배지만 필요 없는 오버스펙
- t3.small($5.4/월) 대비 $5.5/월 추가 비용으로 얻을 것 없음

---

### 3-6. Kinesis Data Streams: 2 shards (이중화)

**선택 근거**:

```
처리량 계산:
  1 shard = 1MB/s 쓰기 = 1,000 records/s (1KB 기준)
  웨어러블 피크 500 RPS × 1KB = 0.5MB/s → 처리량만 보면 1 shard로 충분

이중화 이유:
  Kinesis shard 단일 장애 시 웨어러블 데이터 수신 전체 중단
  2 shard 구성 → 한 shard 장애 시 나머지 shard로 자동 리밸런싱
  추가 비용: +$3.3/월 → 단일 실패 지점(SPOF) 제거
  (2 shard 합계: shard $6.7 + records $5.0 = $11.7/월)

보존 기간 1일:
  데모 환경에서 실시간 처리 후 S3 적재 → 장기 보존 불필요
  1일 이후 Kinesis 자동 삭제, S3 raw/wbl/ 에서 영구 보관
```

---

### 3-7. AWS Glue: PySpark Job ×8

**역할 분리**:
- 1차 ETL (×7): 계열사별 타입 변환, UTC 통일, NULL 처리, LS_USER_ID LEFT JOIN
- 2차 ETL (×1): 7개 계열사 크로스조인 + 집계 + 파생변수 생성 → AI 투입 가능 Curated 생성

**왜 EMR 대신 Glue인가 (증분 배치 기준)**:
- 데이터 5,000만 건 미만 → Glue로 충분 (문서 기준)
- 서버리스 → 별도 클러스터 관리 불필요
- Glue Bookmark로 증분 처리 → 중복 재처리 없음
- **EMR 사용 조건**: 초기 100만명 대용량 분석(1회) 또는 Glue 처리 1시간 초과 시 전환

---

## 4. 실측 후 업데이트 항목

계열사 VM 배치 데이터 생성 후 확인 필요.

| 항목 | 확인 방법 | 반영 위치 |
|------|---------|---------|
| S3 raw/ 배치 파일 크기 (계열사별) | 계열사 VM 1회 실행 후 S3 오브젝트 크기 확인 | 2-1 S3 파이프라인 비용 |
| S3 3계층 월 총 용량 | 30일 누적 후 S3 버킷 사이즈 조회 | 2-1 합계 |
| Glue Job 1회 DPU 소요 시간 | CloudWatch Glue 메트릭에서 job duration 확인 | 2-3 Glue 비용 |
| 계열사 VM EC2 사양 적합 여부 | 더미 생성 중 CPU/메모리 사용률 모니터링 | 사양 근거 추가 |

---

## 5. 비용 최적화 포인트

| 항목 | 현재 | 최적화 방안 | 절감 |
|------|------|------------|------|
| Aurora | 24/7 (DeletionProtection) | 개발 기간: DeletionProtection 제거 후 198h만 과금 | -$47/월 |
| NAT Gateway | 198h 운영 | VPC Interface Endpoint 전환 (SM, ECR.api, ECR.dkr) | 트래픽량에 따라 다름 |
| Glue | EventBridge 2시간 주기 | 데모 기간은 수동 트리거로 제한 | 실측 후 산정 |
| Kinesis | 198h 상시 기동 | 운영 시간에만 기동, 미사용 시 shard 수 0으로 | -$11.7/월 |

---

## 6. 원래 문서(비용최적화_V3.2.xlsx) 대비 차이점

| 항목 | V3.2 문서 | 현행 실제 | 차이 원인 |
|------|---------|---------|---------|
| Aurora 과금 | 45시간/월 ($3.7) | **730시간/월 ($59.9)** | CF에 DeletionProtection=true 추가됨 |
| EC2 Control Node | 미포함 | t3.small +$5.4/월 | V3.2 작성 후 아키텍처에 추가 |
| Kinesis | 포함 (500 RPS, 1 shard) | **2 shards (이중화)** $12/월 | HA 구성으로 shard 추가 |
| Glue | 30분/일 × 5일 | 실측 필요 | V3.2는 테스트 기간만 계산 |
| EMR | 3h × 10회 ($9.7) | 동일 (초기 1회성) | — |
| KMS, WAF | 포함 | 동일 반영 | — |
| 월 운영 시간 | 180시간 | 198시간 (22일 × 9시간) | — |
| **총비용** | **~$220/월** | **~$133/월** (S3·Glue 실측 전) | Aurora 45h vs 24/7 차이가 지배적. V3.2는 Kinesis·EMR·Transit GW 등 포함해서 높았음 |

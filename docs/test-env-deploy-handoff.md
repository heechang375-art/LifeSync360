# 테스트 환경 배포 핸드오프

> 작성일: 2026-05-16
> 대상: lifesync admin + platform 시연용 AWS 계정 (별도 root 계정)
> 목적: ECS에서 admin/platform 두 화면이 Aurora + DynamoDB 데이터로 정상 동작 확인

---

## 1. 현재 상태 요약

### 1-1. 토큰 에러 근본 원인 (해결됨)

이전 ECS task 부팅 시 "토큰 에러"의 원인 3가지를 IaC 측에서 fix:

| 원인 | Fix |
|---|---|
| ExecutionRole에 `kms:Decrypt` 누락 (SSM SecureString 복호화 실패) | `21-lifesync-ecs-existing-vpc.yaml` ExecutionRole inline policy 추가 (Condition: `kms:ViaService=ssm.${REGION}.amazonaws.com`) |
| SSM/KMS VPC Endpoint 미배포 (Private subnet에서 SSM API 호출 timeout) | `01b-lifesync-vpc-endpoints.yaml` 에 KMS endpoint 추가 |
| `taskdef.json` Role ARN 이 자동 hash 이름 참조 (재배포 시 깨짐) → admin은 존재하지 않는 Role 가리킴 | 21 yaml에 RoleName 명시: `lifesync-dev-EcsTaskExecutionRole`, `lifesync-dev-EcsTaskRole` / taskdef.json 도 동일 이름으로 정정 |
| ExecutionRole에 admin/aurora/redis secrets 권한 없음 | inline policy에 `secretsmanager:GetSecretValue` + Secrets Manager용 `kms:Decrypt` 추가 |
| TaskRole에 `lambda:InvokeFunction` (onprem-customer-query) 누락 | inline policy `InvokeOnpremQueryLambda` 추가 |
| TaskRole에 DynamoDB Get/Scan/Query 누락 | inline policy `DynamoDBTableReadWrite` 추가 |

### 1-2. 테스트 환경 — 시연 무관 stack 비활성

| Stack | 상태 | 비활성 사유 |
|---|---|---|
| ❌ 03-route53 | skip | 도메인 없음 |
| ❌ 04-transitgw | skip | 멀티클라우드 안 씀 |
| ❌ 05-vpn | skip | 동일 |
| ❌ 08b-service-db | skip | SQL assets 안 씀 |
| ❌ 09-streaming-api-lambda | skip | Wearable Kinesis 안 씀 |
| ❌ 10-data-processing | skip | Glue/EMR 안 씀 |
| ❌ 11-observability | skip | CloudWatch dashboard 안 씀 |
| ❌ 12-ec2 (Wearable/Group VM) | skip | 시연에 불필요 |
| ❌ 14a/14b/14c (Ansible) | skip | 사용 안 함 |
| ❌ 22-identity-enricher | skip | Lambda 안 씀 |
| ❌ Wearable VPC | skip | `DEPLOY_WEARABLE_VPC=false` |

### 1-3. admin UI 5→4메뉴 + PPTX 도형 정합

| 메뉴 | URL | 데이터 소스 (USE_MOCK=false 시) |
|---|---|---|
| Executive Dashboard | `/dashboard` | mockup_data (Aurora COUNT 대체 가능) |
| Customer 360 | `/users`, `/users/<gid>` | DynamoDB scan + onprem Lambda + Aurora |
| AI 추천 | `/ai` | Aurora customer_recommend_history GROUP BY + DynamoDB |
| 운영 모니터링 | `/ops` | boto3 ping (RDS/DynamoDB/ElastiCache/ECS/ALB/S3 describe-* + TGW/VPN/Glue) |

---

## 2. Secrets Manager — 임의 값으로 생성 완료 (2026-05-16)

테스트 환경이라 임의 값으로 미리 생성. **AWS 계정 732264765472, ap-northeast-2**에 생성됨.

ECS task 가 secret fetch 시 ExecutionRole 의 inline policy `SecretsManagerForAdminAndAurora` 가 다음 패턴 매칭:
```
arn:aws:secretsmanager:ap-northeast-2:732264765472:secret:lifesync/aurora-*
arn:aws:secretsmanager:ap-northeast-2:732264765472:secret:lifesync/admin-*
```

Secrets Manager 의 secret 이름은 random suffix(`-XxXxXx`) 자동 부여 → `lifesync/aurora-*` 패턴 매칭됨.

### 2-1. `lifesync/aurora` ✅ 생성 완료

**ARN**: `arn:aws:secretsmanager:ap-northeast-2:732264765472:secret:lifesync/aurora-zMLeSs`

| Key | 현재 값 | 비고 |
|---|---|---|
| `host` | `PLACEHOLDER-UPDATE-AFTER-08-DEPLOY` | **08-database 배포 후 Aurora writer endpoint 로 update 필요** |
| `user` | `admin` | Aurora 생성 시 동일 username 사용 |
| `password` | (Secrets Manager 안 — git 노출 X) | 32자 hex random. 08 deploy 시 동일 password 사용 |
| `port` | `3306` | |
| `dbname` | `lifesync360` | |

**값 확인**:
```bash
aws secretsmanager get-secret-value --secret-id lifesync/aurora --region ap-northeast-2 --query SecretString --output text | jq .
```

**08-database 배포 후 host update 명령**:
```bash
AURORA_HOST=$(aws rds describe-db-clusters --region ap-northeast-2 \
  --query "DBClusters[?contains(DBClusterIdentifier,'lifesync')].Endpoint | [0]" --output text)
PASS=$(aws secretsmanager get-secret-value --secret-id lifesync/aurora --region ap-northeast-2 \
  --query SecretString --output text | jq -r .password)
aws secretsmanager update-secret --secret-id lifesync/aurora --region ap-northeast-2 \
  --secret-string "{\"host\":\"$AURORA_HOST\",\"user\":\"admin\",\"password\":\"$PASS\",\"port\":\"3306\",\"dbname\":\"lifesync360\"}"
```

### 2-2. `lifesync/admin` ✅ 생성 완료

**ARN**: `arn:aws:secretsmanager:ap-northeast-2:732264765472:secret:lifesync/admin-ek37no`

| Key | 현재 값 | 사용처 |
|---|---|---|
| `username` | `admin` | admin 콘솔 로그인 ID (taskdef `ADMIN_USER`) |
| `password` | (Secrets Manager 안 — git 노출 X) | admin 콘솔 로그인 비번 (taskdef `ADMIN_PASSWORD`) |
| `secret_key` | (Secrets Manager 안 — git 노출 X) | Flask session 암호화 (taskdef `SECRET_KEY`) |

**값 확인**:
```bash
aws secretsmanager get-secret-value --secret-id lifesync/admin --region ap-northeast-2 --query SecretString --output text | jq .
```

### 2-3. ~~`lifesync/redis`~~ (skip — 테스트 환경에서 안 씀)

platform 의 `rec:{global_id}` 캐시 조회는 cache miss 처리되어 Aurora fallback 으로 동작.

### 2-4. JWT Signing Secret (자동 생성 — `21-lifesync-ecs-existing-vpc.yaml` 의 `JwtSigningSecret` Resource)

```yaml
JwtSigningSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: lifesync-dev-ecs-jwt-signing
    GenerateSecretString:
      GenerateStringKey: jwt
      PasswordLength: 64
```

→ 21 stack 배포 시 자동 생성. 수동 입력 불필요.
→ `/lifesync360/jwt-secret` SSM Parameter 가 secret 의 `jwt` 키를 참조.

---

## 3. SSM Parameter Store — 자동 생성 / 수동 확인

### 3-1. 자동 (21 stack)
- `/lifesync360/jwt-secret` — JwtSigningSecret 의 `jwt` 값 (SecureString)
  - lifesync360-platform taskdef의 `JWT_SECRET` 환경변수가 이걸 참조

### 3-2. CodePipeline 측 (15/17/18/19 stack)
- `/lifesync360/ecr-uri` (platform)
- `/lifesync360/ecr-uri-admin` (admin) — admin buildspec.yml 의 `parameter-store` 에서 fetch
  - 15 stack 의 ECR repo 생성 후 수동 또는 19 stack 자동 입력 (cicd-service-platform 측)

```bash
# 07-ecr stack 배포 후 ECR URI 확인하고 SSM에 등록
aws ssm put-parameter \
  --name /lifesync360/ecr-uri-admin \
  --value <ECR repo URI> \
  --type String \
  --region ap-northeast-2 --overwrite
```

---

## 4. GitHub Secrets / 사전 작업

### 4-1. GitHub Secrets (테스트 root 계정 키)

| Secret | 설명 |
|---|---|
| `AWS_ACCESS_KEY_ID` | 테스트 root 계정 IAM access key (20자) |
| `AWS_SECRET_ACCESS_KEY` | 테스트 root 계정 secret key (40자) |

→ `.github/workflows/platform.yml` 의 `mirror-to-codecommit` job 이 이걸로 GitHub → CodeCommit 미러링.
→ 현재 `if: false` 로 비활성. GitHub Secrets 등록 후 `if: github.ref == 'refs/heads/main'` 으로 활성.

### 4-2. AWS CLI 로컬 환경

```bash
# 테스트 root 계정 profile 또는 default
aws configure
# AWS Access Key ID: ...
# AWS Secret Access Key: ...
# Default region: ap-northeast-2
# Default output format: json
```

### 4-3. params 파일 확인

```bash
cd Aws_iac/Aws_iac
cat params/common.env       # PROJECT_NAME=lifesync, ENVIRONMENT=dev, REGION=ap-northeast-2
cat params/network.env      # DEPLOY_WEARABLE_VPC=false 확인
cat params/compute.env      # DEPLOY_EC2_STACK=false 확인
cat params/data.env         # DEPLOY_DATA_LAMBDA/PROCESSING/OBSERVABILITY=false 확인
cat params/cicd.env         # admin/platform 만 활성 확인
cat params/cicd-service-platform.env   # ENABLE_ADMIN_SERVICE_PLATFORM_PIPELINE=true 확인
```

---

## 5. 배포 순서

### 5-1. 한 번에 (권장)

```bash
cd Aws_iac/Aws_iac
bash scripts/infra/deploy.sh
```

순서:
```
01-network → 01b-vpc-endpoints → 02-security
→ 06-s3 → 07-ecr → 08-database (Aurora + DynamoDB + ElastiCache)
→ 09 SKIP → 10 SKIP → 11 SKIP → 12 SKIP
→ 21-lifesync-ecs-existing-vpc (ECS cluster + ALB + ExecutionRole + TaskRole)
→ 15-cicd (CodeCommit repos: lifesync-lifesync-service + lifesync-lifesync-service-admin)
→ 17-cicd-iam (CodePipeline + CodeBuild role)
→ 18-cicd-pipelines (Platform pipeline, 5개 비활성)
→ 19-cicd-service-platform (Platform + Admin pipeline 두 개)
```

### 5-2. 단계별 (디버깅 시)

```bash
bash scripts/infra/deploy-01-network-and-core.sh   # 01 → 01b → 02
bash scripts/infra/deploy-08-database-only.sh
bash scripts/infra/deploy-ecs-existing-lifesync-vpc.sh  # 21
bash scripts/pipelines/core/deploy-cicd-only.sh    # 15 → 17 → 18
bash scripts/pipelines/core/deploy-cicd-service-platform-only.sh  # 19
```

---

## 6. 배포 후 — 시연 검증 흐름

### 6-1. ECS task 부팅 확인

```bash
aws ecs describe-services \
  --cluster lifesync-service-ecs \
  --services lifesync-dev-21-lifesync-ecs-existing-vpc-v4-svc \
  --region ap-northeast-2 \
  --query 'services[0].{status:status,desiredCount:desiredCount,runningCount:runningCount}'

# admin service 도 동일하게
```

### 6-2. 토큰 에러 발생 시 진단

```bash
# 최근 STOPPED task 의 stoppedReason 확인
TASK_ARN=$(aws ecs list-tasks --cluster lifesync-service-ecs --desired-status STOPPED \
  --region ap-northeast-2 --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster lifesync-service-ecs --tasks $TASK_ARN --region ap-northeast-2 \
  --query 'tasks[0].{reason:stoppedReason,containers:containers[*].{name:name,reason:reason}}'
```

체크 포인트:
- `ResourceInitializationError: unable to pull secrets...` → ExecutionRole 권한 부족
- `An error occurred (AccessDeniedException)... kms:Decrypt` → KMS 권한 부족
- `Unable to assume role...` → Role 이름 불일치 (taskdef.json vs IAM)
- `secretsmanager:GetSecretValue ... not authorized` → secret ARN 패턴 매칭 안 됨

### 6-3. CodePipeline 트리거

1. CodeCommit `lifesync-lifesync-service` repo 에 platform 코드 push
2. CodeCommit `lifesync-lifesync-service-admin` repo 에 admin 코드 push (별 branch 사용 시 19 yaml `AdminCodeCommitBranch` 값 변경)
3. CodePipeline 콘솔에서 진행 상황 모니터링
4. ECS service 재배포 자동 진행 (rolling update)

### 6-4. ALB 접속 확인

```bash
# ALB DNS 확인
aws elbv2 describe-load-balancers --region ap-northeast-2 \
  --query 'LoadBalancers[].DNSName'

# 브라우저 접속:
# https://<ALB DNS>/             → platform (lifesync360) 화면
# https://<ALB DNS>:5001/        → admin 화면 (login: admin / lifesync/admin secret 의 password)
```

(실제로는 ALB Listener Rule 로 host/path 기반 분기. admin 은 별 path 또는 별 ALB.)

### 6-5. 화면 데이터 정상 확인

| 화면 | 확인 항목 |
|---|---|
| admin `/dashboard` | 총 고객 수 / 추천 이력 수 (Aurora) · AWS 상태 카드 6개 (boto3 ping) |
| admin `/users?q=G001` | 검색 시 단일 고객 카드 (DynamoDB + onprem Lambda) |
| admin `/ai` | 추천 TOP10 (Aurora) · 점수 분포 (DynamoDB scan) |
| admin `/ops` | TGW/VPN/VPC 상태 (boto3) · Wearable 메트릭 (mock) |
| platform `/` | 추천 상품 리스트 (Redis cache → Aurora fallback) |
| platform `/api/me` | JWT 발급 → 등급/이름 표시 |

---

## 7. 변경된 파일 리스트

### 7-1. main repo (heechang375-art/lifesync360-platform) — push 완료

```
admin-platform/app.py                       # boto3 ping + USE_MOCK 분기 + 라우트
admin-platform/mockup_data.py               # PPTX slide 1~4 도형 의도 dict
admin-platform/static/css/admin.css         # 공백 최소화
admin-platform/taskdef.json                 # Role ARN 정정
admin-platform/templates/base.html          # 4메뉴 사이드바
admin-platform/templates/dashboard.html     # PPTX slide1 도형 의도
admin-platform/templates/users.html         # PPTX slide2
admin-platform/templates/user_detail.html   # 360 요약
admin-platform/templates/ai.html            # PPTX slide3 4×2 그리드
admin-platform/templates/ops.html           # PPTX slide4 그리드
admin-platform/templates/data_integrity.html  # 삭제
lifesync360-platform/taskdef.json           # Role ARN 정정 (hash 제거)
docs/iac-handoff-permissions-addon.md       # §7 추가
docs/test-env-deploy-handoff.md             # (이 문서 — 신규)
통합_문서1_매핑추가.xlsx                    # 15 API 행 매핑 갱신
```

### 7-2. Aws_iac (local-only, remote 없음) — 동기화 별 처리 필요

```
templates/21-lifesync-ecs-existing-vpc.yaml  # RoleName + secrets/Lambda/DynamoDB 권한
scripts/infra/deploy.sh                       # 09/10/11 skip 조건
params/network.env                            # DEPLOY_WEARABLE_VPC=false
params/compute.env                            # DEPLOY_EC2_STACK=false
params/data.env                               # DATA_LAMBDA/PROCESSING/OBSERVABILITY=false
params/cicd.env                               # Wearable/Group/Data/Legacy 5개 비활성
params/cicd-service-platform.env              # admin pipeline 활성 (신규)
```

---

## 8. 알려진 한계

- **GitHub → CodeCommit 미러링**: `.github/workflows/platform.yml` 의 `if: false` 로 비활성. GitHub Secrets 등록 후 활성화 필요.
- **GCP 측 (BigQuery / Vertex AI)**: admin 코드에 stub 함수 있지만 SDK 미연동. mock 데이터로만 동작.
- **Redis 캐시 사전 warm**: V3.7 아키텍처는 04:40 Lambda Recommendation Engine 이 Redis warm 하는 구조. 현재 09 stack skip 했으므로 platform의 `/api/recommendations` 는 cache miss → Aurora fallback 만 동작.
- **Lambda InvokeFunction (onprem-customer-query)**: TaskRole 권한은 추가했지만 실 Lambda 함수 자체는 별도 stack (`lambda/onprem_customer_query/`)에서 배포 필요. 안 배포 시 admin 의 `_call_onprem` 호출 실패 (단, 기본값 처리로 빈 응답 반환).

---

## 9. 다음 단계 (시연 이후)

- [x] ~~Secrets Manager 에 실 secret 값 입력~~ — 임의 값으로 생성 완료 (2026-05-16)
- [ ] `Aws_iac/` IaC 변경 사항 적용 (local-only repo, 별도 동기화)
- [ ] `bash scripts/infra/deploy.sh` 실행 → 01~21 stack 배포
- [ ] 08-database 배포 후 `lifesync/aurora` secret 의 host 값 update (실 Aurora endpoint)
- [ ] CodeCommit 에 코드 push → CodePipeline 트리거 확인
- [ ] ALB 접속 → 화면 정상 확인
- [ ] admin USE_MOCK=false 동작 검증 (Aurora + DynamoDB 실 데이터)
- [ ] GitHub Secrets 등록 → `mirror-to-codecommit` 활성화 (`.github/workflows/platform.yml` `if: false` → `if: github.ref == 'refs/heads/main'`)
- [ ] 시연 끝나면 cleanup 스크립트 실행 (`scripts/cleanup-lifesync-alive-stacks.sh`)

---

## 10. 임의 생성 값 — 별 채널로 전달 (git 미노출)

> 테스트 환경 한정. password 평문은 Secrets Manager 안에만 존재 (git 노출 X).
> 운영 환경에서는 강력한 password 사용 + Secrets Manager 자동 rotation 권장.

### 값 가져오기

```bash
# Aurora 정보 (host/user/password/port/dbname)
aws secretsmanager get-secret-value --secret-id lifesync/aurora --region ap-northeast-2 --query SecretString --output text | jq .

# Admin 로그인 정보 (username/password/secret_key)
aws secretsmanager get-secret-value --secret-id lifesync/admin --region ap-northeast-2 --query SecretString --output text | jq .
```

### 08-database 배포 시 동일 password 사용

```bash
# Secrets Manager 에서 가져온 password 를 변수로
AURORA_PASS=$(aws secretsmanager get-secret-value --secret-id lifesync/aurora --region ap-northeast-2 --query SecretString --output text | jq -r .password)

# 08-database 배포 시 명시 (ManageMasterUserPassword=false 일 때)
aws cloudformation deploy --template-file templates/08-database.yaml \
  --parameter-overrides MasterUserPassword=$AURORA_PASS MasterUsername=admin \
  ...
```

또는 08 stack 이 `ManageMasterUserPassword: true` 면 AWS 가 자동으로 새 password 생성 + Aurora MasterUserSecret 에 저장 → 그 password 를 `lifesync/aurora` 에 sync 필요 (이 경우 위 update 명령 사용).

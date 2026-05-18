# 2026-05-17 추가 테이블 / 역할 IaC 적용 가이드

## 📦 포함 파일 (5)

| 파일 | 종류 | 적용 대상 |
|---|---|---|
| `9.customer_product_application.sql` | Aurora MySQL DDL | `lifesync360` DB |
| `create-recommend-daily-table.sh` | bash + inline SQL | Aurora `lifesync360.customer_recommend_daily` 생성 |
| `23-analytics-batch.yaml` | CloudFormation | DDB 2 테이블 + Lambda + IAM Role + EventBridge cron |
| `deploy-analytics-batch.sh` | bash | 23 yaml stack 단독 deploy (zip 빌드 + S3 업로드 + CFN deploy) |
| `invoke-analytics-aggregator.sh` | bash | analytics_aggregator lambda 1회 수동 invoke |

---

## 🗄️ 신규 테이블 (4)

### Aurora MySQL (2)

| # | 테이블 | PK | 용도 |
|---|---|---|---|
| 1 | `customer_recommend_daily` | `date` | 일별 추천 성과 mart (recommended/clicked/purchased/ctr/cvr) — P3 r10 |
| 2 | `customer_product_application` | `application_id` | 상품 신청 내역 (platform `/api/product/<code>/apply` 결과) |

### DynamoDB (2)

| # | 테이블 | PK | SK | 용도 |
|---|---|---|---|---|
| 3 | `analytics_segment_daily` | `snapshot_date` (S) | `segment_key` (S) — `dim#value` (gender#M / age_band#40s 등) | 인구통계 세그먼트별 CTR/CVR — P3 r12 |
| 4 | `analytics_demographic_daily` | `snapshot_date` (S) | `segment_key` (S) | 인구통계 분포 (성별/연령대/지역/소득/자산 비율) — P3 r13 |

---

## 적용 명령 (순서 중요)

```bash
# 0. AWS 자격 + Aurora 접근 가능 위치 (bastion 또는 같은 VPC) 에서 실행

# 1. Aurora schema migration 2개
mysql --host=<aurora-endpoint> --user=admin --password='...' lifesync360 \
  < 9.customer_product_application.sql

REGION=ap-northeast-2 AURORA_SECRET_ID=lifesync/aurora \
  bash create-recommend-daily-table.sh

# 2. DDB 2 테이블 + Lambda + IAM + EventBridge (23 stack deploy)
#    전제: 06-s3, 07-ecr, 21-lifesync-ecs CFN stack 이 이미 배포돼 있어야 함
#    23-analytics-batch.yaml 은 위 스택 outputs 를 참조
bash deploy-analytics-batch.sh

# 3. (옵션) 1회 수동 invoke — cron 안 기다리고 즉시 batch 실행
bash invoke-analytics-aggregator.sh

# 4. EventBridge cron 활성화 (검증 끝나면)
aws events enable-rule \
  --name lifesync-dev-analytics-aggregator-daily \
  --region ap-northeast-2
```

---

## 🔐 IAM 역할 변경 — 어디에 추가해야 하나

### A. `21-lifesync-ecs-existing-vpc.yaml` (ECS Task Role)

**파일 경로:** `Aws_iac/Aws_iac/templates/21-lifesync-ecs-existing-vpc.yaml`
**Role:** `${ProjectName}-${Environment}-EcsTaskRole`
**Policy:** `admin-monitoring-readonly` 인라인 정책

#### 변경 1 — DynamoDB Read 권한 (신규 DDB 2 테이블 추가)

**위치:** `Sid: DynamoDBTableReadWrite`

```yaml
- Sid: DynamoDBTableReadWrite
  Effect: Allow
  Action:
    - dynamodb:GetItem
    - dynamodb:Scan
    - dynamodb:Query
  Resource:
    - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/lifesync_customer_result"
    # 신규 추가 ↓
    - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/analytics_segment_daily"
    - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/analytics_demographic_daily"
```

#### 변경 2 — Kinesis / EMR describe 권한

**위치:** `Sid: DescribeAwsResources` Action 배열

```yaml
- Sid: DescribeAwsResources
  Effect: Allow
  Action:
    - rds:DescribeDBClusters
    - dynamodb:ListTables
    - dynamodb:DescribeTable
    - ...(기존 권한 유지)...
    - cloudwatch:GetMetricStatistics
    - cloudwatch:GetMetricData
    # 신규 추가 ↓
    - kinesis:DescribeStream
    - kinesis:DescribeStreamSummary
    - kinesis:ListStreams
    - elasticmapreduce:ListClusters
    - elasticmapreduce:DescribeCluster
  Resource: "*"
```

### B. `23-analytics-batch.yaml` (신규 Lambda Role)

**Role:** `${ProjectName}-${Environment}-analytics-aggregator-role`

이미 23 yaml 안에 정의됨 — 별도 작업 불요. 다만 다른 계정에 복제 적용 시 참고:

```yaml
ManagedPolicyArns:
  - arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

Policies:
  - PolicyName: ${ProjectName}-${Environment}-analytics-aggregator-inline
    PolicyDocument:
      Statement:
        - Sid: AuroraSecretRead
          Action:
            - secretsmanager:GetSecretValue
            - secretsmanager:DescribeSecret
          Resource: arn:aws:secretsmanager:${REGION}:${ACCOUNT}:secret:lifesync/aurora-*

        - Sid: DdbWriteAnalytics
          Action:
            - dynamodb:PutItem
            - dynamodb:BatchWriteItem
            - dynamodb:DescribeTable
          Resource:
            - {analytics_segment_daily ARN}
            - {analytics_demographic_daily ARN}

        - Sid: OnpremLambdaInvoke
          Action: lambda:InvokeFunction
          Resource: arn:aws:lambda:${REGION}:${ACCOUNT}:function:*
```

### C. admin / platform `taskdef.json` 환경변수

**파일:** `admin-platform/taskdef.json`

추가된 환경변수:

```json
{ "name": "DDB_SEGMENT_TABLE",     "value": "analytics_segment_daily" },
{ "name": "DDB_DEMOGRAPHIC_TABLE", "value": "analytics_demographic_daily" }
```

**파일:** `lifesync360-platform/taskdef.json` (선택)

```json
{ "name": "VIP_PROB_THRESHOLD", "value": "0.5" }   // default 0.5, 운영 분포 보고 조정
```

---

## 🔄 적용 순서 — 신규 계정/환경에 복제 적용 시

1. **사전 조건 확인** — Aurora `lifesync360` DB + DDB `lifesync_customer_result` 테이블 존재
2. **`21-lifesync-ecs-existing-vpc.yaml` patch** — 위 A.1 + A.2 적용 후 stack update
3. **Aurora 2 테이블 적용** — `9.customer_product_application.sql` + `create-recommend-daily-table.sh`
4. **23 stack deploy** — `deploy-analytics-batch.sh`
5. **admin taskdef.json 환경변수 추가** — CodePipeline 재배포로 ECS service 갱신
6. **1회 수동 invoke** — `invoke-analytics-aggregator.sh` 로 첫 batch 실행
7. **검증** — `/api/admin/segment-performance?dim=gender` curl → DDB 결과 확인
8. **EventBridge cron 활성화** — `aws events enable-rule ...`

---

## 검증 쿼리

### Aurora — 테이블 생성 확인

```sql
USE lifesync360;
SHOW TABLES LIKE '%recommend_daily%';
SHOW TABLES LIKE '%product_application%';
DESCRIBE customer_recommend_daily;
DESCRIBE customer_product_application;
```

### DynamoDB — 테이블 + 권한 확인

```bash
aws dynamodb describe-table --table-name analytics_segment_daily --region ap-northeast-2 \
  --query 'Table.[TableName,TableStatus,KeySchema]'

aws dynamodb describe-table --table-name analytics_demographic_daily --region ap-northeast-2 \
  --query 'Table.[TableName,TableStatus,KeySchema]'
```

### IAM — 신규 권한 확인

```bash
aws iam get-role-policy \
  --role-name lifesync-dev-EcsTaskRole \
  --policy-name admin-monitoring-readonly \
  --query 'PolicyDocument.Statement[?Sid==`DynamoDBTableReadWrite`]'

aws iam get-role --role-name lifesync-dev-analytics-aggregator-role
```

### Lambda — 함수 + cron 상태

```bash
aws lambda get-function --function-name lifesync-dev-analytics-aggregator --region ap-northeast-2
aws events describe-rule --name lifesync-dev-analytics-aggregator-daily --region ap-northeast-2
```

---

## 잘 안 되는 경우 (Troubleshooting)

| 증상 | 원인 | 해결 |
|---|---|---|
| `deploy-analytics-batch.sh` "ScriptBucketName from ... 없음" | `06-s3` stack 미배포 | 06 먼저 배포 |
| Lambda invoke 시 `AccessDenied (dynamodb)` | 23 yaml IAM Resource ARN 오타 또는 stack 갱신 누락 | 23 stack 재배포 |
| Lambda invoke 시 `Aurora connect timeout` | VPC config 의 SecurityGroup 이 Aurora SG ingress 허용 안 됨 | 21 stack `AppSgId` ingress 에 Lambda SG 추가 |
| admin `/api/admin/segment-performance` 빈 결과 | 1회 batch invoke 안 됨 / cron 활성화 X | `invoke-analytics-aggregator.sh` 실행 |
| EventBridge cron 활성화 후 결과 없음 | cron 표현식 UTC 기준 / KST 보정 안 됨 | 23 yaml `ScheduleExpression: cron(0 18 * * ? *)` (UTC 18:00 = KST 03:00) 확인 |
| `customer_product_application` INSERT 실패 (FK) | `product_master` 에 해당 `product_id` 없음 | `product_master` 데이터 선적재 (`Service-DB/4.product_master.sql`) |

---

## 관련 코드 변경 (참고)

| 파일 | 변경 요약 |
|---|---|
| `lifesync360-platform/app.py` | `/api/recommendations` 재작성 (recommend_rule + cross_sell + NBA), `GET /product/<code>/apply` + `POST /api/product/<code>/apply`, `VIP_PROB_THRESHOLD` env |
| `lifesync360-platform/templates/consent.html` | 8 계열사 카드 UI |
| `lifesync360-platform/templates/apply.html` (신규) | 신청 폼 + 결과 카드 |
| `lifesync360-platform/templates/product.html` | "신청하기" → `/product/<code>/apply` 페이지 이동 |
| `admin-platform/app.py` | `/api/admin/*` 라우트 22개 (segment/demographic/local-lab/applications 등) + GCP/Redis/Kinesis/EMR 헬퍼 |
| `admin-platform/requirements.txt` | redis, google-cloud-bigquery/aiplatform/monitoring 추가 |
| `admin-platform/taskdef.json` | DDB_SEGMENT_TABLE, DDB_DEMOGRAPHIC_TABLE 환경변수 |
| `lambda/onprem_customer_query/handler.py` | action 8 → 17 (local_lab_status + count 3 + master/identity 2 + health 3) |
| `lambda/analytics_aggregator/handler.py` (신규) | batch lambda 핸들러 |

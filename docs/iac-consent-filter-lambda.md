# IaC 전달 — consent_filter Lambda 배포 및 온프레미스 네트워크 연동

> 작성일: 2026-05-13  
> 대상: IaC 담당자  
> 관련 파일: `lambda/consent_filter/handler.py`, `lambda-to-onprem-network.md`

---

## 개요

Glue / EMR 실행 전에 온프레미스 MySQL(`lifesync_onprem.consent`)에서  
동의 고객을 추출해 S3에 저장하는 Lambda입니다.

Lambda가 온프레미스 MySQL에 직접 연결하므로  
**Data VPC → TGW → Site-to-Site VPN → ls-db(192.168.56.11:3306)** 경로가 필요합니다.

> 온프레미스 네트워크 연결 전체 설계는 `lambda-to-onprem-network.md` 참조.  
> 이 문서는 `consent_filter` Lambda에 특화된 신규 항목만 정리합니다.

---

## 1. Lambda 함수 설정

| 항목 | 값 |
|------|-----|
| 함수명 | `lifesync-consent-filter` |
| Runtime | Python 3.11 |
| 핸들러 | `handler.handler` |
| 메모리 | 512 MB |
| 제한시간 | **600초 (10분)** — 100만 건 기준 약 2~5분 소요 |
| 아키텍처 | x86_64 |
| 배포 패키지 | `lambda/consent_filter/dist/consent_filter.zip` |
| VPC | Data VPC (온프레미스 MySQL 직접 접근 필요) |

---

## 2. 환경변수

| 변수명 | 필수 | 설명 | 예시 |
|--------|------|------|------|
| `AUTH_DB_HOST` | ✅ | 온프레미스 MySQL IP | `192.168.56.11` |
| `AUTH_DB_USER` | ✅ | MySQL 계정 | `lifesync` |
| `AUTH_DB_PASS` | ✅ | MySQL 비밀번호 | Secrets Manager 참조 |
| `AUTH_DB_NAME` | | DB명 (기본값 `lifesync_onprem`) | `lifesync_onprem` |
| `OUTPUT_BUCKET` | ✅ | S3 출력 버킷명 | `lifesync-glue-input` |
| `OUTPUT_PREFIX` | | S3 키 프리픽스 (기본값 `consent-filter/`) | `consent-filter/` |
| `GLUE_JOB_NAME` | | Glue Job 이름 (비어있으면 미트리거) | `lifesync-customer-analysis` |
| `AWS_REGION` | | 리전 (기본값 `ap-northeast-2`) | `ap-northeast-2` |
| `FETCH_BATCH` | | 커서 배치 크기 (기본값 `5000`) | `5000` |

`AUTH_DB_PASS`는 평문 환경변수 대신 **Secrets Manager 참조** 방식으로 주입 권장:

```yaml
Environment:
  Variables:
    AUTH_DB_HOST: "192.168.56.11"
    AUTH_DB_USER: "lifesync"
    AUTH_DB_NAME: "lifesync_onprem"
    OUTPUT_BUCKET: "lifesync-glue-input"
    GLUE_JOB_NAME: "lifesync-customer-analysis"
    AWS_REGION:    "ap-northeast-2"
```

비밀번호는 Lambda 코드에서 Secrets Manager로 직접 조회하거나,  
CloudFormation `resolve:secretsmanager` 참조로 주입:

```yaml
AUTH_DB_PASS: "{{resolve:secretsmanager:lifesync/onprem-db:SecretString:password}}"
```

---

## 3. Secrets Manager

기존 `lifesync/aurora` 시크릿과 별개로 온프레미스 DB 자격증명 시크릿 신규 생성 필요.

```bash
aws secretsmanager create-secret \
  --name lifesync/onprem-db \
  --secret-string '{"host":"192.168.56.11","user":"lifesync","password":"<MySQL lifesync 패스워드>"}' \
  --region ap-northeast-2
```

> MySQL `lifesync` 계정 패스워드는 보안 채널로 별도 전달 예정.

---

## 4. VPC / 네트워크 구성

> Data VPC TGW Attachment 및 TGW 라우팅은 `lambda-to-onprem-network.md` 1번 항목 참조.

`consent_filter` Lambda에 추가로 필요한 사항:

### Lambda Security Group (신규 생성)

| 방향 | 프로토콜 | 포트 | 대상 | 목적 |
|------|---------|------|------|------|
| Outbound | TCP | 3306 | 192.168.56.11/32 | 온프레미스 MySQL (ls-db) |
| Outbound | TCP | 443 | 0.0.0.0/0 | S3 / Glue / EMR API 호출 |

> Outbound 443은 S3 VPC Endpoint가 Data VPC에 있으면 `pl-xxxxxxxx`(S3 Prefix List)로 제한 가능.

### Lambda VPC 설정

```yaml
VpcConfig:
  SubnetIds:
    - <Data VPC Private Subnet ID>   # TGW 라우팅이 설정된 서브넷
  SecurityGroupIds:
    - <위에서 생성한 Lambda SG ID>
```

### 온프레미스 측 — ls-db MySQL 원격 접근 확인

Lambda VPC CIDR에서 3306 접근이 허용되어 있는지 확인.

```bash
# ls-db VM에서 MySQL 원격 접근 허용 확인
mysql -u root -p -e "SELECT host, user FROM mysql.user WHERE user = 'lifesync';"
# host가 '%' 또는 Lambda VPC CIDR이어야 함
# '192.168.56.11' (localhost only) 이면 원격 접근 불가 → 아래 명령으로 수정
mysql -u root -p -e "
  UPDATE mysql.user SET host = '%' WHERE user = 'lifesync' AND host = '192.168.56.11';
  FLUSH PRIVILEGES;
"
```

ls-db VM ufw 방화벽 확인:

```bash
# ls-db VM에서
sudo ufw status
# 3306이 막혀 있으면 Lambda VPC CIDR 허용 추가
sudo ufw allow from <Lambda VPC CIDR> to any port 3306
```

---

## 5. IAM 역할 및 정책

Lambda 실행 역할(`lifesync-consent-filter-role`) 에 아래 정책 부여.

```yaml
ConsentFilterLambdaPolicy:
  Type: AWS::IAM::ManagedPolicy
  Properties:
    ManagedPolicyName: lifesync-consent-filter-policy
    PolicyDocument:
      Version: "2012-10-17"
      Statement:
        # S3 동의 파일 업로드
        - Effect: Allow
          Action:
            - s3:PutObject
            - s3:GetObject
          Resource: arn:aws:s3:::lifesync-glue-input/consent-filter/*

        # Glue Job 트리거 (선택)
        - Effect: Allow
          Action:
            - glue:StartJobRun
            - glue:GetJobRun
          Resource: arn:aws:glue:ap-northeast-2:<ACCOUNT_ID>:job/lifesync-*

        # EMR Step 추가 (선택)
        - Effect: Allow
          Action:
            - elasticmapreduce:AddJobFlowSteps
            - elasticmapreduce:DescribeStep
          Resource: arn:aws:elasticmapreduce:ap-northeast-2:<ACCOUNT_ID>:cluster/*

        # Secrets Manager — 온프레미스 DB 자격증명 조회
        - Effect: Allow
          Action:
            - secretsmanager:GetSecretValue
          Resource: arn:aws:secretsmanager:ap-northeast-2:<ACCOUNT_ID>:secret:lifesync/onprem-db*

        # CloudWatch Logs
        - Effect: Allow
          Action:
            - logs:CreateLogGroup
            - logs:CreateLogStream
            - logs:PutLogEvents
          Resource: arn:aws:logs:ap-northeast-2:<ACCOUNT_ID>:log-group:/aws/lambda/lifesync-consent-filter:*

        # VPC 내 ENI 생성 (Lambda VPC 배치 필수)
        - Effect: Allow
          Action:
            - ec2:CreateNetworkInterface
            - ec2:DescribeNetworkInterfaces
            - ec2:DeleteNetworkInterface
          Resource: "*"
```

---

## 6. S3 버킷

출력 버킷이 없으면 신규 생성. 기존 Glue 입력 버킷이 있으면 재사용 가능.

```yaml
ConsentOutputBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: lifesync-glue-input
    LifecycleConfiguration:
      Rules:
        - Id: DeleteOldConsentFiles
          Status: Enabled
          Prefix: consent-filter/
          ExpirationInDays: 30   # 30일 이상 된 파일 자동 삭제
```

---

## 7. EventBridge Scheduler (Lambda 자동 트리거)

Glue / EMR 실행 X분 전에 Lambda가 먼저 실행되도록 스케줄 설정.

```yaml
ConsentFilterSchedule:
  Type: AWS::Scheduler::Schedule
  Properties:
    Name: lifesync-consent-filter-schedule
    ScheduleExpression: "cron(0 1 * * ? *)"   # 매일 UTC 01:00 (KST 10:00)
    FlexibleTimeWindow:
      Mode: "OFF"
    Target:
      Arn: !GetAtt ConsentFilterLambda.Arn
      RoleArn: !GetAtt SchedulerRole.Arn
      Input: |
        {
          "consent_keys": ["BANK", "CARD", "INS", "ONINS", "SEC", "HLT", "wearable"],
          "trigger_glue": true
        }
```

> Glue Job 실행 시각이 KST 11:00이면 Lambda를 KST 10:00에 실행.  
> 실행 순서를 Step Functions으로 제어하는 경우 이 스케줄 대신 Step Functions State Machine 사용.

---

## 8. CloudWatch Log Group

```yaml
ConsentFilterLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: /aws/lambda/lifesync-consent-filter
    RetentionInDays: 30
```

---

## 9. 배포 절차

### 패키지 빌드

```bash
# 로컬에서 실행
cd lambda/consent_filter
bash build.sh
# → dist/consent_filter.zip 생성
```

### Lambda 생성 (최초 1회)

```bash
# 패키지를 S3에 업로드 후 Lambda 생성
aws s3 cp dist/consent_filter.zip s3://lifesync-artifact/lambda/consent_filter.zip

aws lambda create-function \
  --function-name lifesync-consent-filter \
  --runtime python3.11 \
  --handler handler.handler \
  --role arn:aws:iam::<ACCOUNT_ID>:role/lifesync-consent-filter-role \
  --code S3Bucket=lifesync-artifact,S3Key=lambda/consent_filter.zip \
  --timeout 600 \
  --memory-size 512 \
  --vpc-config SubnetIds=<Data VPC Private Subnet>,SecurityGroupIds=<Lambda SG ID> \
  --environment Variables="{
    AUTH_DB_HOST=192.168.56.11,
    AUTH_DB_USER=lifesync,
    AUTH_DB_NAME=lifesync_onprem,
    OUTPUT_BUCKET=lifesync-glue-input,
    GLUE_JOB_NAME=lifesync-customer-analysis
  }" \
  --region ap-northeast-2
```

### 코드 업데이트 (이후)

```bash
aws s3 cp dist/consent_filter.zip s3://lifesync-artifact/lambda/consent_filter.zip

aws lambda update-function-code \
  --function-name lifesync-consent-filter \
  --s3-bucket lifesync-artifact \
  --s3-key lambda/consent_filter.zip \
  --region ap-northeast-2
```

---

## 10. 검증

### 네트워크 연결 확인 (배포 전)

```bash
# Ansible EC2 (Management VPC) → ls-db MySQL 접근 확인
# VPN 연결 상태에서
mysql -h 192.168.56.11 -u lifesync -p lifesync_onprem -e "SHOW TABLES;"
# users / consent / master_customer 등 테이블 목록 출력되면 정상
```

### Lambda 수동 테스트 invoke

```bash
aws lambda invoke \
  --function-name lifesync-consent-filter \
  --payload '{"consent_keys":["BANK","CARD"],"trigger_glue":false}' \
  --region ap-northeast-2 \
  response.json

cat response.json
# 정상 응답 예시:
# {"statusCode": 200, "consented_count": 823456, "s3_uri": "s3://lifesync-glue-input/consent-filter/20260513/consented_customers.csv.gz", "glue_run_id": null, "emr_step_id": null}
```

### S3 출력 확인

```bash
aws s3 ls s3://lifesync-glue-input/consent-filter/ --recursive
# → consent-filter/20260513/consented_customers.csv.gz 파일 존재 확인

# 내용 일부 확인 (첫 5행)
aws s3 cp s3://lifesync-glue-input/consent-filter/20260513/consented_customers.csv.gz - \
  | gunzip | head -5
```

### CloudWatch 로그 확인

```bash
aws logs tail /aws/lambda/lifesync-consent-filter --follow --region ap-northeast-2
# "조회 완료: 동의 고객 XXXXX명" 메시지 확인
```

---

## 11. 작업 체크리스트

| 항목 | 담당 | 상태 |
|------|------|------|
| Data VPC TGW Attachment | IaC | ⏳ (`lambda-to-onprem-network.md` 참조) |
| Data VPC 라우팅 테이블 — 192.168.56.0/24 → TGW | IaC | ⏳ |
| Lambda SG 생성 (3306 outbound) | IaC | ⏳ |
| ls-db MySQL 원격 접근 허용 확인 | 온프레미스 담당 | ⏳ |
| Secrets Manager `lifesync/onprem-db` 생성 | IaC | ⏳ |
| S3 버킷 `lifesync-glue-input` 생성 | IaC | ⏳ |
| IAM Role / Policy 생성 | IaC | ⏳ |
| Lambda 함수 생성 및 환경변수 설정 | IaC | ⏳ |
| CloudWatch Log Group 생성 | IaC | ⏳ |
| EventBridge Scheduler 생성 | IaC | ⏳ |
| Lambda 수동 invoke 테스트 | IaC + 개발 | ⏳ |
| Glue Job `--consent_s3_path` 인자 수신 확인 | Glue 담당 | ⏳ |

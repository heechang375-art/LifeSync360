# IaC 인계 노트 — 권한 / VPC Endpoint 보강 (732 재배포 + 토큰 에러 해결)

> **작성일**: 2026-05-15
> **배경**: 354 → 732 마이그레이션 중 ECS task의 `invalid token` 에러 추적. 원인은 ExecutionRole의 KMS:Decrypt 부재 + KMS VPC Endpoint 부재 + SSM Endpoint SG가 SqlOps EC2만 허용한 조합.
> **이 노트의 변경은 이미 `Aws_iac/Aws_iac/templates/` 의 yaml 에 반영됨.** 운영팀은 재배포 후 검증만 진행.

---

## 1. 토큰 에러 근본 원인 (확정)

ECS task 가 `JWT_SECRET` 을 SSM SecureString 으로 주입받을 때, 다음 세 조건이 모두 필요:

1. **ExecutionRole 의 `ssm:GetParameters`** — Parameter 자체 fetch
2. **ExecutionRole 의 `kms:Decrypt`** — SecureString 복호화 (AWS-managed `alias/aws/ssm` 키여도 명시 권한 권장)
3. **ECS task subnet 에서 SSM + KMS 에 도달 가능** — NAT 경유 시 일시적 timeout / 권한 거부 발생 가능

기존 yaml 상태:
- ✅ (1) `ssm:GetParameters` 는 있음 (`21-lifesync-ecs-existing-vpc.yaml:208~213`)
- ❌ (2) `kms:Decrypt` 명시 없음 — **이게 invalid token 의 직접 원인**
- ❌ (3) SSM endpoint 는 08 stack 의 `SqlOpsSsmVpceSg` 가 SqlOps EC2 만 허용 / KMS endpoint 자체 없음

증상: ECS task 가 startup 시 secret fetch 일부 실패 → fallback `dev-jwt-secret-...32bytes!!` 사용 → task 간 secret 불일치 → ALB 라운드로빈 시 발급 task ≠ 검증 task → `invalid token`

---

## 2. 적용된 IaC 변경 (3개 파일)

### 변경 ① `21-lifesync-ecs-existing-vpc.yaml` — ExecutionRole 에 KMS:Decrypt 추가

```yaml
EcsExecutionRole:
  Type: AWS::IAM::Role
  Properties:
    ...
    Policies:
      - PolicyName: !Sub "${AWS::StackName}-exec-ssm-lifesync360"
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            - Sid: SsmSecretsForTaskExecution
              Effect: Allow
              Action:
                - ssm:GetParameters
                - ssm:GetParameter
              Resource: !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/lifesync360/*"
            - Sid: KmsDecryptForSsmSecureString          # ← 신규
              Effect: Allow                              # ← 신규
              Action: kms:Decrypt                        # ← 신규
              Resource: "*"                              # ← 신규 (Condition 으로 제한)
              Condition:                                 # ← 신규
                StringEquals:                            # ← 신규
                  kms:ViaService: !Sub "ssm.${AWS::Region}.amazonaws.com"  # ← 신규
```

`Resource: "*"` + `Condition.kms:ViaService` 패턴 — SSM 경유 KMS 호출만 허용 (다른 서비스 우회 차단).

### 변경 ② `01b-lifesync-vpc-endpoints.yaml` — KMS endpoint 추가 + ECR Public 제거

#### (a) KMS Interface Endpoint 신규 추가
```yaml
LifeSyncVpceKms:
  Type: AWS::EC2::VPCEndpoint
  Properties:
    VpcEndpointType: Interface
    PrivateDnsEnabled: true
    VpcId: !Ref LifeSyncVpcId
    ServiceName: !Sub "com.amazonaws.${AWS::Region}.kms"
    SubnetIds: [!Ref LifeSyncAppPrivateSubnetAId, !Ref LifeSyncAppPrivateSubnetBId]
    SecurityGroupIds: [!Ref LifeSyncVpceSg]
```

#### (b) ECR Public 제거
- `com.amazonaws.ap-northeast-2.ecr.public` 는 region 미지원 → 새벽 작업 중 stack `ROLLBACK_COMPLETE` 원인
- 제거하고 주석으로 사유 명시
- 만약 ECR Public 이미지가 필요하면 ECR Pull-Through-Cache 또는 NAT 경유로 처리

### 변경 ③ `08-database.yaml` — SqlOpsSsmVpceSg 에 VPC CIDR inbound 추가

```yaml
SecurityGroupIngress:
  - IpProtocol: tcp
    FromPort: 443
    ToPort: 443
    SourceSecurityGroupId: !Ref SqlOpsEc2Sg
    Description: SSM traffic from sql db dev EC2
  - IpProtocol: tcp
    FromPort: 443
    ToPort: 443
    SourceSecurityGroupId: !Ref SqlSsmAccessEc2Sg
    Description: SSM traffic from sql ssm access EC2
  - IpProtocol: tcp                                       # ← 신규
    FromPort: 443                                          # ← 신규
    ToPort: 443                                            # ← 신규
    CidrIp: "10.0.0.0/16"                                  # ← 신규
    Description: SSM SecureString fetch from any VPC subnet (incl. ECS App subnet)  # ← 신규
```

⚠️ `CidrIp: "10.0.0.0/16"` 은 현재 VPC CIDR 고정값. **VPC CIDR 이 다르면 yaml 의 값을 일치시켜야 함**. 추후 정식 `VpcCidr` Parameter 로 받도록 리팩토링 권장.

---

## 3. 재배포 후 검증 체크리스트

배포 순서대로:

### Phase 1 — 인프라
- [ ] `01-network` (VPC, subnet, NAT)
- [ ] `01b-lifesync-vpc-endpoints` — **KMS endpoint 생성 확인** (`aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.ap-northeast-2.kms`)
- [ ] `02-security`
- [ ] `06-s3`, `07-ecr`

### Phase 2 — DB
- [ ] `08-database` — **SqlOpsSsmVpceSg 에 VPC CIDR rule 확인**
  ```bash
  aws ec2 describe-security-groups --group-ids <sg-id> --query "SecurityGroups[0].IpPermissions[?FromPort==`443`].IpRanges[].CidrIp"
  # 결과에 "10.0.0.0/16" 포함되어야 함
  ```

### Phase 3 — ECS
- [ ] `21-lifesync-ecs-existing-vpc` — **ExecutionRole 권한 확인**
  ```bash
  ROLE=$(aws cloudformation describe-stack-resources --stack-name lifesync-dev-21-lifesync-ecs-existing-vpc --logical-resource-id EcsExecutionRole --query "StackResources[0].PhysicalResourceId" --output text)
  aws iam get-role-policy --role-name "$ROLE" --policy-name lifesync-dev-21-lifesync-ecs-existing-vpc-exec-ssm-lifesync360 --query "PolicyDocument.Statement[?Sid=='KmsDecryptForSsmSecureString']"
  # 비어있지 않아야 함
  ```

### Phase 4 — 동작 검증
- [ ] ECS task RUNNING 후 `/health` 호출:
  ```bash
  curl -s http://<alb-dns>/health
  # 기대: jwt_from_env: true, jwt_len: 64 (강한 hex secret), jwt_prefix: "fdd78ce2" 등 (mock fallback "dev-jwt-" 아님)
  ```
- [ ] `/api/login` → 토큰 발급 → 즉시 `/api/me` 호출 → **200 정상** (invalid token 아님)
- [ ] 여러 번 반복 (ALB 라운드로빈 task 모두에서 동일 secret 사용 확인)

---

## 4. 추가 인계 사항

### SSM Parameter `/lifesync360/jwt-secret` 재생성
새벽에 cleanup으로 삭제됨. 재배포 시:
- 21 stack 의 `EnableJwtRuntime` Condition 활성 시 `JwtSigningSecret` (Secrets Manager) + `Lifesync360JwtSecretParameter` (SSM) 자동 생성됨
- 또는 수동: `aws ssm put-parameter --name /lifesync360/jwt-secret --value <64-hex> --type SecureString`

### DynamoDB `lifesync_customer_result` 재생성 + 시드
- 08b stack 에 포함 (또는 별도)
- 시드 스크립트: `Aws_iac/Aws_iac/service-db/scripts/seed-dynamodb.sh` (3 row 시연 데이터)

### ECR 이미지 재push
새벽 cleanup으로 삭제됨. CI/CD 파이프라인 재실행 또는 수동 docker build + push.

### taskdef.json 의 role hash 업데이트
재배포 시 ExecutionRole / TaskRole 의 ARN hash가 새로 생성됨 (e.g. `EcsExecutionRole-A2eQoeWGranp` → 새 hash). 다음 파일들의 ARN 업데이트 필요:
- `lifesync360-platform/taskdef.json`
- `admin-platform/taskdef.json`

```bash
# 새 hash 추출
NEW_EXEC=$(aws cloudformation describe-stack-resources --stack-name lifesync-dev-21-lifesync-ecs-existing-vpc --logical-resource-id EcsExecutionRole --query "StackResources[0].PhysicalResourceId" --output text)
NEW_TASK=$(aws cloudformation describe-stack-resources --stack-name lifesync-dev-21-lifesync-ecs-existing-vpc --logical-resource-id EcsTaskRole --query "StackResources[0].PhysicalResourceId" --output text)
# sed 로 taskdef.json 업데이트
```

---

## 7. 추가 변경 (2026-05-16) — Role 이름 안정화 + 추가 권한

**파일**: `21-lifesync-ecs-existing-vpc.yaml`, `admin-platform/taskdef.json`, `lifesync360-platform/taskdef.json`

### 7-1. Role 이름 안정화 (CFN 자동 hash 제거)
ECS task 부팅 시 "토큰 에러"의 진짜 원인: **taskdef.json의 Role ARN이 실제 존재하지 않는 Role 가리킴**.
- 이전: `lifesync-EcsTaskExecutionRole` (hardcoded) — 21 yaml에 RoleName 명시 안 됨 → 자동 hash 이름 (`lifesync-dev-21-lifesync-ecs-exist-EcsExecutionRole-Dm8CCIe7mct9`)
- 수정: 21 yaml의 EcsExecutionRole / EcsTaskRole 에 `RoleName` 명시
  - `lifesync-dev-EcsTaskExecutionRole`
  - `lifesync-dev-EcsTaskRole`
- taskdef.json (admin / lifesync360) Role ARN을 안정적 이름으로 정정

### 7-2. ExecutionRole 에 admin secrets 권한 추가
admin taskdef는 `lifesync/aurora`, `lifesync/admin` secrets 사용 — ExecutionRole에 `secretsmanager:GetSecretValue` 권한 없으면 secret fetch 실패.

```yaml
- Sid: SecretsManagerForAdminAndAurora
  Action: [secretsmanager:GetSecretValue, secretsmanager:DescribeSecret]
  Resource:
    - arn:aws:secretsmanager:...:secret:lifesync/aurora-*
    - arn:aws:secretsmanager:...:secret:lifesync/admin-*
    - arn:aws:secretsmanager:...:secret:lifesync/redis-*
- Sid: KmsDecryptForSecretsManager  (kms:ViaService=secretsmanager.*)
```

### 7-3. EcsTaskRole 추가 권한 (admin 측)
- Lambda InvokeFunction: `lifesync-onprem-customer-query`, `lifesync-onprem-query-lambda`
- DynamoDB Get/Scan/Query: `lifesync_customer_result`

### 7-4. 배포 전 필수
- Secrets Manager 에 `lifesync/aurora` (host/user/password), `lifesync/admin` (secret_key/username/password) 생성 + value 입력
- `lifesync/redis` (host) 도 필요시 생성
- 21-stack update-stack 으로 Role 변경 반영 (downtime 없음)
- ECS service force-new-deployment

---

## 5. 알려진 한계

- **`10.0.0.0/16` 하드코딩**: 08-database.yaml 의 VPC CIDR. VPC CIDR 이 다르면 yaml 수정 필요. 정식 fix 는 `VpcCidr` Parameter 추가.
- **KMS endpoint 비용**: Interface endpoint 1개당 시간당 ~$0.01 + 데이터 처리. ECS task 가 자주 secret fetch 안 한다면 NAT 경유 + KMS 권한 추가만으로도 가능. 단 안정성은 endpoint 가 높음.
- **ECR Public 미지원**: 현재 region(ap-northeast-2)에서 endpoint 미지원. ECR Public 이미지 필요하면 별도 처리.

---

## 6. 추가 변경 (2026-05-16) — admin 운영 모니터링용 IAM

**파일**: `21-lifesync-ecs-existing-vpc.yaml` (EcsTaskRole)

admin-platform 의 `/ops`, `/dashboard` 화면에서 USE_MOCK=false 로 동작 시 AWS 리소스 ping 이 필요. EcsTaskRole 에 read-only inline policy `admin-monitoring-readonly` 추가:

```yaml
EcsTaskRole:
  Properties:
    Policies:
      - PolicyName: admin-monitoring-readonly
        PolicyDocument:
          Statement:
            - Sid: DescribeAwsResources
              Action:
                - rds:DescribeDBClusters
                - dynamodb:ListTables / DescribeTable
                - elasticache:DescribeCacheClusters
                - ecs:ListClusters / DescribeServices / ListServices
                - elbv2:DescribeLoadBalancers / DescribeTargetGroups / DescribeTargetHealth
                - s3:ListAllMyBuckets / HeadBucket
                - ec2:DescribeInstances / DescribeTransitGateways / DescribeVpnConnections / DescribeVpcPeeringConnections
                - lambda:GetFunction / ListFunctions
                - glue:GetJobRuns / ListJobs
                - events:DescribeRule / ListRules
                - cloudwatch:GetMetricStatistics / GetMetricData
              Resource: "*"
            - Sid: ListLifesyncBuckets
              Action: s3:ListBucket
              Resource: "arn:aws:s3:::lifesync-*"
```

**적용 시점**: 21-stack 재배포 시 자동. 기존 배포된 경우 update-stack 으로 IAM 변경분만 반영 (downtime 없음).

**검증**: admin-platform Task 컨테이너 안에서:
```bash
aws sts get-caller-identity   # EcsTaskRole 확인
aws rds describe-db-clusters --region ap-northeast-2
aws s3 ls
```

# Platform CI/CD 트러블슈팅

> 작성일: 2026-05-12

---

## 트러블슈팅 요약

| 순서 | 오류 | 원인 | 해결 |
|------|------|------|------|
| 1 | `Invalid character in header content ["authorization"]` | AWS Secret Key가 `+`로 시작 → 엑셀이 `=` 붙여 41자로 오염 | GitHub Secrets 값 직접 재입력 (엑셀 사용 금지) |
| 2 | `Signature mismatch` | Secret Key 값 불일치 | 신규 IAM 액세스 키 발급 후 재등록 |
| 3 | `buildspec.yml: no such file or directory` | CodeBuild가 `deploy/buildspec.yml` 기대, 실제 루트에 위치 | `lifesync360-platform/deploy/buildspec.yml`로 이동 |
| 4 | `imagedefinitions.json not found` | buildspec이 `imageDetail.json` 생성 (Blue/Green 포맷), 파이프라인은 ECS rolling update 포맷 기대 | artifacts를 `imagedefinitions.json`으로 변경 |
| 5 | AS `register-scalable-target` exit 254 | buildspec에 클러스터명 `lifesync-cluster` 하드코딩, 실제명과 불일치 | buildspec env에 실제 클러스터/서비스명 반영 |
| 6 | `ValidationException: Unable to assume IAM role` (AS exit 254) | `lifesync-dev-codebuild-role`에 `application-autoscaling:*` 권한 없음 | IAM 인라인 정책 `codebuild-autoscaling-policy` 추가 (`docs/codebuild-role-policy.json` 참고) |
| 7 | ECS 태스크 exit code 3 (Gunicorn worker boot error) | 태스크 정의에 `JWT_SECRET` 환경변수 없음 → `os.environ['JWT_SECRET']` KeyError → 워커 크래시 | SSM `/lifesync360/jwt-secret` 생성 후 태스크 정의 `secrets` 필드에 추가, Execution Role에 `ssm:GetParameters` 권한 추가 |
| 8 | ECS 태스크 포트 불일치 / ALB 헬스체크 실패 루프 | Gunicorn이 8000으로 바인딩, ALB 타겟 그룹은 80 고정 → 헬스체크 실패 → 태스크 교체 무한 루프 | Dockerfile `EXPOSE` 및 `--bind` 포트를 80으로 수정 후 이미지 재빌드 (타겟 그룹 포트는 생성 후 변경 불가) |
| 9 | ECS 배포 stuck (`unable to stop or start tasks`) | 서비스 배포 설정 `minimumHealthyPercent=100, maximumPercent=100` → desiredCount=1 환경에서 롤링 업데이트 불가 | `minimumHealthyPercent=0, maximumPercent=200`으로 변경 |
| 10 | ECS task 부팅 시 `invalid token` (SSM SecureString fetch 실패) — 2026-05-15 | ExecutionRole에 `ssm:GetParameters`만 있고 `kms:Decrypt` 없음 → SecureString 복호화 불가 | `21-lifesync-ecs-existing-vpc.yaml` ExecutionRole inline policy에 `kms:Decrypt` (Condition: `kms:ViaService=ssm.${REGION}.amazonaws.com`) 추가 |
| 11 | SSM endpoint timeout (VPC private subnet) — 2026-05-15 | SSM/SSMMessages/EC2Messages Interface VPC Endpoint 미배포 + SG inbound 443 누락 | `01b-lifesync-vpc-endpoints.yaml` KMS endpoint 추가, `08-database.yaml` SqlOpsSsmVpceSg 에 `CidrIp: 10.0.0.0/16` 443 inbound 추가, ECR Public endpoint 제거 (region 미지원) |
| 12 | CloudFormation 06-S3 stack `EarlyValidation: bucket already exists` (732 신규 계정) — 2026-05-15 | S3 bucket 이름이 전역 unique → 354 계정 이름과 충돌 | `params/data.env` 의 `LIFESYNC_*_S3_BUCKET` 이름에 `-732264765472` suffix 추가 |
| 13 | DynamoDB `RecommendationResultTable` stack 삭제 차단 — 2026-05-15 | `DeletionPolicy: Retain` 으로 cleanup 시 dangling 발생 | 08/08b stack: DynamoDB + SqlAssetsBucket `Retain` → `Delete` (시연/테스트 환경 한정, 운영은 Retain 복귀) |
| 14 | GitHub Actions `mirror-to-codecommit` 가 354 계정으로 동작 — 2026-05-15 | GitHub Secrets `AWS_ACCESS_KEY_ID` 가 354 계정 IAM key | `.github/workflows/platform.yml` 의 `mirror-to-codecommit` job `if: false` 로 임시 비활성. 732 키로 재발급 후 복원 예정 |

---

---

## CloudShell 진단 명령어 모음

ECS/CI/CD 파이프라인 트러블슈팅 시 사용한 명령어 정리.

### IAM 역할 정책 확인

```bash
# CodeBuild 역할에 어떤 인라인 정책이 붙어있는지 확인
aws iam list-role-policies --role-name lifesync-dev-codebuild-role

# 특정 인라인 정책 내용 확인
aws iam get-role-policy --role-name lifesync-dev-codebuild-role --policy-name codebuild-autoscaling-policy
```

### ECS 클러스터 / 서비스 확인

```bash
# 계정 내 모든 ECS 클러스터 목록
aws ecs list-clusters --region ap-northeast-2 --output text

# 특정 클러스터의 서비스 목록
aws ecs list-services --cluster <클러스터명> --region ap-northeast-2 --output text

# 서비스 상태 확인 (desiredCount, runningCount, deployments)
aws ecs describe-services \
  --cluster <클러스터명> \
  --services <서비스명> \
  --region ap-northeast-2 \
  --query 'services[0].{status:status,desiredCount:desiredCount,runningCount:runningCount,events:events[0].message}'
```

### ECS 태스크 확인

```bash
# 실행 중인 태스크 목록
aws ecs list-tasks --cluster <클러스터명> --region ap-northeast-2

# 중단된 태스크 목록 (가장 최근 1개)
aws ecs list-tasks --cluster <클러스터명> --desired-status STOPPED --region ap-northeast-2 --query 'taskArns[0]' --output text

# 태스크 상세 확인 (종료 원인, exit code)
aws ecs describe-tasks \
  --cluster <클러스터명> \
  --tasks <태스크ID> \
  --region ap-northeast-2 \
  --query 'tasks[0].{taskDef:taskDefinitionArn,stoppedReason:stoppedReason,containers:containers[*].{name:name,exitCode:exitCode,reason:reason}}'

# 여러 태스크 상태 한 번에 확인
aws ecs describe-tasks \
  --cluster <클러스터명> \
  --tasks <ID1> <ID2> <ID3> \
  --region ap-northeast-2 \
  --query 'tasks[*].{id:taskArn,status:lastStatus,taskDef:taskDefinitionArn}'
```

### ECS 태스크 정의 확인 / 등록

```bash
# 태스크 정의 목록
aws ecs list-task-definitions --region ap-northeast-2 --output text

# 태스크 정의 상세 확인
aws ecs describe-task-definition \
  --task-definition <태스크정의명>:<revision> \
  --region ap-northeast-2 \
  --query 'taskDefinition.containerDefinitions[0].environment'

# 새 태스크 정의 등록 (파일 업로드 후)
aws ecs register-task-definition \
  --cli-input-json file:///home/cloudshell-user/new-taskdef.json \
  --region ap-northeast-2 \
  --query 'taskDefinition.taskDefinitionArn'
```

### CloudWatch 로그 확인

```bash
# 로그 그룹 목록
aws logs describe-log-groups --log-group-name-prefix /ecs --region ap-northeast-2 --query 'logGroups[*].logGroupName' --output text

# 최근 로그 스트리밍
aws logs tail /ecs/lifesync-platform --since 10m --region ap-northeast-2
```

### Application Auto Scaling

```bash
# AS 서비스 연결 역할 생성 (계정당 최초 1회)
aws iam create-service-linked-role --aws-service-name ecs.application-autoscaling.amazonaws.com

# AS 서비스 연결 역할 trust policy 확인
aws iam get-role \
  --role-name AWSServiceRoleForApplicationAutoScaling_ECSService \
  --query 'Role.AssumeRolePolicyDocument'

# scalable target 수동 등록 (권한 테스트용)
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/<클러스터명>/<서비스명> \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 --max-capacity 4 \
  --region ap-northeast-2
```

### ALB 타겟 그룹 확인

```bash
# 타겟 그룹 설정 확인 (포트, 헬스체크 경로)
aws elbv2 describe-target-groups \
  --region ap-northeast-2 \
  --query 'TargetGroups[?contains(TargetGroupName, `AppTa`)].{Name:TargetGroupName,Port:Port,HealthCheckPort:HealthCheckPort,HealthCheckPath:HealthCheckPath}'
```

### SSM Parameter Store

```bash
# SSM 파라미터 생성 (SecureString, JWT 시크릿)
aws ssm put-parameter \
  --name /lifesync360/jwt-secret \
  --value "$(openssl rand -hex 32)" \
  --type SecureString \
  --region ap-northeast-2

# Execution Role에 SSM 읽기 권한 추가
aws iam put-role-policy \
  --role-name <ExecutionRole명> \
  --policy-name ecs-ssm-secret \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ssm:GetParameters"],"Resource":"arn:aws:ssm:ap-northeast-2:354493396671:parameter/lifesync360/*"}]}'
```

---

## GitHub Secrets 주의사항

| Secret 이름 | 설명 | 주의사항 |
|-------------|------|---------|
| `AWS_ACCESS_KEY_ID` | IAM 액세스 키 ID (20자, `AKIA`로 시작) | **엑셀로 열지 말 것** — `+` 시작 값에 `=` 자동 추가되어 오염됨 |
| `AWS_SECRET_ACCESS_KEY` | IAM 시크릿 키 (40자) | 메모장에서 직접 복사, 앞뒤 공백 없이 입력 |

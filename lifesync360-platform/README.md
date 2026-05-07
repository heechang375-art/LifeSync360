# LifeSync360 Platform CI/CD

ECS 기반 플랫폼 서비스 배포 파이프라인.

## 파이프라인 흐름

```
Developer Push (GitHub)
    → GitHub Actions (Unit Test / Security Scan / Docker Build Test)
    → 테스트 통과 시 자동 승인
    → CodeCommit Mirror
    → CodePipeline 트리거
    → CodeBuild (Docker Build → ECR Push)
    → CodeDeploy (ECS Deploy)
    → ALB 연결
```

---

## 파일 역할

| 파일 | 역할 |
|------|------|
| `.github/workflows/ci.yml` | GitHub Actions: 테스트 + CodeCommit 미러링 |
| `buildspec.yml` | CodeBuild: Docker 빌드 후 ECR 푸시 |
| `appspec.yaml` | CodeDeploy: ECS 배포 설정 |
| `taskdef.json` | ECS Task Definition 템플릿 |

---

## 사전 준비

### 1. taskdef.json 수정

```json
"executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole"
"taskRoleArn":      "arn:aws:iam::ACCOUNT_ID:role/ecsTaskRole"
"valueFrom":        "arn:aws:secretsmanager:ap-northeast-2:ACCOUNT_ID:secret:lifesync/db:password::"
```
→ `ACCOUNT_ID` 를 실제 AWS 계정 ID로 교체

### 2. GitHub Secrets 등록

GitHub Repo → Settings → Secrets and variables → Actions

| Secret 이름 | 값 |
|------------|-----|
| `AWS_ACCESS_KEY_ID` | CodeCommit + ECR 권한을 가진 IAM User Access Key |
| `AWS_SECRET_ACCESS_KEY` | 위 Key의 Secret |

### 3. AWS Systems Manager Parameter Store 등록

```bash
aws ssm put-parameter \
  --name /lifesync360/ecr-uri \
  --value "ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/lifesync360-platform" \
  --type String \
  --region ap-northeast-2
```

### 4. AWS 리소스 생성 (Terraform으로 관리)

- ECR Repository: `lifesync360-platform`
- ECS Cluster: `lifesync360-cluster`
- ECS Service: `lifesync360-service`
- CodePipeline: Source(CodeCommit) → Build(CodeBuild) → Deploy(CodeDeploy)
- CodeDeploy Application + Deployment Group (ECS 타입)

---

## 배포 방법

### 일반 배포 (자동)

```bash
git add .
git commit -m "feat: 변경 내용"
git push origin main
```

GitHub Actions가 자동으로 테스트 → CodeCommit 미러 → CodePipeline 트리거.

### 수동 배포 (긴급 시)

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com

# 빌드 및 푸시
docker build -t lifesync360-platform .
docker tag lifesync360-platform:latest ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/lifesync360-platform:latest
docker push ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/lifesync360-platform:latest

# ECS 서비스 강제 재배포
aws ecs update-service \
  --cluster lifesync360-cluster \
  --service lifesync360-service \
  --force-new-deployment \
  --region ap-northeast-2
```

---

## 배포 상태 확인

```bash
# CodePipeline 상태
aws codepipeline get-pipeline-state \
  --name lifesync360-pipeline \
  --region ap-northeast-2

# ECS 서비스 상태
aws ecs describe-services \
  --cluster lifesync360-cluster \
  --services lifesync360-service \
  --region ap-northeast-2 \
  --query "services[0].deployments"

# ECS 태스크 로그 (CloudWatch)
aws logs tail /ecs/lifesync360 --follow --region ap-northeast-2
```

---

## 트러블슈팅

### GitHub Actions에서 CodeCommit 미러 실패
```
원인: IAM User에 CodeCommit 권한 없음
해결: IAM Policy에 AWSCodeCommitPowerUser 추가
```

### CodeBuild에서 ECR Push 실패
```
원인: CodeBuild 서비스 역할에 ECR 권한 없음
해결: IAM Role에 AmazonEC2ContainerRegistryPowerUser 추가
```

### ECS 태스크가 시작 안 됨
```
원인: Secrets Manager 접근 권한 또는 잘못된 ARN
해결:
  1. taskdef.json의 ARN 확인
  2. ecsTaskExecutionRole에 SecretsManagerReadWrite 추가
  3. CloudWatch Logs에서 태스크 시작 로그 확인
```

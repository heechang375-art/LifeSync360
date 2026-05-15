# IaC 팀 전달 항목

> 작성일: 2026-05-12
> 현재 콘솔에서 수동 처리된 항목들 — CloudFormation으로 이관 필요.

---

## 1. IAM 역할 정책 추가

### `lifesync-dev-codebuild-role`

```yaml
# SSM 파라미터 읽기
- Effect: Allow
  Action:
    - ssm:GetParameters
    - ssm:GetParameter
  Resource: arn:aws:ssm:ap-northeast-2:354493396671:parameter/lifesync360/*

# Auto Scaling 등록 및 정책 설정
- Effect: Allow
  Action:
    - application-autoscaling:RegisterScalableTarget
    - application-autoscaling:PutScalingPolicy
    - application-autoscaling:DescribeScalingPolicies
    - cloudwatch:PutMetricAlarm
  Resource: "*"
```

### `lifesync-dev-codepipeline-role`

```yaml
# S3 아티팩트 버킷 접근
- Effect: Allow
  Action:
    - s3:GetObject
    - s3:PutObject
    - s3:GetObjectVersion
    - s3:GetBucketVersioning
  Resource:
    - arn:aws:s3:::lifesync-artifact
    - arn:aws:s3:::lifesync-artifact/*
```

---

## 2. SSM Parameter Store 파라미터 생성

| 파라미터 이름 | 타입 | 값 |
|--------------|------|-----|
| `/lifesync360/ecr-uri` | String | `354493396671.dkr.ecr.ap-northeast-2.amazonaws.com/lifesync-dev-lifesync360-service` |

CloudFormation 예시:

```yaml
EcrUriParameter:
  Type: AWS::SSM::Parameter
  Properties:
    Name: /lifesync360/ecr-uri
    Type: String
    Value: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/lifesync-dev-lifesync360-service
```

---

## 3. CodeBuild 프로젝트 buildspec 경로 확인

buildspec 경로가 `deploy/buildspec.yml`로 설정돼 있어야 함.

```yaml
Source:
  BuildSpec: deploy/buildspec.yml
```

---

## 4. ECS Execution Role SSM 권한 추가

### `lifesync-dev-21-lifesync-ecs-exist-EcsExecutionRole-ZE9R5wfJvb9o`

ECS 태스크가 SSM SecureString을 `secrets` 필드로 주입받으려면 Execution Role에 아래 권한 필요.

```yaml
- Effect: Allow
  Action:
    - ssm:GetParameters
  Resource: arn:aws:ssm:ap-northeast-2:354493396671:parameter/lifesync360/*
```

---

## 5. SSM Parameter Store 추가 파라미터

| 파라미터 이름 | 타입 | 설명 |
|--------------|------|------|
| `/lifesync360/jwt-secret` | SecureString | JWT 서명 키 (최초 1회 생성 후 고정) |

CloudFormation 예시:

```yaml
JwtSecretParameter:
  Type: AWS::SSM::Parameter
  Properties:
    Name: /lifesync360/jwt-secret
    Type: String
    Value: !Sub "{{resolve:secretsmanager:lifesync/jwt-secret}}"
```

> SecureString은 CloudFormation 직접 생성 불가 — Secrets Manager 연동 또는 초기 구축 스크립트로 처리 필요.

---

## 6. ECS 태스크 정의 수정 사항

현재 콘솔에서 수동 처리된 내용 — CloudFormation 태스크 정의에 반영 필요.

```yaml
ContainerDefinitions:
  - Name: app
    PortMappings:
      - ContainerPort: 80
        HostPort: 80
        Protocol: tcp
    Environment:
      - Name: USE_MOCK
        Value: "true"
    Secrets:
      - Name: JWT_SECRET
        ValueFrom: !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/lifesync360/jwt-secret"
    LogConfiguration:
      LogDriver: awslogs
      Options:
        awslogs-group: /ecs/lifesync-platform
        awslogs-region: !Ref AWS::Region
        awslogs-stream-prefix: ecs
```

---

## 7. CloudWatch Log Group 생성

```yaml
PlatformLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: /ecs/lifesync-platform
    RetentionInDays: 30
```

---

## 8. ECS 서비스 배포 설정 수정

롤링 업데이트 가능하도록 배포 설정 변경 필요. desiredCount=1 환경에서 `minimumHealthyPercent=100`이면 배포 불가.

```yaml
DeploymentConfiguration:
  MinimumHealthyPercent: 0
  MaximumPercent: 200
```

---

## 9. 어드민 플랫폼 CI/CD 인프라 신규 구성

> 플랫폼과 동일한 패턴으로 어드민 전용 파이프라인 구성 필요.

### 9-1. ECR 리포지토리

| 리포명 | 용도 |
|--------|------|
| `lifesync-dev-admin-service` | 어드민 플랫폼 Docker 이미지 |

### 9-2. CodeCommit 리포지토리

| 리포명 | 용도 |
|--------|------|
| `lifesync360-admin` | GitHub `admin-platform/` 폴더 미러링 대상 |

### 9-3. SSM Parameter Store

| 파라미터 이름 | 타입 | 값 |
|--------------|------|-----|
| `/lifesync360/ecr-uri-admin` | String | `354493396671.dkr.ecr.ap-northeast-2.amazonaws.com/lifesync-dev-admin-service` |

```yaml
EcrUriAdminParameter:
  Type: AWS::SSM::Parameter
  Properties:
    Name: /lifesync360/ecr-uri-admin
    Type: String
    Value: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/lifesync-dev-admin-service
```

### 9-4. CodeBuild 프로젝트

| 항목 | 값 |
|------|-----|
| 프로젝트명 | `lifesync-admin-build` |
| 소스 | CodeCommit `lifesync360-admin` |
| BuildSpec 경로 | `deploy/buildspec.yml` |
| 실행 역할 | `lifesync-dev-codebuild-role` (기존 플랫폼과 동일) |

### 9-5. CodePipeline

| 항목 | 값 |
|------|-----|
| 파이프라인명 | `lifesync-admin-pipeline` |
| Source | CodeCommit `lifesync360-admin` (main 브랜치) |
| Build | CodeBuild `lifesync-admin-build` |
| Deploy | Amazon ECS — 클러스터: 기존, 서비스: `lifesync-admin-svc` |

### 9-6. ECS 서비스

| 항목 | 값 |
|------|-----|
| 서비스명 | `lifesync-admin-svc` |
| 클러스터 | 기존 (`lifesync-dev-21-lifesync-ecs-existing-vpc-v4-EcsCluster-ZRqOqKu4Gzpb`) |
| 태스크 정의명 | `lifesync-admin-td` |
| 초기 DesiredCount | `0` (플랫폼과 동일하게 CI/CD 첫 실행 시 AS가 1로 올림) |
| 포트 | 80 |

태스크 정의 파일: `docs/new-taskdef-admin.json` 참고

```yaml
DeploymentConfiguration:
  MinimumHealthyPercent: 0
  MaximumPercent: 200
```

### 9-7. CloudWatch Log Group

```yaml
AdminLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: /ecs/lifesync-admin
    RetentionInDays: 30
```

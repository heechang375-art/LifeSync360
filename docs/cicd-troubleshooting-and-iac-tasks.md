# CI/CD 트러블슈팅 및 IaC 팀 전달 항목

> 작성일: 2026-05-12

---

## 1. 트러블슈팅 요약 (platform CI/CD)

| 순서 | 오류 | 원인 | 해결 |
|------|------|------|------|
| 1 | `Invalid character in header content ["authorization"]` | AWS Secret Key가 `+`로 시작 → 엑셀이 `=` 붙여 41자로 오염 | GitHub Secrets 값 직접 재입력 (엑셀 사용 금지) |
| 2 | `Signature mismatch` | Secret Key 값 불일치 | 신규 IAM 액세스 키 발급 후 재등록 |
| 3 | `buildspec.yml: no such file or directory` | CodeBuild가 `deploy/buildspec.yml` 기대, 실제 루트에 위치 | `lifesync360-platform/deploy/buildspec.yml`로 이동 |
| 4 | `parameter does not exist: /lifesync360/ecr-uri` | SSM 파라미터 미생성 | 콘솔에서 수동 생성 (→ IaC 이관 필요) |
| 5 | `ssm:GetParameters not authorized` | CodeBuild 역할에 SSM 권한 없음 | 인라인 정책 수동 추가 (→ IaC 이관 필요) |
| 6 | `s3:PutObject AccessDenied` | CodePipeline 역할에 S3 아티팩트 버킷 권한 없음 | 인라인 정책 수동 추가 (→ IaC 이관 필요) |
| 7 | `imagedefinitions.json not found` | buildspec이 `imageDetail.json` 생성 (Blue/Green 포맷), 파이프라인은 ECS rolling update 포맷 기대 | artifacts를 `imagedefinitions.json`으로 변경 |
| 8 | AS `register-scalable-target` exit 254 | buildspec에 클러스터명 `lifesync-cluster` 하드코딩, 실제명과 불일치 | buildspec env에 실제 클러스터/서비스명 반영 |

---

## 2. IaC 팀 전달 항목

> 아래 항목들은 현재 AWS 콘솔에서 수동으로 처리된 상태.
> CloudFormation으로 이관하여 코드로 관리 필요.

---

### 2-1. IAM 역할 정책 추가

#### `lifesync-dev-codebuild-role`

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

#### `lifesync-dev-codepipeline-role`

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

### 2-2. SSM Parameter Store 값 생성

현재 콘솔에서 수동 생성된 파라미터 — CloudFormation `AWS::SSM::Parameter` 리소스로 이관 필요.

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

### 2-3. CodeBuild 프로젝트 buildspec 경로 설정

CodeBuild 프로젝트에 buildspec 경로가 `deploy/buildspec.yml`로 설정돼 있어야 함.
CloudFormation으로 CodeBuild 프로젝트를 관리한다면 아래 확인:

```yaml
Source:
  BuildSpec: deploy/buildspec.yml
```

---

## 3. GitHub Secrets 주의사항

IaC 범위 외 — 배포 담당자가 직접 등록.

| Secret 이름 | 설명 | 주의사항 |
|-------------|------|---------|
| `AWS_ACCESS_KEY_ID` | IAM 액세스 키 ID (20자, `AKIA`로 시작) | **엑셀로 열지 말 것** — `+` 시작 값에 `=` 자동 추가되어 오염됨 |
| `AWS_SECRET_ACCESS_KEY` | IAM 시크릿 키 (40자) | 메모장에서 직접 복사, 앞뒤 공백 없이 입력 |

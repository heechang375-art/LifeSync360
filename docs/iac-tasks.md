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

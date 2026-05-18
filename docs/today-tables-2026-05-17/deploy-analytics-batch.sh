#!/usr/bin/env bash
# Deploy 23-analytics-batch stack (Lambda + DDB 2 tables + EventBridge cron DISABLED).
#
# 전제: 06-s3 (ScriptBucket), 08-database (Aurora), 21-lifesync-ecs (VPC/Subnet/SG) 이미 배포됨.
# 흐름: zip 빌드 → S3 업로드 → CFN deploy.
set -euo pipefail

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${_HERE}/../.." && pwd)"

if command -v cygpath >/dev/null 2>&1; then
  ROOT_DIR=$(cygpath -m "${ROOT_DIR}")
fi
source "${ROOT_DIR}/params/common.env"
[[ "${AWS_PROFILE:-}" =~ ^[[:space:]]*$ ]] && unset AWS_PROFILE

aws_cli() {
  if [[ -n "${AWS_PROFILE:-}" ]]; then aws --profile "${AWS_PROFILE}" "$@"; else aws "$@"; fi
}

get_output() {
  aws_cli cloudformation describe-stacks --region "${REGION}" --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text
}

STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}-23-analytics-batch"
TEMPLATE="${ROOT_DIR}/templates/23-analytics-batch.yaml"
LAMBDA_DIR="$(cd "${ROOT_DIR}/../../lambda/analytics_aggregator" && pwd)"
[[ -d "${LAMBDA_DIR}" ]] || { echo "FAIL: lambda dir not found: ${LAMBDA_DIR}"; exit 1; }

S3_STACK="${PROJECT_NAME}-${ENVIRONMENT}-06-s3"
ECS_STACK="${PROJECT_NAME}-${ENVIRONMENT}-21-lifesync-ecs-existing-vpc-v4"

echo "[INFO] 23 analytics batch: REGION=${REGION} STACK=${STACK_NAME}"

# ── 의존 stack outputs 수집 ──
SCRIPT_BUCKET=$(get_output "${S3_STACK}" "ScriptBucketName")
[[ -n "${SCRIPT_BUCKET}" && "${SCRIPT_BUCKET}" != "None" ]] || { echo "FAIL: ScriptBucketName from ${S3_STACK}"; exit 1; }

APP_SG=$(get_output "${ECS_STACK}" "AppSgId")
VPC_ID=$(get_output "${ECS_STACK}" "LifeSyncVpcId")
[[ -n "${APP_SG}" && "${APP_SG}" != "None" ]] || { echo "FAIL: AppSgId from ${ECS_STACK}"; exit 1; }
[[ -n "${VPC_ID}" && "${VPC_ID}" != "None" ]] || { echo "FAIL: LifeSyncVpcId from ${ECS_STACK}"; exit 1; }

# private subnet 자동 추출 (Tag Name 에 'private' 포함)
SUBNET_IDS=$(aws_cli ec2 describe-subnets --region "${REGION}" \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=tag:Name,Values=*private*" \
  --query "Subnets[].SubnetId" --output text | tr '\t' ',')
[[ -n "${SUBNET_IDS}" ]] || { echo "FAIL: private subnet 없음 (vpc=${VPC_ID})"; exit 1; }

ONPREM_LAMBDA="${ONPREM_QUERY_LAMBDA_NAME:-}"

# ── lambda zip 빌드 ──
echo "[Build] analytics_aggregator zip"
( cd "${LAMBDA_DIR}" && bash build.sh )

ZIP_LOCAL="${LAMBDA_DIR}/analytics_aggregator.zip"
S3_KEY="lambda/analytics_aggregator/analytics_aggregator.zip"

echo "[Upload] s3://${SCRIPT_BUCKET}/${S3_KEY}"
aws_cli s3 cp "${ZIP_LOCAL}" "s3://${SCRIPT_BUCKET}/${S3_KEY}"

# ── CFN deploy ──
echo "[Validate] ${TEMPLATE}"
aws_cli cloudformation validate-template --region "${REGION}" --template-body "file://${TEMPLATE}" >/dev/null

echo "[Deploy] ${STACK_NAME}"
aws_cli cloudformation deploy \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    "ProjectName=${PROJECT_NAME}" \
    "Environment=${ENVIRONMENT}" \
    "LambdaCodeS3Bucket=${SCRIPT_BUCKET}" \
    "LambdaCodeS3Key=${S3_KEY}" \
    "LambdaSubnetIds=${SUBNET_IDS}" \
    "LambdaSecurityGroupId=${APP_SG}" \
    "OnpremQueryLambdaName=${ONPREM_LAMBDA}"

echo "[DONE] ${STACK_NAME}"
aws_cli cloudformation describe-stacks --region "${REGION}" --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs" --output table

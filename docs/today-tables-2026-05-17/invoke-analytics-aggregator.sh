#!/usr/bin/env bash
# analytics_aggregator lambda 1회 수동 invoke (cron 안 기다리고).
# 사용: bash scripts/data/invoke-analytics-aggregator.sh
set -euo pipefail

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${_HERE}/../.." && pwd)"
source "${ROOT_DIR}/params/common.env"

STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}-23-analytics-batch"
FUNCTION_NAME=$(aws cloudformation describe-stacks --region "${REGION}" --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='AnalyticsAggregatorFunctionName'].OutputValue" --output text)

[[ -n "${FUNCTION_NAME}" && "${FUNCTION_NAME}" != "None" ]] || { echo "FAIL: 23 stack 미배포 또는 함수명 못 가져옴"; exit 1; }

echo "[Invoke] ${FUNCTION_NAME}"
OUT=$(mktemp)
aws lambda invoke --region "${REGION}" --function-name "${FUNCTION_NAME}" \
  --invocation-type RequestResponse \
  --cli-binary-format raw-in-base64-out \
  --payload '{}' \
  "${OUT}" >/dev/null

echo "[Result]"
cat "${OUT}" | jq .
rm -f "${OUT}"

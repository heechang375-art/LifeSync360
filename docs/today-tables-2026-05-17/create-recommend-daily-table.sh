#!/usr/bin/env bash
# Aurora 안에 customer_recommend_daily mart 테이블 생성 (P3 r10).
# Secrets Manager 'lifesync/aurora' 에서 host/user/password 가져와 mysql client로 적용.
#
# 전제: mysql client 설치됨, lambda 가 Aurora 같은 SG/Subnet 에 있거나 bastion 경유.
set -euo pipefail

REGION="${REGION:-ap-northeast-2}"
SECRET_ID="${AURORA_SECRET_ID:-lifesync/aurora}"
DB_NAME="${AURORA_DB_NAME:-lifesync360}"

command -v mysql >/dev/null 2>&1 || { echo "FAIL: mysql client 필요 (apt install mysql-client / brew install mysql-client)"; exit 1; }
command -v jq    >/dev/null 2>&1 || { echo "FAIL: jq 필요"; exit 1; }

SECRET_JSON=$(aws secretsmanager get-secret-value --region "${REGION}" --secret-id "${SECRET_ID}" --query SecretString --output text)
HOST=$(echo "${SECRET_JSON}" | jq -r .host)
USER=$(echo "${SECRET_JSON}" | jq -r .user)
PASS=$(echo "${SECRET_JSON}" | jq -r .password)
PORT=$(echo "${SECRET_JSON}" | jq -r '.port // "3306"')

[[ "${HOST}" == "null" || -z "${HOST}" ]] && { echo "FAIL: secret '${SECRET_ID}' 에 host 없음"; exit 1; }

echo "[INFO] Aurora ${HOST}:${PORT} DB=${DB_NAME} USER=${USER}"

mysql --host="${HOST}" --port="${PORT}" --user="${USER}" --password="${PASS}" "${DB_NAME}" <<'SQL'
CREATE TABLE IF NOT EXISTS customer_recommend_daily (
  date         DATE         PRIMARY KEY,
  recommended  INT          NOT NULL,
  clicked      INT          NOT NULL,
  purchased    INT          NOT NULL,
  ctr          DECIMAL(5,2),
  cvr          DECIMAL(5,2),
  created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- recommended_at 인덱스 (batch GROUP BY DATE 최적화) — 이미 있으면 SKIP
-- CREATE INDEX 는 멱등 아니므로 INFORMATION_SCHEMA 체크 후 동적 SQL 필요. 시연에선 수동 확인.
SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'customer_recommend_history'
  AND COLUMN_NAME = 'recommended_at';
SQL

echo ""
echo "[DONE] customer_recommend_daily 테이블 적용 완료."
echo "[INFO] 위 SELECT 결과가 비어있으면 다음 명령으로 인덱스 추가:"
echo "       CREATE INDEX idx_recommended_at ON customer_recommend_history(recommended_at);"

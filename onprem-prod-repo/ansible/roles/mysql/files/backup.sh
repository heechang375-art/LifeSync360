#!/bin/bash
BACKUP_DIR=/opt/mysql/backups
DB_NAME=lifesync_onprem
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id lifesync/onprem-db \
  --region ap-northeast-2 \
  --query SecretString \
  --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['root_password'])")

mysqldump -u root -p"$PASSWORD" $DB_NAME > $BACKUP_DIR/${DB_NAME}_${DATE}.sql

find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

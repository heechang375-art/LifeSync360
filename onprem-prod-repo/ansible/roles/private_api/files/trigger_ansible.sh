#!/bin/bash
LOG=/opt/private-api/ansible-deploy.log

if [ "${ANSIBLE_ENV}" = "production" ]; then
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${CONTROL_NODE_URL}/deploy" \
    -H "X-Deploy-Token: ${DEPLOY_TOKEN}" \
    --max-time 10)

  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | head -1)

  if [ "$HTTP_CODE" != "200" ]; then
    echo "$(date) ERROR: Control Node 호출 실패 (HTTP $HTTP_CODE): $BODY" >&2
    exit 1
  fi
  echo "$(date) 배포 트리거 완료: $BODY" >> $LOG
else
  ANSIBLE_DIR=/opt/ansible/onprem-prod-repo/ansible
  echo "$(date) [LOCAL] ansible-playbook 직접 실행" >> $LOG
  cd $ANSIBLE_DIR && ansible-playbook site.yml -i inventory/hosts.yml >> $LOG 2>&1
fi

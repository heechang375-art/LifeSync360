#!/bin/bash
ANSIBLE_DIR=/opt/ansible/ansible
LOG=/var/log/ansible-deploy.log

if [ "${ANSIBLE_ENV}" = "production" ]; then
  REGION=ap-northeast-2
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=ansible-control-node" \
              "Name=instance-state-name,Values=running" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text \
    --region $REGION)

  if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" = "None" ]; then
    echo "$(date) ERROR: ansible-control-node 인스턴스를 찾을 수 없음" >&2
    exit 1
  fi

  aws ssm send-command \
    --document-name "AWS-RunShellScript" \
    --instance-ids "$INSTANCE_ID" \
    --parameters 'commands=["ansible-pull -U https://git-codecommit.ap-northeast-2.amazonaws.com/v1/repos/onprem-prod-repo ansible/site.yml >> /var/log/ansible-deploy.log 2>&1"]' \
    --timeout-seconds 600 \
    --region $REGION \
    --output text \
    --query "Command.CommandId"
else
  echo "$(date) [LOCAL] ansible-playbook 직접 실행" >> $LOG
  cd $ANSIBLE_DIR && ansible-playbook site.yml >> $LOG 2>&1
fi

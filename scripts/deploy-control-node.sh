#!/bin/bash
# Control Node 배포 후 로컬 작업 스크립트
#
# 실행 전제:
#   1. 14a-ansible-iam, 14b-ansible-ec2, 14c-ansible-key-publish 스택 배포 완료
#   2. VPN 터널 연결 상태
#
# 사용법:
#   bash scripts/deploy-control-node.sh

set -euo pipefail

REGION="ap-northeast-2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE_NAME="lifesync-dev-management-ec2-ansible"   # 14b EC2 Name 태그

# ── 헬퍼 ──────────────────────────────────────────────────
log()     { echo "[$(date '+%H:%M:%S')] $*"; }
section() { echo ""; echo "══════════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════════"; echo ""; }
pause()   { read -r -p "$* [Enter 계속]: " _; }

# ═══════════════════════════════════════════════
# 1단계: VPN 터널 연결
# ═══════════════════════════════════════════════
section "1단계: VPN 터널 연결"

read -r -p "  터널이 이미 연결돼 있습니까? (y=건너뜀 / n=터널 스크립트 실행): " TUNNEL_ALREADY_UP
if [[ "$TUNNEL_ALREADY_UP" =~ ^[Yy]$ ]]; then
    log "터널 연결 확인됨 — 건너뜀"
else
    bash "${SCRIPT_DIR}/update-vpn-tunnel.sh"
    echo ""
    echo "  ls-api에서 확인: sudo ipsec status"
    echo "  ESTABLISHED 확인 후 계속하세요."
    pause "  터널 ESTABLISHED 확인됨?"
fi

# ═══════════════════════════════════════════════
# 2단계: Control Node SSM 검증
# ═══════════════════════════════════════════════
section "2단계: Control Node UserData 검증"

INSTANCE_INFO=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=${INSTANCE_NAME}" \
              "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].[InstanceId,PrivateIpAddress]' \
    --output text --region "$REGION" 2>/dev/null || echo "")

INSTANCE_ID=$(echo "$INSTANCE_INFO" | awk '{print $1}')
PRIVATE_IP=$(echo "$INSTANCE_INFO" | awk '{print $2}')

if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" = "None" ]; then
    log "Name 태그(${INSTANCE_NAME})로 인스턴스를 찾지 못했습니다."
    read -r -p "  Instance ID 직접 입력 (EC2 콘솔에서 확인): " INSTANCE_ID
fi

if [ -z "$PRIVATE_IP" ] || [ "$PRIVATE_IP" = "None" ]; then
    read -r -p "  Private IP 직접 입력 (EC2 콘솔에서 확인): " PRIVATE_IP
fi

log "Instance ID : $INSTANCE_ID"
log "Private IP  : $PRIVATE_IP"

log "SSM Agent 준비 대기 중 (최대 5분)..."
SSM_READY=false
for i in $(seq 1 30); do
    STATUS=$(aws ssm describe-instance-information \
        --filters "Key=InstanceIds,Values=${INSTANCE_ID}" \
        --query 'InstanceInformationList[0].PingStatus' \
        --output text --region "$REGION" 2>/dev/null || echo "None")
    if [ "$STATUS" = "Online" ]; then
        log "SSM Agent Online ✓"
        SSM_READY=true
        break
    fi
    echo "  대기 중... ($i/30)"
    sleep 10
done

if [ "$SSM_READY" = false ]; then
    echo "[오류] SSM Agent 응답 없음. 수동으로 확인하세요:"
    echo "  aws ssm start-session --target $INSTANCE_ID --region $REGION"
    exit 1
fi

log "UserData 완료 여부 확인 중 (SSH 키 생성 확인)..."
CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["test -f /home/ansible/.ssh/id_rsa.pub && echo SUCCESS || echo FAILED"]' \
    --query 'Command.CommandId' \
    --output text --region "$REGION")

sleep 8

RESULT=$(aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text --region "$REGION" 2>/dev/null || echo "FAILED")

if [[ "$RESULT" == *"SUCCESS"* ]]; then
    log "UserData 완료 ✓ — SSH 키 정상 생성됨"
else
    log "[주의] SSH 키 미생성 — UserData 미완료 또는 실패"
    echo ""
    echo "  부트스트랩 로그 확인:"
    echo "    aws ssm start-session --target $INSTANCE_ID --region $REGION"
    echo "    sudo tail -50 /var/log/ansible-bootstrap.log"
    echo ""
    echo "  수동 키 생성 (SSM 세션에서):"
    echo "    sudo install -d -m 0700 -o ansible -g ansible /home/ansible/.ssh"
    echo "    sudo -u ansible ssh-keygen -t rsa -b 4096 -N \"\" -f /home/ansible/.ssh/id_rsa -q"
    echo "    sudo chown -R ansible:ansible /home/ansible/.ssh"
fi

# ═══════════════════════════════════════════════
# 완료
# ═══════════════════════════════════════════════
section "완료"

echo "  Control Node 정보"
echo "  ─────────────────────────────────────────"
echo "  Instance ID   : $INSTANCE_ID"
echo ""
echo "  SSM 접속 명령"
echo "  ─────────────────────────────────────────"
echo "  aws ssm start-session --target $INSTANCE_ID --region $REGION"
echo ""

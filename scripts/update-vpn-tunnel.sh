#!/bin/bash
# LifeSync360 VPN 터널 자동 연결
# IaC 재배포(매일 9AM) 후 실행 — 새 AWS 터널 IP를 ls-api StrongSwan에 반영
#
# 사전 조건:
#   - AWS CLI 설치 및 `aws configure` 완료
#   - ls-api (192.168.56.13) 부팅 완료 및 Host-only 네트워크 접근 가능
#   - ~/.ssh/lifesync360-onprem.pem 존재
#
# PSK 조회 우선순위:
#   1. Secrets Manager lifesync/vpn-psk (IaC팀이 등록 후 완전 자동화)
#   2. ls-api /etc/ipsec.secrets 기존 PSK 추출 (임시, PSK 불변 보장 안 됨)

set -euo pipefail

# ── 설정 ──────────────────────────────────────────────────────────
VPN_NAME_TAG="lifesync-vpn"        # IaC팀 CF VPN Connection의 Name 태그 확인 필요
SM_PSK_SECRET="lifesync/vpn-psk"   # IaC팀이 SM에 PSK 등록 후 자동 활성화
LS_API_IP="192.168.56.13"
LS_API_USER="ansible"
SSH_KEY="${HOME}/.ssh/lifesync360-onprem.pem"
AWS_REGION="ap-northeast-2"

# 환경변수로 VPN Connection ID 직접 지정 가능 (태그 조회 실패 시 사용)
# 사용법: VPN_CONNECTION_ID=vpn-xxxxxxxxx ./update-vpn-tunnel.sh
VPN_CONNECTION_ID="${VPN_CONNECTION_ID:-}"

# ── SSH 옵션 ──────────────────────────────────────────────────────
SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes"
[ -f "$SSH_KEY" ] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"

echo "================================================"
echo " LifeSync360 VPN 터널 업데이트"
echo "================================================"

# ── [1/4] 터널 IP 조회 ───────────────────────────────
echo ""
echo "[1/4] AWS VPN 터널 IP 조회..."

if [ -n "$VPN_CONNECTION_ID" ]; then
    # ID 직접 지정
    QUERY_ARGS="--vpn-connection-ids $VPN_CONNECTION_ID"
else
    # Name 태그로 조회
    QUERY_ARGS="--filters Name=tag:Name,Values=${VPN_NAME_TAG}"
fi

# UP 상태 터널 우선
TUNNEL_IP=$(aws ec2 describe-vpn-connections \
    --region "$AWS_REGION" \
    $QUERY_ARGS \
    --query 'VpnConnections[?State==`available`] | [0].VgwTelemetry[?Status==`UP`] | [0].OutsideIpAddress' \
    --output text 2>/dev/null || echo "None")

# UP 없으면 첫 번째 터널로 폴백
if [ "$TUNNEL_IP" = "None" ] || [ -z "$TUNNEL_IP" ]; then
    echo "  UP 상태 터널 없음 — 첫 번째 터널 IP로 시도..."
    TUNNEL_IP=$(aws ec2 describe-vpn-connections \
        --region "$AWS_REGION" \
        $QUERY_ARGS \
        --query 'VpnConnections[?State==`available`] | [0].VgwTelemetry[0].OutsideIpAddress' \
        --output text 2>/dev/null || echo "None")
fi

if [ "$TUNNEL_IP" = "None" ] || [ -z "$TUNNEL_IP" ]; then
    echo ""
    echo "[오류] 터널 IP 조회 실패. 확인 항목:"
    echo "  1. aws configure — 인증 설정 여부"
    echo "  2. VPN Name 태그가 '${VPN_NAME_TAG}'인지 IaC팀 확인"
    echo "     또는: VPN_CONNECTION_ID=vpn-xxx ./update-vpn-tunnel.sh"
    echo "  3. VPN Connection 상태가 available인지 AWS 콘솔 확인"
    exit 1
fi
echo "  ✓ 터널 IP: ${TUNNEL_IP}"

# ── [2/4] PSK 조회 ───────────────────────────────────
echo ""
echo "[2/4] PSK 조회..."
PSK=""

# Secrets Manager 시도 (IaC팀이 등록한 경우)
if aws secretsmanager describe-secret \
    --secret-id "$SM_PSK_SECRET" \
    --region "$AWS_REGION" > /dev/null 2>&1; then
    PSK=$(aws secretsmanager get-secret-value \
        --secret-id "$SM_PSK_SECRET" \
        --region "$AWS_REGION" \
        --query SecretString --output text \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['psk'])")
    echo "  ✓ PSK: Secrets Manager(${SM_PSK_SECRET}) 조회 완료"
else
    # ls-api ipsec.secrets에서 현재 PSK 추출
    PSK=$(ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
        "sudo sed -n 's/.*PSK \"\(.*\)\".*/\1/p' /etc/ipsec.secrets 2>/dev/null" || true)
    if [ -n "$PSK" ]; then
        echo "  ✓ PSK: ls-api ipsec.secrets 기존 값 유지"
        echo "  [주의] IaC 재배포 시 PSK가 변경됐을 수 있음"
        echo "         VPN 연결 실패 시 CF 설정 파일에서 PSK 수동 확인 후 재실행"
    else
        echo "  [경고] PSK 조회 실패 — ipsec.secrets의 IP 필드만 교체"
    fi
fi

# ── [3/4] ls-api 접속 확인 ───────────────────────────
echo ""
echo "[3/4] ls-api(${LS_API_IP}) 접속 확인..."
if ! ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" "true" 2>/dev/null; then
    echo ""
    echo "[오류] ls-api SSH 접속 실패. 확인 항목:"
    echo "  1. VirtualBox 실행 여부"
    echo "  2. ls-api VM 부팅 완료 여부"
    echo "  3. Host-only 네트워크 어댑터 활성화 여부"
    exit 1
fi
echo "  ✓ SSH 접속 가능"

# ── [4/4] ipsec 업데이트 및 재시작 ───────────────────
echo ""
echo "[4/4] ipsec 설정 업데이트 및 StrongSwan 재시작..."

# ipsec.conf right= 업데이트
ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
    "sudo sed -i '/right=/s/=.*/=${TUNNEL_IP}/' /etc/ipsec.conf"
echo "  ✓ ipsec.conf: right=${TUNNEL_IP}"

# ipsec.secrets 업데이트
if [ -n "$PSK" ]; then
    LEFTID=$(ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
        "sudo awk 'NF>0{print \$1; exit}' /etc/ipsec.secrets")
    # printf로 PSK 내 특수문자 안전하게 처리, 파이프로 전달 (커맨드라인 노출 없음)
    printf '%s %s : PSK "%s"\n' "$LEFTID" "$TUNNEL_IP" "$PSK" | \
        ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
        "sudo tee /etc/ipsec.secrets > /dev/null && sudo chmod 600 /etc/ipsec.secrets"
    echo "  ✓ ipsec.secrets: 전체 업데이트"
else
    # PSK 미확인 — IP 필드만 교체 (PSK 부분 보존)
    ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
        "sudo sed -i 's/^\([^ ]*\) [^ ]*/\1 ${TUNNEL_IP}/' /etc/ipsec.secrets"
    echo "  ✓ ipsec.secrets: IP만 교체 (PSK 보존)"
fi

# StrongSwan 재시작
echo "  StrongSwan 재시작 중..."
ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
    "sudo systemctl restart strongswan-starter"
sleep 6

# 상태 확인
echo ""
echo "=== VPN 상태 ==="
ssh $SSH_OPTS "${LS_API_USER}@${LS_API_IP}" \
    "sudo ipsec status 2>/dev/null || echo '(상태 정보 없음)'"

echo ""
echo "================================================"
echo " 완료"
echo " ESTABLISHED 확인되면 정상."
echo " 연결 안 되면: sudo ipsec statusall (ls-api에서)"
echo "================================================"

# LifeSync360 프로젝트 진행 기록

---

## 전체 현황 (빠른 확인)

### 온프레미스

| 항목 | 상태 |
|------|------|
| VM 4대 생성 및 네트워크 구성 | ✅ |
| Ansible 초기 배포 (mysql / tokenization / private_api) | ✅ |
| 크로스 VM 연결 및 서비스 검증 | ✅ |
| 초기 데이터 적재 (master_customer 100만 / identity_map 349만 / profile 100만) | ✅ |
| PII 암호화 (representative_name, birth_dt) | ✅ |
| Ansible Vault encrypt 실행 | ✅ |
| private_api DB 접속 환경변수 방식 전환 | ✅ |

### 플랫폼 / 어드민

| 항목 | 상태 |
|------|------|
| lifesync360-platform — Mock 전체 기능 | ✅ |
| lifesync360-platform — Aurora/DynamoDB/Redis 연동 코드 | ✅ (클라우드 배포 전) |
| admin-platform — Mock 전체 기능 | ✅ |
| admin-platform — Aurora/DynamoDB 연동 코드 | ✅ (클라우드 배포 전) |
| GitHub → CodeCommit 미러 CI | ✅ |
| taskdef.json / buildspec.yml / appspec.yaml (platform + admin) | ✅ |
| settings 포인트 Aurora 연동 | ⏳ |
| /api/my-products 운영 연결 | ⏳ |
| upgrade_actions 운영 연결 | ⏳ |

### 클라우드 인프라

| 항목 | 상태 |
|------|------|
| CloudFormation 전체 YAML 작성 | ✅ |
| ECS Blue/Green (CODE_DEPLOY, Green TG, TestListener) | ✅ |
| CodeDeploy / CodePipeline IaC | ✅ |
| ECS 부트스트랩 (DesiredCount=0, public 이미지 직접 참조) | ✅ |
| Site-to-Site VPN Static 라우팅 전환 (BGP → Static) | ✅ |
| taskdef.json ACCOUNT_ID 치환 | ✅ |
| EC2 Control Node IaC (infra/compute/control-node.yaml) | ✅ |
| Deploy Server 구축 (Flask 9000, systemd, setup-ssh-keys.sh) | ✅ |
| DEPLOY_TOKEN Secrets Manager 분리 (/etc/deploy-server/env) | ✅ |
| hosts.yml ProxyJump 설정 (ls-db / ls-token → ls-api 경유) | ✅ |
| Secrets Manager 값 입력 (lifesync/* 전체) | ⏳ 배포 시점 |
| CloudFormation 스택 실제 배포 | ⏳ |

---

## 온프레미스 구축 Runbook

처음부터 다시 구성할 때 이 순서대로 실행.

---

### Step 1 — VirtualBox VM 생성 및 네트워크 구성

**Host-Only 어댑터 생성 (VirtualBox GUI)**
```
VirtualBox → 파일 → 호스트 네트워크 관리자 → 만들기
  IP: 192.168.56.1 / 서브넷마스크: 255.255.255.0
  DHCP 서버: 비활성화
```

**VM 4대 생성**

| VM 이름 | IP | 역할 | 메모리 | 디스크 |
|---------|-----|------|--------|--------|
| ls-vpngw | 192.168.56.10 | VPN Gateway (초기 구축 시 임시 Ansible Control Node 겸용) | 1GB | 20GB |
| ls-db    | 192.168.56.11 | MySQL | 2GB | 50GB |
| ls-token | 192.168.56.12 | Tokenization Service | 1GB | 20GB |
| ls-api   | 192.168.56.13 | Private API + Cron | 1GB | 20GB |

> **Note**: Ansible Control Node 역할은 Step 11에서 EC2로 이전. ls-vpngw는 VPN 터널 유지 전용으로 남음.

공통 설정: Ubuntu 22.04 / 어댑터1=NAT / 어댑터2=Host-Only(192.168.56.x 고정 IP)

> **ls-api 전용 추가 설정**: VPN 터널용 브리지 어댑터 필요.
> `VirtualBox → ls-api VM → 설정 → 네트워크 → 어댑터3 → 브리지 어댑터 → 실제 NIC 선택 (Wi-Fi 또는 이더넷)`

---

### Step 2 — VM 공통 초기 설정 (각 VM에서)

```bash
# ansible 유저 생성
sudo useradd -m -s /bin/bash ansible
sudo usermod -aG sudo ansible
echo "ansible ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/ansible

# Host-Only 어댑터 고정 IP 설정 (ls-db 예시, IP만 VM마다 변경)
sudo tee /etc/netplan/01-netcfg.yaml << 'EOF'
network:
  version: 2
  ethernets:
    enp0s8:
      dhcp4: no
      addresses: [192.168.56.11/24]
EOF
sudo netplan apply

# 설정 확인
ip addr show enp0s8
# → 192.168.56.x/24 확인
```

VirtualBox 공유 폴더(Step 7) 사용을 위한 Guest Additions 설치 (ls-db에서):
```bash
sudo apt install -y virtualbox-guest-utils
sudo usermod -aG vboxsf ansible
sudo reboot
```

---

### Step 3 — SSH 키 생성 및 배포

> 개발 PC(VirtualBox 호스트) 또는 ls-vpngw에서 실행. 3개 VM에 직접 접근 가능한 환경 기준.
> EC2 Control Node에서 배포할 경우 → Step 12의 `setup-ssh-keys.sh` 사용.

```bash
# SSH 키 생성 (최초 1회, ~/.ssh 없으면 먼저 생성)
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lifesync360-onprem.pem -N ""

# 각 VM에 공개키 등록 (3개 VM 직접 접근 가능한 환경에서)
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.11
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.12
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.13

# 확인
ssh -i ~/.ssh/lifesync360-onprem.pem ansible@192.168.56.13 "echo ok"
```

---

### Step 4 — Ansible 초기 설정 및 연결 확인 (초기 구축 전용)

> **이 단계는 초기 온프레미스 구축 시 ls-vpngw를 임시 Control Node로 쓸 때만 필요.**
> EC2 Control Node가 준비되면 Step 11~12로 대체됨.

```bash
ssh ansible@192.168.56.10

# Ansible 설치
sudo apt update && sudo apt install -y ansible python3-pip

# 레포 클론
git clone <repo_url> /opt/ansible/onprem-prod-repo
cd /opt/ansible/onprem-prod-repo

# SSH 키 복사 (개발 PC → ls-vpngw는 공유 폴더 또는 scp 이용)
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cp /mnt/downloads/lifesync360-onprem.pem ~/.ssh/
chmod 600 ~/.ssh/lifesync360-onprem.pem

# 연결 확인 — 3개 VM 모두 pong 이면 정상
ansible all -m ping -i ansible/inventory/hosts.yml
# ls-vpngw는 3개 VM 직접 접근 가능하므로 ProxyJump 불필요
```

---

### Step 5 — Ansible 첫 배포

> Vault 암호화 전이면 `--ask-vault-pass` 없이 실행. Step 9 이후엔 vault-pass 필요.

```bash
# ls-vpngw 또는 개발 PC에서 (초기 구축 시)
cd /opt/ansible/onprem-prod-repo

# Vault 암호화 전
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml

# Vault 암호화 후 (Step 9 완료 시)
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass
# 또는 패스워드 직접 입력
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --ask-vault-pass
```

배포 후 서비스 상태 확인:
```bash
ssh -i ~/.ssh/lifesync360-onprem.pem ansible@192.168.56.11 "sudo systemctl status mysql"
ssh -i ~/.ssh/lifesync360-onprem.pem ansible@192.168.56.12 "sudo systemctl status tokenization"
ssh -i ~/.ssh/lifesync360-onprem.pem ansible@192.168.56.13 "sudo systemctl status private-api nginx"
```

---

### Step 5-1 — AWS Site-to-Site VPN 설정 (ls-api ↔ AWS TGW)

> 상세 내용 및 트러블슈팅은 `aws-vpn-setup.md` 참고.

**① ls-api에 StrongSwan 설치**
```bash
ssh ansible@192.168.56.13
sudo apt update && sudo apt install -y strongswan strongswan-pki libcharon-extra-plugins
```

**② 브리지 어댑터 IP 및 공인 IP 확인**
```bash
# 브리지 어댑터 IP (enp0s9, left= 값)
ip addr show enp0s9 | grep 'inet '
# → 예: 172.16.1.73

# 공유기 공인 IP (leftid= 값, AWS Customer Gateway에 등록할 IP)
curl ifconfig.me
```

**③ AWS 콘솔 — Customer Gateway 및 VPN Connection 생성**
```
VPC → Customer Gateways → Create
  IP Address: ②의 공인 IP
  BGP ASN: 65000

VPC → Site-to-Site VPN → Create
  Customer Gateway: 위에서 생성한 것
  Transit Gateway 선택
  Routing: Static
  Static IP Prefixes: <브리지 어댑터 IP>/32  (예: 172.16.1.73/32)

생성 후 → Download Configuration → Vendor: Generic
  → 파일에서 터널 IP(Outside IP)와 PSK 값 확인
```

**④ /etc/ipsec.conf 설정**
```bash
sudo tee /etc/ipsec.conf << 'EOF'
config setup
    charondebug="ike 2, knl 2, cfg 2"

conn aws-vpn
    authby=secret
    left=<브리지 어댑터 IP>
    leftid=<공유기 공인 IP>
    leftsubnet=<브리지 어댑터 IP>/32
    right=<AWS VPN 터널 IP>
    rightsubnet=<Management VPC CIDR>
    ike=aes256-sha256-modp2048
    esp=aes256-sha256
    keyingtries=%forever
    keyexchange=ikev2
    forceencaps=yes
    auto=start
EOF
```

**⑤ /etc/ipsec.secrets 설정**
```bash
sudo tee /etc/ipsec.secrets << 'EOF'
<공유기 공인 IP> <AWS VPN 터널 IP> : PSK "<다운로드한 PSK값>"
EOF
sudo chmod 600 /etc/ipsec.secrets
```

**⑥ IP 포워딩 및 StrongSwan 시작**
```bash
echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

sudo systemctl enable strongswan-starter
sudo systemctl restart strongswan-starter
```

**⑦ 연결 확인**
```bash
sudo ipsec status
# → aws-vpn[1]: ESTABLISHED ... 확인
# → aws-vpn{1}: INSTALLED, TUNNEL 확인

# EC2 Control Node까지 통신 확인 (VPN 연결 후)
ping <EC2 Private IP>
```

---

### Step 6 — 서비스 검증

```bash
# ls-api health (Nginx 경유 80포트)
curl http://192.168.56.13/health
# → {"status":"ok"}

# ls-token health
curl http://192.168.56.12:8000/health
# → {"status":"ok"}

# tokenize 정상 호출
curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "phone_number", "value": "01012345678"}'
# → {"token_id": "xxxx-xxxx-xxxx-xxxx"}

# dedup — 같은 값 두 번 호출 → token_id 동일해야 함
curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "phone_number", "value": "01099999999"}'
# (두 번 실행 후 token_id 비교)

# 허용되지 않은 필드 → 400
curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "address", "value": "서울시 강남구"}'
# → HTTP 400 {"detail":"Field 'address' not in allowed fields"}

# 없는 token_id detokenize → 404
curl http://192.168.56.12:8000/detokenize/00000000-0000-0000-0000-000000000000
# → HTTP 404

# 크로스 VM MySQL 연결 (ls-db)
ssh ansible@192.168.56.11
mysql -u lifesync -p lifesync_onprem -e "SHOW TABLES;"
```

---

### Step 7 — 초기 데이터 적재

**파일 전송 — VirtualBox 공유 폴더**
```
VirtualBox GUI → ls-db VM → 설정 → 공유 폴더 → 추가
  호스트 경로: C:\Users\campus3S026\Downloads
  폴더 이름: downloads
  자동 마운트: 체크 / 영구: 체크
→ VM 재기동
```

**ls-db VM에서 마운트 및 파일 복사**
```bash
ssh ansible@192.168.56.11
sudo mkdir -p /mnt/downloads
sudo mount -t vboxsf downloads /mnt/downloads
ls /mnt/downloads/*.csv

# MySQL secure_file_priv 경로로 복사
sudo cp /mnt/downloads/customer_master.csv      /var/lib/mysql-files/
sudo cp /mnt/downloads/customer_identity_map.csv /var/lib/mysql-files/
sudo cp /mnt/downloads/customer_profile.csv      /var/lib/mysql-files/
```

**스키마 적용 (데이터 적재 전 필수)**
```bash
mysql -u root -p lifesync_onprem < /mnt/downloads/onprem_schema.sql
```

**데이터 적재**
```bash
mysql -u root -p lifesync_onprem
```

```sql
USE lifesync_onprem;

-- ① master_customer (100만건)
LOAD DATA INFILE '/var/lib/mysql-files/customer_master.csv'
INTO TABLE master_customer
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(global_id, representative_name, birth_dt, gender, nationality);

-- ② customer_identity_map (349만건)
LOAD DATA INFILE '/var/lib/mysql-files/customer_identity_map.csv'
INTO TABLE customer_identity_map
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(global_id, company_id, affiliate_customer_id);

-- ③ customer_360_profile (100만건 — global_id만 적재, 나머지 38컬럼 @변수로 버림)
LOAD DATA INFILE '/var/lib/mysql-files/customer_profile.csv'
INTO TABLE customer_360_profile
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
  @global_id,
  @고객유형, @나이, @성별, @소득구간, @건강상태, @신용등급, @라이프스타일, @시나리오,
  @가입계열사수, @은행가입, @카드가입, @보험가입, @인터넷보험가입, @병원가입,
  @헬스케어가입, @증권가입, @웨어러블가입,
  @은행ID, @카드ID, @보험ID, @인터넷보험ID, @병원ID, @헬스케어ID, @증권ID, @웨어러블ID,
  @은행동의, @카드동의, @보험동의, @인터넷보험동의, @병원동의, @헬스케어동의, @증권동의, @웨어러블동의,
  @혈당, @지질, @간기능, @신장기능
)
SET global_id = @global_id, grade = 'BASIC';
```

**적재 결과 확인**
```sql
SELECT COUNT(*) FROM master_customer;         -- 1,000,000
SELECT COUNT(*) FROM customer_identity_map;   -- 3,498,623
SELECT COUNT(*) FROM customer_360_profile;    -- 1,000,000
SELECT * FROM master_customer LIMIT 3;
SELECT * FROM customer_identity_map WHERE global_id = 'G000000001';
```

---

### Step 8 — PII 암호화

> 상세 내용은 `pii-encryption-guide.md` 참고. 핵심 실행 순서만 아래 정리.

**① 암호화 키 생성 (ls-vpngw에서)**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 출력된 키를 복사해둘 것 — 잃어버리면 복호화 불가
```

**② Vault 파일에 키 등록**
```bash
cd /opt/ansible/onprem-prod-repo
cat > ansible/inventory/group_vars/private_api/vault.yml << 'EOF'
vault_pii_aes_key: "<①에서 생성한 키>"
EOF
```

**③ ls-db 컬럼 타입 변경**
```bash
ssh ansible@192.168.56.11
mysql -u root -p lifesync_onprem
```
```sql
ALTER TABLE master_customer
  MODIFY representative_name VARCHAR(300),
  MODIFY birth_dt VARCHAR(100);
EXIT;
```

**④ 마이그레이션 스크립트 실행 (ls-vpngw에서, 약 5~10분)**
```bash
pip3 install cryptography pymysql --break-system-packages

export PII_AES_KEY=<①에서 생성한 키>
export DB_HOST=192.168.56.11
export DB_USER=lifesync
export DB_PASS=<MySQL lifesync 패스워드>
python3 /opt/ansible/onprem-prod-repo/db/migrate_pii_encrypt.py
```

**⑤ 암호화 확인**
```bash
ssh ansible@192.168.56.11
mysql -u root -p lifesync_onprem -e \
  "SELECT global_id, representative_name FROM master_customer LIMIT 3;"
# representative_name 값이 'gAAAAAB...' 형태면 정상
```

**⑥ ls-api 재배포 및 복호화 검증**
```bash
# ls-vpngw에서
cd /opt/ansible/onprem-prod-repo
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml \
  --limit ls-api --ask-vault-pass

# 복호화 확인 — 한글 이름이 정상 출력되면 성공
curl http://192.168.56.13/internal/customer/G000000001
```

---

### Step 9 — Ansible Vault 암호화

```bash
# ls-vpngw에서
# vault 패스워드 파일 생성 (Ansible 실행 시 자동 참조)
echo "<vault 패스워드>" > ~/.vault_pass
chmod 600 ~/.vault_pass

cd /opt/ansible/onprem-prod-repo

# tokenization vault
ansible-vault encrypt ansible/inventory/group_vars/tokenization/vault.yml
git add ansible/inventory/group_vars/tokenization/vault.yml
git commit -m "feat(vault): tokenization vault 암호화 적용"

# private_api vault (Step 8 완료 후)
ansible-vault encrypt ansible/inventory/group_vars/private_api/vault.yml
git add ansible/inventory/group_vars/private_api/
git commit -m "feat(vault): private_api vault 암호화 적용"

git push
```

이후 Ansible 실행 시:
```bash
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --ask-vault-pass
```

---

### Step 10 — Secrets Manager 등록

CloudFormation 스택 배포 전에 아래 시크릿을 모두 등록해야 함.
Aurora/Redis 엔드포인트는 스택 배포 후 확정되므로 플레이스홀더로 먼저 생성 후 업데이트.

```bash
# ── 플랫폼 / 어드민 ──────────────────────────────
aws secretsmanager create-secret \
  --name lifesync/aurora \
  --secret-string '{"host":"<Aurora 엔드포인트>","user":"<DB 유저>","password":"<DB 패스워드>"}' \
  --region ap-northeast-2

aws secretsmanager create-secret \
  --name lifesync/jwt \
  --secret-string '{"secret":"<JWT 서명 키>"}' \
  --region ap-northeast-2

aws secretsmanager create-secret \
  --name lifesync/redis \
  --secret-string '{"host":"<ElastiCache 엔드포인트>"}' \
  --region ap-northeast-2

aws secretsmanager create-secret \
  --name lifesync/admin \
  --secret-string '{"username":"<관리자 계정>","password":"<관리자 패스워드>","secret_key":"<Flask 세션 키>"}' \
  --region ap-northeast-2

# ── EC2 Control Node (아래 3개는 CloudFormation UserData가 참조 — 배포 전 필수) ──
aws secretsmanager create-secret \
  --name lifesync/ansible-vault \
  --secret-string '{"password":"<Ansible Vault 패스워드>"}' \
  --region ap-northeast-2

aws secretsmanager create-secret \
  --name lifesync/ansible-vm \
  --secret-string '{"password":"<온프레미스 ansible 계정 패스워드>"}' \
  --region ap-northeast-2

aws secretsmanager create-secret \
  --name lifesync/deploy-token \
  --secret-string '{"token":"<X-Deploy-Token 값>"}' \
  --region ap-northeast-2
```

Aurora/Redis 엔드포인트 확정 후 값 업데이트:
```bash
aws secretsmanager update-secret \
  --secret-id lifesync/aurora \
  --secret-string '{"host":"<확정된 Aurora 엔드포인트>","user":"<DB 유저>","password":"<DB 패스워드>"}' \
  --region ap-northeast-2

aws secretsmanager update-secret \
  --secret-id lifesync/redis \
  --secret-string '{"host":"<확정된 ElastiCache 엔드포인트>"}' \
  --region ap-northeast-2
```

---

### Step 11 — EC2 Control Node CloudFormation 배포

> VPN이 연결된 상태에서 배포해야 UserData [5/6] SSH 키 배포 단계가 성공함.

```bash
aws cloudformation deploy \
  --template-file infra/compute/control-node.yaml \
  --stack-name lifesync-control-node \
  --parameter-overrides \
    SubnetId=<Management VPC 서브넷 ID> \
    VpcId=<Management VPC ID> \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-2
```

배포 후 EC2 정보 확인 (Step 12 SSM 접속 및 Step 13 vars.yml 업데이트에 필요):
```bash
aws cloudformation describe-stacks \
  --stack-name lifesync-control-node \
  --query 'Stacks[0].Outputs' \
  --region ap-northeast-2
# → InstanceId, PrivateIp, DeployServerUrl 출력

# InstanceId만 추출
aws cloudformation describe-stacks \
  --stack-name lifesync-control-node \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text --region ap-northeast-2
```

---

### Step 12 — Control Node 초기화 확인 및 연결 테스트

UserData 완료까지 약 5~10분 소요. SSM Session Manager로 접속해서 확인.

```bash
# SSM으로 접속 (SSH 키 없이)
aws ssm start-session --target <InstanceId> --region ap-northeast-2

# 초기화 완료 여부 확인
cat /tmp/control-node-ready       # "done" 이면 정상
cat /var/log/control-node-init.log  # 상세 로그

# Deploy Server 상태 확인
sudo systemctl status deploy-server
curl http://localhost:9000/health
# → {"status": "ok"}

# Ansible 연결 확인
ansible all -m ping \
  -i /opt/ansible/onprem-prod-repo/ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass
# → ls-api: pong, ls-db: pong, ls-token: pong 확인
```

SSH 키 배포가 실패했을 경우 수동 실행:
```bash
# SSM 세션에서
sudo -u ubuntu bash /opt/ansible/onprem-prod-repo/infra/deploy-server/setup-ssh-keys.sh
# ANSIBLE_PASS 환경변수 없으면 대화형으로 패스워드 입력
```

---

### Step 13 — vars.yml control_node_url 업데이트 및 재배포

EC2 Control Node Private IP를 확인 후 레포 업데이트.

```yaml
# onprem-prod-repo/ansible/inventory/group_vars/private_api/vars.yml
deploy_token: "lifesync-deploy-token-2026"
control_node_url: "http://<EC2-Private-IP>:9000"   # ← 실제 IP로 변경
```

```bash
git add ansible/inventory/group_vars/private_api/vars.yml
git commit -m "chore: control_node_url EC2 Private IP 반영"
git push

# EC2 Control Node에서 레포 최신화 후 ls-api 재배포
cd /opt/ansible/onprem-prod-repo
git pull
ansible-playbook ansible/site.yml \
  -i ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass \
  --limit ls-api
```

---

### Step 14 — CI/CD 트리거 전체 흐름 테스트

ls-api VM에서 배포 트리거 → EC2 Control Node → ansible-playbook 실행까지 확인.

```bash
# ls-api VM에서
TOKEN=$(sudo grep DEPLOY_TOKEN /etc/systemd/system/private-api.service | cut -d= -f3-)

curl -X POST http://localhost:8000/internal/deploy \
  -H "X-Deploy-Token: ${TOKEN}"
# → {"status": "triggered"}

# EC2 Control Node에서 로그 확인
tail -f /var/log/ansible-deploy.log
# ansible-playbook 실행 로그 확인
```

---

## 매일 아침 운영 절차 (IaC 재배포 후)

매일 9AM IaC가 VPN Connection을 재생성하므로 AWS 터널 IP가 바뀜.
VirtualBox와 VM을 먼저 켠 후 아래 순서로 진행.

### 1단계 — VPN 터널 재연결 (로컬 PC에서)

```bash
# AWS CLI 인증 확인
aws sts get-caller-identity

# 터널 IP 자동 갱신 및 StrongSwan 재시작
bash scripts/update-vpn-tunnel.sh

# VPN Name 태그 모를 경우 Connection ID 직접 지정
VPN_CONNECTION_ID=vpn-xxxxxxxxx bash scripts/update-vpn-tunnel.sh
```

출력에 `ESTABLISHED` 확인되면 VPN 연결 완료.
연결 실패 시 → `local-test-troubleshooting.md` "IaC 재배포 후 VPN 터널 끊김" 항목 참고.

### 2단계 — EC2 Control Node 접속 (Control Node 재생성 시 InstanceId 갱신)

```bash
# Control Node 재생성 시 새 InstanceId 조회
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name lifesync-control-node \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text --region ap-northeast-2)

# SSM으로 EC2 접속
aws ssm start-session --target $INSTANCE_ID --region ap-northeast-2

# 온프레미스 VM 연결 확인
ansible all -m ping \
  -i /opt/ansible/onprem-prod-repo/ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass
# ls-api / ls-db / ls-token 모두 pong 이어야 함
```

---

## 플랫폼 / 어드민 개발 이력 (참고)

### 2026-04 초중순
- LifeSync360 RFP v7, 아키텍처 설계 v2.8, 데이터셋 정의서 v9
- lifesync360-platform Flask 초기 버전 (로그인/동의/홈/상품/설정)
- Ansible 레포 초기 구성 (mysql / tokenization / private_api role)

### 2026-05-04
- platform Aurora 연동 코드 (register/login/me/consent)
- templates 수정 (login 리다이렉트, consent 전체선택, settings 동의상태 로드)
- buildspec.yml IMAGE_TAG 누락 버그 수정 / taskdef.json 리소스 조정

### 2026-05-05
- platform DynamoDB 연동 (dashboard 점수), Redis 연동 (추천 캐시)
- admin-platform 신규 구축 (overview / users / user_detail, 포트 5001)
- lambda/gcp_result_ingest build.sh

### 2026-05-06
- Site-to-Site VPN 연결 (TGW ↔ ls-api)
- ls-token 자격증명 영속성 수정 (systemd 템플릿 환경변수 주입)
- taskdef.json 컨테이너명 / 패밀리명 정합성 수정 (platform)
- admin-platform gunicorn 전환 / CI 완성 / taskdef.json + buildspec.yml + appspec.yaml 신규
- lambda/customer_profile_sync 작성 (로그인 시 global_id 조회)
- GitHub Actions Monorepo 통합 (루트 .github/workflows/)
- 보안 감사 — 하드코딩 민감정보 5건 제거 / Ansible Vault 패턴 구성

### 2026-05-07
- platform UI: 건강점수 모달, 지표 pills, MY탭 세그먼트, 계열사 보유상품 드릴다운
- 업그레이드 액션 개인화 엔진 (upgrade_actions_engine.py)
- 동의 기반 접근 제어 (/api/my-products 403)
- Mock 3명 유저 (PLATINUM/GOLD/SILVER) + 계정별 동의 범위
- ECR/ECS IaC 전면 수정 (레포명, Blue/Green 전환, DesiredCount=0)
- ALB Green TG + TestListener 추가
- CodeDeploy Blue/Green / CodePipeline CodeDeployToECS 전환
- buildspec.yml imageDetail.json 전환 (CodeDeployToECS 포맷)
- 초기 데이터 3종 적재 완료 (→ Step 7)

### 2026-05-08
- PII 암호화 설계 및 가이드 작성 (→ pii-encryption-guide.md)
- PII 암호화 구현 완료 — app.py, service.j2, tasks/main.yml, hosts.yml, onprem_schema.sql 5개 파일 수정
- master_customer 100만 건 Fernet 암호화 마이그레이션 완료 (representative_name, birth_dt)
- private_api DB 접속 방식 변경 — Secrets Manager → 환경변수 (DB_HOST, DB_USER, DB_PASS)
- Ansible Vault 암호화 완료 (private_api, tokenization)
- onprem-prod-repo README 최신화
- MySQL root 비밀번호 재설정 (skip-grant-tables 복구)
- Site-to-Site VPN BGP → Static 라우팅 전환 (→ aws-vpn-setup.md 문제3 참고)

### 2026-05-11
- admin-platform 대시보드 사이드바 탭 네비게이션 개편 (overview 4탭, user_detail 5탭)
- admin-platform 동의현황 / 추천이력 / 제휴사매핑 / 활성캠페인 / 최근추천 섹션 추가
- EC2 Control Node CloudFormation IaC 작성 (infra/compute/control-node.yaml)
  - IAM Role: Secrets Manager + CodeCommit + SSM
  - UserData: 패키지 설치 → CodeCommit 클론 → vault 패스워드 → Deploy Server → SSH 키 배포
- Deploy Server 구축 (infra/deploy-server/)
  - Flask 9000포트, /health + /deploy 엔드포인트, X-Deploy-Token 인증
  - DEPLOY_TOKEN 하드코딩 → Secrets Manager(lifesync/deploy-token) → /etc/deploy-server/env 분리
- setup-ssh-keys.sh: mkdir -p ~/.ssh 누락 수정, ~/.vault_pass 없을 때 안전 처리
- hosts.yml: ls-db / ls-token에 ansible_ssh_common_args ProxyJump(via ls-api) 추가

---

## 배포 전 필수 처리 항목

| 항목 | 담당 | 참고 파일 |
|------|------|-----------|
| PII 암호화 | ~~온프레미스~~ ✅ 완료 | pii-encryption-guide.md |
| Ansible Vault encrypt 실행 | ~~온프레미스~~ ✅ 완료 | Step 9 |
| taskdef.json ACCOUNT_ID 치환 | ~~배포 담당자~~ ✅ 완료 | platform + admin 총 11곳 |
| Secrets Manager 값 입력 (lifesync/aurora, jwt, redis, admin) | 배포 담당자 | cloud-deploy-procedure.md 2단계 |
| Secrets Manager 값 입력 (lifesync/ansible-vault, ansible-vm, deploy-token) | 배포 담당자 | Control Node IaC 배포 전 필수 |
| GitHub Secrets 등록 | 배포 담당자 | AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY |
| Parameter Store 등록 | 배포 담당자 | /lifesync360/ecr-uri / ecr-uri-admin |
| CloudFormation 스택 배포 | IaC 담당자 | cloud-deploy-procedure.md |
| Lambda TGW Attachment | IaC 담당자 | lambda-to-onprem-network.md |
| 동의 고객 선별 Lambda 구현 | 개발 | ETL 파이프라인 AWS→GCP 전송 전 consent 필터링 |
| settings 포인트 Aurora 연동 | 개발 | /api/points 엔드포인트 추가 |
| /api/my-products 운영 연결 | 개발 | Aurora consent 테이블 체크 |
| upgrade_actions 운영 연결 | 개발 | DynamoDB/Aurora 실데이터 ctx |

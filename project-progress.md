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
| schema.sql 아키텍처 ERD 기준 전면 재작성 | ✅ |
| 실서버 스키마 마이그레이션 (컬럼 RENAME/DROP 적용) | ⏳ |

### Lambda

| 항목 | 상태 |
|------|------|
| gcp_result_ingest — GRADE_MAP / SQL / DB 연결 수정 | ✅ |
| customer_profile_sync — on-prem 연결 전환 / 컬럼명 수정 | ✅ |
| consent_filter — 신규 작성 (동의 고객 S3 추출) | ✅ |
| consent_filter — IaC 배포 (Lambda / SG / IAM / EventBridge) | ⏳ IaC 담당 |
| onprem_customer_query Lambda — 신규 작성 (Platform VPC 직접 VPN) | ✅ |
| onprem_customer_query Lambda — IaC 배포 (Platform VPC 서브넷 / SG / 환경변수) | ⏳ IaC 담당 |

### 플랫폼 / 어드민

| 항목 | 상태 |
|------|------|
| lifesync360-platform — Mock 전체 기능 | ✅ |
| lifesync360-platform — Aurora/DynamoDB/Redis 연동 코드 | ✅ (클라우드 배포 전) |
| lifesync360-platform — 아키텍처 기준 컬럼명 전면 통일 | ✅ |
| lifesync360-platform — 온프레미스 인증/동의 Lambda 연동 (_call_onprem) | ✅ |
| lifesync360-platform — 로컬 테스트 JWT 발급 환경 (make_token.py) | ✅ |
| lifesync360-platform — 포인트 기능 제거 (Aurora 테이블 없음, 화면 미노출) | ✅ |
| lifesync360-platform — Service-DB 스키마 기준 쿼리 정합성 검증 완료 | ✅ |
| private_api — 아키텍처 기준 컬럼명/파라미터명 전면 통일 | ✅ |
| global_customer_id → global_id 전환 (schema.sql 2개 / lambda handler 2개) | ✅ |
| admin-platform — Mock 전체 기능 | ✅ |
| admin-platform — Mock 데이터 실제 스키마 기준 정합 (domain/consent_flag/clicked_flag 등) | ✅ |
| admin-platform — Aurora 쿼리 전면 수정 (캠페인/추천이력/퍼널/dashboard log) | ✅ |
| admin-platform — DynamoDB 기반 등급분포/유저목록 전환 | ✅ |
| admin-platform — 온프레미스 Lambda 헬퍼 (_call_onprem) 추가 | ✅ |
| admin-platform — user_detail URL global_id 기반 전환 | ✅ |
| GitHub → CodeCommit 미러 CI | ✅ |
| taskdef.json / buildspec.yml / appspec.yaml (platform + admin) | ✅ |
| /api/me name/grade 연동 (PII 복호화 + DynamoDB grade) | ⏳ |
| /api/my-products 운영 연결 | ⏳ |
| upgrade_actions 운영 연결 | ⏳ |
| Aurora users_ref 동기화 테이블 설계 및 구축 (어드민 유저목록 이름/이메일 표시) | ⏳ |

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

### Step 11 — EC2 Control Node CloudFormation 배포 (14a → 14b → 14c)

> IAM(14a) → EC2(14b) → SSM Association(14c) 순서로 배포. 14b 출력을 14c에 넘겨야 하므로 반드시 순서 지킬 것.

```bash
# ── 14a: IAM 롤 + 인스턴스 프로파일 ──────────────────────────────
aws cloudformation deploy \
  --template-file 14a-ansible-iam.yaml \
  --stack-name lifesync-dev-ansible-iam \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-2

# 14a 출력 확인 (14b 파라미터에 사용)
PROFILE_NAME=$(aws cloudformation describe-stacks \
  --stack-name lifesync-dev-ansible-iam \
  --query 'Stacks[0].Outputs[?OutputKey==`AnsibleControlNodeInstanceProfileName`].OutputValue' \
  --output text --region ap-northeast-2)
echo "Profile: $PROFILE_NAME"

# ── 14b: EC2 + UserData ───────────────────────────────────────────
# AmiId: EC2 콘솔에서 AL2023 최신 AMI ID 확인
# ManagementSubnetId: Management VPC private subnet ID
# ManagementSgId: Management VPC SG ID (SSM 아웃바운드 443 허용 필요)
aws cloudformation deploy \
  --template-file 14b-ansible-ec2.yaml \
  --stack-name lifesync-dev-ansible-ec2 \
  --parameter-overrides \
    AmiId=<AL2023 AMI ID> \
    InstanceType=t3.small \
    ManagementSubnetId=<Management VPC private subnet ID> \
    ManagementSgId=<Management VPC SG ID> \
    AnsibleControlNodeInstanceProfileName=$PROFILE_NAME \
  --region ap-northeast-2

# 14b 출력 확인 (14c 파라미터에 사용)
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name lifesync-dev-ansible-ec2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AnsibleControlInstanceId`].OutputValue' \
  --output text --region ap-northeast-2)
echo "Instance ID: $INSTANCE_ID"

# ── 14c: SSM Association (공개키 SSM 등록 + 온프레미스 푸시) ──────
aws cloudformation deploy \
  --template-file 14c-ansible-key-publish.yaml \
  --stack-name lifesync-dev-ansible-key-publish \
  --parameter-overrides \
    AnsibleControlInstanceId=$INSTANCE_ID \
  --region ap-northeast-2
```

---

### Step 12 — Control Node 초기화 확인 및 연결 테스트

UserData 완료까지 약 5~15분 소요 (ansible-core venv 설치 포함). SSM Session Manager로 접속해서 확인.

```bash
# SSM으로 접속 (SSH 키 없이)
aws ssm start-session --target <AnsibleControlInstanceId> --region ap-northeast-2

# ── EC2 내부에서 확인 ──────────────────────────────────────────
# UserData 로그 (14b 완료 시 마지막 줄에 "14b 완료:" 포함됨)
sudo tail -100 /var/log/ansible-bootstrap.log

# SSH 키 생성 확인
ls -la /home/ansible/.ssh/
# → id_rsa (600), id_rsa.pub (644) 존재해야 함

# Ansible venv 확인
/opt/ansible-venv/bin/ansible --version

# Ansible 연결 확인 (VPN 연결 상태에서만 성공)
ansible all -m ping \
  -i /opt/ansible/onprem-prod-repo/ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass
# → ls-api: pong, ls-db: pong, ls-token: pong 확인
```

14c SSM Association 결과 확인 (로컬 PC에서):
```bash
# 공개키가 SSM Parameter Store에 올라갔는지 확인
aws ssm get-parameter \
  --name /lifesync/dev/ansible/public-key \
  --region ap-northeast-2 \
  --query Parameter.Value --output text
# → ssh-rsa AAAA... 형태면 정상
```

SSH 키 미생성 시 수동 복구 (SSM 세션 내부에서):
```bash
sudo install -d -m 0700 -o ansible -g ansible /home/ansible/.ssh
sudo -u ansible ssh-keygen -t rsa -b 4096 -N "" -f /home/ansible/.ssh/id_rsa -q
sudo chown -R ansible:ansible /home/ansible/.ssh
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
# PSK를 Secrets Manager에 등록한 경우 (lifesync/vpn-psk)
bash scripts/update-vpn-tunnel.sh

# PSK를 직접 지정할 경우 (SM 미등록 시)
VPN_PSK="<PSK값>" bash scripts/update-vpn-tunnel.sh

# VPN Name 태그 모를 경우 Connection ID 직접 지정
VPN_CONNECTION_ID=vpn-xxxxxxxxx bash scripts/update-vpn-tunnel.sh
```

출력에 `ESTABLISHED` 확인되면 VPN 연결 완료.
연결 실패 시 → `local-test-troubleshooting.md` "IaC 재배포 후 VPN 터널 끊김" 항목 참고.

### 2단계 — EC2 Control Node 접속 (Control Node 재생성 시 InstanceId 갱신)

```bash
# Control Node 재생성 시 새 InstanceId 조회 (EC2 Name 태그 기준)
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=lifesync-dev-management-ec2-ansible" \
            "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text --region ap-northeast-2)

# 또는 CF Output에서 조회
# INSTANCE_ID=$(aws cloudformation describe-stacks \
#   --stack-name lifesync-dev-ansible-ec2 \
#   --query 'Stacks[0].Outputs[?OutputKey==`AnsibleControlInstanceId`].OutputValue' \
#   --output text --region ap-northeast-2)

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

### 2026-05-13 (2차)

- **consent_filter Lambda 신규 작성** (`lambda/consent_filter/`)
  - 역할: Glue/EMR 실행 전 온프레미스 MySQL `consent` 테이블 조회 → 동의 고객 gzip CSV를 S3에 저장
  - `handler.py`, `requirements.txt`(pymysql==1.1.1), `build.sh` 작성
  - 도메인별 동의 피벗 SQL (`MAX(CASE WHEN domain = ... AND consent_flag = 'Y')`)
  - `SSDictCursor` 서버사이드 커서로 스트리밍 처리 — 100만 건 이상도 Lambda 메모리 초과 없음
  - Glue Job 트리거(`--consent_s3_path`, `--job_date` 인자 전달) + EMR Step 추가 선택 지원
  - 출력 S3 경로: `s3://<OUTPUT_BUCKET>/consent-filter/<YYYYMMDD>/consented_customers.csv.gz`

- **IaC/Glue 전달 문서 작성**
  - `docs/iac-consent-filter-lambda.md`: Lambda 설정, 환경변수, VPC/SG, IAM, EventBridge Scheduler, 배포 절차, 체크리스트
  - `docs/glue-emr-consent-spec.md`: 실행 흐름, S3 파일 스펙, 컬럼 구조, PySpark 코드 예시, EMR 연동, 장애 대응

- **아키텍처 다이어그램(17페이지) ERD 검토 → 온프레미스 스키마/코드 불일치 발견**
  - 실제 배포 schema.sql vs 아키텍처 다이어그램 차이 비교
  - 주요 불일치: `consent_key`→`domain`, `consent_yn`→`consent_flag`, `global_id`→`global_customer_id`, 도메인 값(INS/ONINS/SEC/HLT→INSURANCE/SECURITIES/HEALTHCARE), HOSPITAL 추가, ONINS 제거
  - `gcp_result_ingest`: GRADE_MAP PLATINUM/BRONZE 없는 등급 사용, recommend_rule SQL 컬럼 전체 오류, UPDATE users를 Aurora로 연결하는 버그

- **온프레미스 schema.sql 전면 재작성** (`onprem-prod-repo/ansible/roles/mysql/files/schema.sql`)

  | 테이블 | 변경 내용 |
  |--------|-----------|
  | `users` | `id`→`user_id`, `global_id`→`global_customer_id`, `email`→`login_email`, `name`/`grade` 제거, `mobile`/`user_status`/`consent_completed`/`last_login_dt` 추가 |
  | `master_customer` | `global_id`→`global_customer_id`, `representative_name`/`birth_dt`/`gender`/`nationality` 제거, `customer_status`/`vip_grade`/`customer_type` 추가 |
  | `consent` | `global_id`→`global_customer_id`, `consent_key`→`domain`, `consent_yn`→`consent_flag`, `consent_version`/`revoke_dt` 추가 |
  | `customer_identity_map` | `global_id`→`global_customer_id`, `company_id`→`domain`, `affiliate_customer_id`→`source_customer_id`, `match_type`/`active_flag` 추가 |
  | `customer_360_profile` | `global_id`→`global_customer_id`, `grade` 제거, `gender`/`age_band`/`region`/`income_grade`/`asset_grade`/`wearable_flag`/`health_score`/`finance_score`/`asset_score` 추가 |
  | `customer_pii_secure` | `pii_type`/`encrypted_val` 구조 → `customer_name_enc`/`ssn_enc`/`mobile_enc`/`email_enc`/`address_enc` 필드별 암호화 컬럼으로 재설계 |
  | `matching_audit_log` | `id`/`action_type`/`action_detail` → `audit_id`/`request_id`/`match_rule`/`result`/`match_score`/`consent_dt`/`request_dt` 등 전면 재설계 |
  | `token_map` | `global_id`→`global_customer_id` |

- **코드 전면 수정 (아키텍처 기준 컬럼명 통일)**

  - **`consent_filter/handler.py`**
    - `CONSENT_KEYS`: `INS/ONINS/SEC/HLT/wearable` → `SECURITIES/INSURANCE/HEALTHCARE/HOSPITAL/WEARABLE`
    - SQL: `consent_key`→`domain`, `consent_yn`→`consent_flag`, `global_id`→`global_customer_id AS global_id` (Glue CSV 호환)

  - **`lifesync360-platform/app.py`**
    - `COMPANIES`/`CONSENTS`: 도메인 값 전체 변경, ONINS 제거, HOSPITAL 추가, wearable→WEARABLE
    - consent INSERT: `consent_key`→`domain`, `consent_yn`→`consent_flag`, `global_id`→`global_customer_id`
    - register: `master_customer`/`users` INSERT 컬럼명 통일 (`login_email`, `global_customer_id`, `name`/`grade` 제거)
    - login: `WHERE email` → `WHERE login_email`, `global_id` → `global_customer_id`
    - me: `SELECT` 컬럼명 통일, `name`/`grade`는 NULL 반환 (PII/DynamoDB에서 별도 조회 필요)

  - **`private_api/app.py`**
    - 전체 엔드포인트: `global_id`→`global_customer_id`, `consent_key`→`domain`, `consent_yn`→`consent_flag`
    - `company_id`→`domain`, `affiliate_customer_id`→`source_customer_id`
    - `MatchRequest` 모델 필드명 통일, matching_audit_log INSERT 컬럼명 통일

  - **`gcp_result_ingest/handler.py`**
    - `GRADE_MAP`: VIP→PLATINUM 제거, BRONZE 제거, CARE 추가 (VIP/GOLD/SILVER/BASIC/CARE 1:1 매핑)
    - `GRADE_LEVELS` 전체 제거
    - `_fetch_recommended_ids` SQL: `recommend_rule → category_master → product_master` JOIN 경로로 전면 수정 (`active_flag='Y'`, `target_grade=%s`, `priority_rank` 정렬)
    - `UPDATE users SET grade` 단계 제거 (users에 grade 컬럼 없음, grade는 DynamoDB `dynamic_grade`로 관리)

  - **`customer_profile_sync/handler.py`**
    - DB 연결: `AURORA_HOST` → `AUTH_DB_HOST` (on-prem MySQL)
    - `DB_NAME`: `lifesync` → `lifesync_onprem`
    - 컬럼명: `global_id`→`global_customer_id`
    - Private API 쿼리 파라미터: `company_id` → `domain`
    - 기본값: `DEFAULT_COMPANY='bank'` → `DEFAULT_DOMAIN='BANK'`

- **온프레미스 실서버 마이그레이션 스크립트**

  > `CREATE TABLE IF NOT EXISTS`는 기존 테이블을 변경하지 않음 — Ansible 재배포만으로는 컬럼명이 바뀌지 않는다. 아래 ALTER TABLE 스크립트를 ls-db에서 직접 실행해야 함.
  > 실행 전 필수 백업: `mysqldump -u root -p lifesync_onprem > /backup/pre_migration_$(date +%Y%m%d).sql`

  ```sql
  USE lifesync_onprem;

  -- ① users: id→user_id, global_id→global_customer_id, email→login_email, name/grade 제거, 신규 컬럼 추가
  ALTER TABLE users
    RENAME COLUMN id TO user_id,
    RENAME COLUMN global_id TO global_customer_id,
    RENAME COLUMN email TO login_email,
    DROP COLUMN name,
    DROP COLUMN grade,
    ADD COLUMN mobile VARCHAR(20) NULL,
    ADD COLUMN user_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN consent_completed CHAR(1) NOT NULL DEFAULT 'N',
    ADD COLUMN last_login_dt TIMESTAMP NULL;

  -- ② master_customer: global_id→global_customer_id, PII 컬럼 제거(customer_pii_secure로 분리), 신규 컬럼 추가
  ALTER TABLE master_customer
    RENAME COLUMN global_id TO global_customer_id,
    DROP COLUMN representative_name,
    DROP COLUMN birth_dt,
    DROP COLUMN gender,
    DROP COLUMN nationality,
    ADD COLUMN customer_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN vip_grade VARCHAR(10) NOT NULL DEFAULT 'NORMAL',
    ADD COLUMN customer_type VARCHAR(20) NOT NULL DEFAULT 'INDIVIDUAL',
    CHANGE COLUMN created_dt first_created_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN last_updated_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

  -- ③ consent: global_id→global_customer_id, consent_key→domain, consent_yn→consent_flag, 신규 컬럼 추가
  ALTER TABLE consent
    RENAME COLUMN global_id TO global_customer_id,
    RENAME COLUMN consent_key TO domain,
    RENAME COLUMN consent_yn TO consent_flag,
    ADD COLUMN consent_version VARCHAR(10) NOT NULL DEFAULT 'v1.0',
    ADD COLUMN revoke_dt TIMESTAMP NULL;

  -- ④ customer_identity_map: global_id→global_customer_id, company_id→domain, affiliate_customer_id→source_customer_id
  ALTER TABLE customer_identity_map
    RENAME COLUMN global_id TO global_customer_id,
    RENAME COLUMN company_id TO domain,
    RENAME COLUMN affiliate_customer_id TO source_customer_id,
    ADD COLUMN match_type VARCHAR(10) NOT NULL DEFAULT 'EXACT',
    ADD COLUMN active_flag CHAR(1) NOT NULL DEFAULT 'Y';

  -- ⑤ customer_360_profile: global_id→global_customer_id, grade 제거, 신규 컬럼 추가
  ALTER TABLE customer_360_profile
    RENAME COLUMN global_id TO global_customer_id,
    DROP COLUMN grade,
    ADD COLUMN gender CHAR(1) NULL,
    ADD COLUMN age_band VARCHAR(10) NULL,
    ADD COLUMN region VARCHAR(50) NULL,
    ADD COLUMN income_grade VARCHAR(10) NULL,
    ADD COLUMN asset_grade VARCHAR(10) NULL,
    ADD COLUMN wearable_flag CHAR(1) NOT NULL DEFAULT 'N',
    ADD COLUMN health_score DECIMAL(5,1) NULL,
    ADD COLUMN finance_score DECIMAL(5,1) NULL,
    ADD COLUMN asset_score DECIMAL(5,1) NULL,
    ADD COLUMN lifesync_score DECIMAL(5,1) NULL;

  -- ⑥ token_map: global_id→global_customer_id
  ALTER TABLE token_map
    RENAME COLUMN global_id TO global_customer_id;

  -- ⑦ consent 도메인값 마이그레이션 (구 값 → 신 값)
  UPDATE consent SET domain = 'INSURANCE'  WHERE domain = 'INS';
  UPDATE consent SET domain = 'SECURITIES' WHERE domain = 'SEC';
  UPDATE consent SET domain = 'HEALTHCARE' WHERE domain = 'HLT';
  UPDATE consent SET domain = 'WEARABLE'   WHERE domain = 'wearable';
  DELETE FROM consent WHERE domain = 'ONINS';

  -- ⑧ customer_identity_map 도메인값 마이그레이션
  UPDATE customer_identity_map SET domain = 'INSURANCE'  WHERE domain = 'INS';
  UPDATE customer_identity_map SET domain = 'SECURITIES' WHERE domain = 'SEC';
  UPDATE customer_identity_map SET domain = 'HEALTHCARE' WHERE domain = 'HLT';
  UPDATE customer_identity_map SET domain = 'WEARABLE'   WHERE domain = 'wearable';

  -- ⑨ customer_pii_secure: 구 구조(pii_type/encrypted_val)에서 필드별 컬럼 구조로 재설계
  --    기존 데이터가 없다면 DROP 후 schema.sql 재적용, 있다면 별도 마이그레이션 스크립트 필요
  DROP TABLE IF EXISTS customer_pii_secure;
  CREATE TABLE customer_pii_secure (
      pii_token            VARCHAR(36)  NOT NULL PRIMARY KEY,
      global_customer_id   VARCHAR(30)  NOT NULL,
      customer_name_enc    TEXT,
      ssn_enc              TEXT,
      mobile_enc           TEXT,
      email_enc            TEXT,
      address_enc          TEXT,
      created_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
      updated_dt           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_global (global_customer_id),
      CONSTRAINT fk_pii_customer FOREIGN KEY (global_customer_id)
          REFERENCES master_customer(global_customer_id)
  );
  ```

  > `RENAME COLUMN` 문법은 MySQL 8.0+ 전용. Ubuntu 22.04 기본 MySQL이 8.0이므로 정상 동작.
  > 마이그레이션 완료 후 `SHOW COLUMNS FROM users;` 등으로 컬럼명 확인 필수.

- **로컬 테스트 환경 정비**

  - `lifesync360-platform/app.py` 에서 `JWT_SECRET` 라인이 주석처리된 것 발견
    ```python
    # 기존 (주석처리됨 → 변수 미정의 상태 → 로컬 실행 불가)
    # JWT_SECRET = os.environ['JWT_SECRET']

    # 수정 후 (로컬 fallback + 운영 환경 변수 주입 공존)
    JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-jwt-secret-lifesync360-32bytes!!')
    ```
  - `lifesync360-platform/make_token.py` 신규 작성 — 로컬 테스트용 JWT 토큰 발급
    ```python
    import jwt
    import datetime
    from datetime import timezone

    JWT_SECRET = 'dev-jwt-secret-lifesync360-32bytes!!'

    token = jwt.encode({
        'sub': 'LS-AABBCC11-000001',
        'gid': 'G000000001',
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=24),
    }, JWT_SECRET, algorithm='HS256')

    print(token)
    ```
  - `.env.local`은 이미 `JWT_SECRET=dev-jwt-secret-lifesync360-32bytes!!` 포함 → 수정 불필요
  - 로컬 테스트 실행 방법:
    ```bash
    cd lifesync360-platform

    # 토큰 발급
    python make_token.py
    # 출력 예: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

    # 앱 실행 (Mock 모드)
    USE_MOCK=true JWT_SECRET=dev-jwt-secret-lifesync360-32bytes!! python app.py

    # API 호출 테스트
    curl http://localhost:5000/api/me \
      -H "Authorization: Bearer <위에서 발급한 토큰>"
    ```

- **미완료 / 추후 작업 필요**
  - `/api/me` 응답의 `name`: `customer_pii_secure` 복호화 연동 필요
  - `/api/me` 응답의 `grade`: DynamoDB `dynamic_grade` 조회 연동 필요
  - 온프레미스 실서버에 schema.sql 변경사항 마이그레이션 적용 필요 (위 ALTER TABLE 스크립트 실행)

---

### 2026-05-14 (2차)

- **lifesync360-platform 포인트 기능 완전 제거**
  - Aurora에 `points` / `point_history` 테이블 없음 → 기능 삭제 결정
  - `app.py`: `MOCK_POINTS`, `MOCK_POINT_HISTORY` import 제거, `settings()` 라우트 단순화 (포인트 변수 전달 제거)
  - `templates/settings.html`: 포인트 탭 버튼(`.stab-bar`), 포인트 잔액 카드, 포인트 이력 테이블 전체 삭제, `switchStab()` JS 함수 제거
  - 등급 정보는 DynamoDB에서 조회 — `settings.html` grade 표시 영역 유지

- **admin-platform Aurora 쿼리 전면 재작성 (실제 Service-DB 스키마 기준)**
  - `overview()` 비Mock 블록:
    - `active_campaigns`: `campaign_master WHERE end_date >= CURDATE()` (컬럼명 `start_date`/`end_date` 반영)
    - `recent_recommends`: `customer_recommend_history` JOIN `product_master` (`clicked_flag`/`purchased_flag` CHAR(1) 방식)
    - `product_funnel`: `customer_recommend_history` JOIN `product_master` + `company_master`, `SUM(clicked_flag="Y")` 집계
    - `top_viewed`: `customer_dashboard_log` JOIN `product_master` WHERE `product_click='Y'` (존재하지 않는 `customer_event_log` 대체)
    - `tab_clicks`: `customer_dashboard_log GROUP BY page_type`
  - `users()` 비Mock: DynamoDB scan 기반 목록 — Aurora `users_ref` 동기화 전까지 `name`/`email`은 `'-'` 표시
  - `user_detail()` 비Mock: DynamoDB(점수/등급) + Lambda(_call_onprem 'get_consent') + Aurora(추천 이력) + Private API(제휴사 매핑)
  - 등급 분포 집계: DynamoDB scan → `dynamic_grade` 기준 집계 (Aurora users.grade 컬럼 없음)

- **admin-platform Mock 데이터 실제 스키마 기준 전면 정합**
  - `MOCK_CONSENTS`: `consent_key`→`domain`, `consent_yn`→`consent_flag`, 모든 도메인 키 대문자 통일
  - `MOCK_RECOMMEND_HISTORY` / `MOCK_RECENT_RECOMMENDS`: `clicked_at`/`purchased_at` DATETIME → `clicked_flag`/`purchased_flag` CHAR(1) 'Y'/'N'
  - `MOCK_CAMPAIGNS`: `start_dt`/`end_dt` → `start_date`/`end_date`
  - `MOCK_USERS`: `PLATINUM`→`VIP`, `BRONZE`→`BASIC` (실제 등급 체계 반영)
  - `MOCK_PRODUCT_FUNNEL`: `affiliate` 값 대문자 통일 (`'insurance'`→`'INSURANCE'` 등)
  - `MOCK_TAB_CLICKS`: `'포인트'` 항목 제거

- **admin-platform 템플릿 컬럼명 수정**
  - `overview.html`: `url_for('user_detail', ls_user_id=...)` → `global_id=...`, `c.start_dt`/`c.end_dt` → `c.start_date`/`c.end_date`, `r.purchased_at`/`r.clicked_at` → `r.purchased_flag == 'Y'`/`r.clicked_flag == 'Y'`
  - `user_detail.html`: `c.consent_key`→`c.domain`, `c.consent_yn == 'Y'`→`c.consent_flag == 'Y'`, 추천이력 플래그 동일 변경
  - `users.html`: `url_for('user_detail', ls_user_id=...)` → `global_id=...`

- **온프레미스 대량 조회 아키텍처 결정**
  - 유저 목록/검색(bulk) → Lambda round-trip 부적합, 응답 지연 + 비용 문제
  - 단기: DynamoDB 기반 유저 목록 (`name`/`email`은 `-` 표시)
  - 장기: Aurora `users_ref` 동기화 테이블 구축 — 온프레미스 `users` 테이블의 비PII 필드 (`global_id`, `ls_user_id`, `login_email`, `user_status`)를 주기적으로 Aurora에 동기화
  - 개별 유저 조회(user_detail) → Lambda OK (per-user action, 지연 허용)

- **미완료 / 추후 작업 필요**
  - Aurora `users_ref` 동기화 테이블 설계 및 구현 (어드민 유저목록 이름/이메일 표시, total_users 정확도)
  - consent_rate 어드민 overview 현재 0 하드코딩 → `users_ref` 동기화 후 구현
  - `/api/me` name 복호화 (`customer_pii_secure` KMS/AES 방식 확정 필요)
  - `/api/me` grade DynamoDB 연동

---

### 2026-05-14 (1차)

- **온프레미스 고객 데이터 조회 Lambda 신규 작성** (`lambda/onprem_customer_query/`)
  - 역할: Platform VPC → Site-to-Site VPN → 온프레미스 Private API 직접 호출 (Control Node 미경유)
  - 지원 액션: `login` / `register` / `get_user` / `get_consent` / `save_consent` / `get_profile` / `get_all`
  - stdlib(urllib)만 사용, 외부 의존성 없음 (`requirements.txt` 비어있음)
  - 환경변수: `PRIVATE_API_URL=http://172.16.1.73` (VPN 경유 on-prem API 주소)
  - 엔드포인트 매핑:

    | action | HTTP | 경로 |
    |--------|------|------|
    | login | POST | `/internal/auth/login` |
    | register | POST | `/internal/auth/register` |
    | get_user | GET | `/internal/auth/user/{ls_user_id}` |
    | get_consent | GET | `/internal/consent/{global_id}` |
    | save_consent | POST | `/internal/auth/consent` |
    | get_profile | GET | `/internal/customer/{global_id}` |
    | get_all | GET ×2 | customer + consent 순차 조회 후 병합 |

- **private_api/app.py — 인증 엔드포인트 4개 신규 추가**
  - `POST /internal/auth/login`: `login_email` 기준 사용자 조회 + `check_password_hash` 검증 (werkzeug)
  - `POST /internal/auth/register`: `master_customer` + `users` 동시 INSERT
  - `GET /internal/auth/user/{ls_user_id}`: 사용자 조회
  - `POST /internal/auth/consent`: `consent` 테이블 UPSERT (`INSERT ... ON DUPLICATE KEY UPDATE`)
  - 전체 필드명 `global_customer_id` → `global_id` 전환 (팀 합의 반영)
  - `ansible/roles/private_api/tasks/main.yml` pip 목록에 `werkzeug` 추가

- **lifesync360-platform/app.py — 온프레미스 Lambda 연동 전환**
  - `get_auth_db()` 직접 연결 제거 → `_call_onprem(action, **kwargs)` Lambda 호출 헬퍼로 대체
  - `ONPREM_QUERY_LAMBDA = os.environ.get('ONPREM_QUERY_LAMBDA', '')` 환경변수로 함수명 주입
  - register / login / me / consent 라우트 모두 Lambda 경유로 전환
  - `taskdef.json`에 `{ "name": "ONPREM_QUERY_LAMBDA", "value": "lifesync-onprem-customer-query" }` 추가
  - `taskdef.json`에 `AUTH_DB_HOST` 환경변수 없음 → Lambda 전환으로 해소

- **Control Node deploy_webhook — PRIVATE_API_URL 추가 및 `/query` 엔드포인트**
  - `deploy_webhook.service`에 `Environment=PRIVATE_API_URL=http://172.16.1.73` 추가
  - `deploy_webhook.py`에 `/query` 엔드포인트 추가 (Option B 백업 경로 — Lambda는 직접 VPN 사용)

- **멀티 VPC IPSec 설계 확인**
  - StrongSwan `rightsubnet`에 여러 CIDR 콤마 구분 지원 확인
  - Platform VPC + Data VPC CIDR 추가 시 기존 Management VPC 터널 영향 없음
  - On-prem ipsec.conf 수정 필요 (IaC 배포 전 온프레미스 담당자 작업):
    ```
    rightsubnet=<Management VPC CIDR>,<Platform VPC CIDR>,<Data VPC CIDR>
    ```
    수정 후: `sudo systemctl restart strongswan-starter`

- **미완료 / 추후 작업 필요**
  - Lambda IaC 배포: Platform VPC 서브넷 지정, SG outbound 172.16.1.73:80, env `PRIVATE_API_URL`
  - ECS Task Role (`lifesync-EcsPlatformTaskRole`) — `lambda:InvokeFunction` 권한 추가 필요
  - On-prem ipsec.conf `rightsubnet` Platform VPC CIDR 추가 + StrongSwan 재시작
  - `schema.sql` 및 기존 수정 파일(consent_filter, customer_profile_sync 등)의 `global_customer_id` → `global_id` 전환 (팀 합의 기준으로 불일치 상태)
  - Platform VPC TGW Attachment IaC (현재 Management VPC만 TGW 연결됨)

---

### 2026-05-13 (1차)

- **Service-DB 분석 및 aurora_schema.sql 정리**
  - `.tmp_extract/Service-DB/` 압축 해제 후 SQL 파일 8개 분석 완료
  - Service-DB 구조 파악: `company_master`(6개) × `category_master`(15개) × `base_product_pool`(120) × `product_variant`(10) → `product_master` 1,200건 자동생성
  - `recommend_rule`(score 기반 36+건), `cross_sell_rule`(53건), `campaign_master`(110건)
  - grade 체계 변경 확인: BASIC/BRONZE/SILVER/GOLD/PLATINUM → VIP(90)/GOLD(80)/SILVER(70)/BASIC(60)/CARE(0)
  - `clicked_flag`/`purchased_flag` CHAR(1) 방식 확인 (DATETIME 아님)
  - aurora_schema.sql에 잘못 포함됐던 `users`/`consent` 테이블 위치 파악
    - 아키텍처 14페이지 기준: users/consent는 온프레미스 전용 → Service-DB(aurora)에 없는 게 맞음

- **lifesync360-platform 클라우드 전환 (app.py 전면 재작성)**
  - 기존 mock 파일 백업: `mock_backup.zip` (app.py + mock_data.py)
  - `get_db()` → `lifesync360` Service-DB 연결 (AURORA_HOST/DB_USER/DB_PASS/DB_NAME)
  - `get_auth_db()` 신규 추가 → 온프레미스 auth DB 연결 (AUTH_DB_* 환경변수)
  - `GRADE_SCORE_MAP`: VIP(90)/GOLD(80)/SILVER(70)/BASIC(60)/CARE(0) 반영
  - `GRADE_BENEFITS`: BRONZE/PLATINUM 제거, VIP/GOLD/SILVER/BASIC/CARE 전환
  - `COMPANIES`: 기존 키 → BANK/CARD/INS/ONINS/SEC/HLT (Service-DB company_code 일치)
  - `api_recommendations`: DynamoDB `dynamic_grade` 기준 grade 조회, `min_score` 필터, `customer_recommend_history` INSERT
  - `api_event`: `clicked_at=NOW()` → `clicked_flag='Y'` / `purchased_flag='Y'`
  - `product/<product_code>`: product_code VARCHAR 조회, company_master + category_master + product_option JOIN
  - `api_my_products`: `purchased_flag='Y'` 기준 조회
  - 인증 라우트(register/login/me/consent) 전체 `get_auth_db()` 사용으로 전환
  - `.env.example` 업데이트 (AUTH_DB_* 항목 추가)

- **온프레미스 스키마 누락 버그 수정**
  - `db/onprem_schema.sql`: users 테이블에 `global_id`/`grade` 컬럼 누락 → 추가
  - `onprem-prod-repo/ansible/roles/mysql/files/schema.sql`: users 테이블 자체가 없었음 → 추가 (실제 배포 파일)
  - 아키텍처 구성도 14페이지 확인 후 수정 — 초기 구성 시 참조 누락이 원인

- **회원가입 flow 버그 3건 수정 (api_register)**
  1. `global_id` NULL 유지 버그 → `G-{uuid.hex[:12].upper()}` 생성 코드 추가
  2. `master_customer` INSERT 누락 → 회원가입 시 `representative_name`과 함께 INSERT
  3. JWT `gid` 클레임에 `ls_user_id` 오입력 → 실제 `global_id` 사용으로 수정

- **register.html 유효성 검사 추가**
  - name/email/password input에 `required` 속성 추가
  - password input에 `minlength="8"` 추가
  - 클라이언트 JS 검증: 필수 항목 빈값 체크 + 8자 미만 체크
  - phone/rrn 필드는 PII 암호화 파이프라인용으로 유지 (제거 안 함)

### 2026-05-12

- Platform CI/CD 파이프라인 전체 트러블슈팅 및 정상화
  - GitHub Secrets 오염 (Excel `+`→`=` 변환) 수정, IAM 액세스 키 재발급
  - buildspec 경로 `deploy/buildspec.yml`로 이동, `imagedefinitions.json` 포맷 수정
  - CodeBuild Role SSM/AS/CloudWatch 권한 추가 (`docs/codebuild-role-policy.json`)
  - CodePipeline Role S3 아티팩트 권한 추가
  - buildspec env에 실제 클러스터/서비스명 하드코딩 수정
  - Application Auto Scaling post_build 등록 (CPU 70% scale-out / 30% scale-in, min 1 / max 4)
  - ECS 태스크 exit 3 원인: `JWT_SECRET` 미설정 → SSM `/lifesync360/jwt-secret` 생성, 태스크 정의 revision 6 등록 (JWT_SECRET secret, USE_MOCK=true, CloudWatch 로그 설정)
  - ECS Execution Role SSM 권한 추가
  - 포트 불일치 수정: ALB 타겟 그룹이 80 고정이라 Dockerfile Gunicorn 바인딩 포트를 8000 → 80으로 수정
  - ECS 배포 설정 `minimumHealthyPercent=0, maximumPercent=200` 수정 (롤링 업데이트 가능하도록)
  - 트러블슈팅 문서: `docs/cicd-troubleshooting-and-iac-tasks.md`
  - IaC 전달 항목: `docs/iac-tasks.md` (Execution Role, SSM, 태스크 정의, Log Group, 배포 설정)
- update-vpn-tunnel.sh 버그 수정 3건
  - **Windows CRLF `\r` 버그 (IP 미반영 근본 원인)**: Windows AWS CLI가 CRLF로 출력 → `$()` substitution이 `\n`은 제거하지만 `\r`은 남김 → TUNNEL_IP에 `\r` 포함 → sed가 ipsec.conf에 `right=IP\r` 기록 → StrongSwan 파싱 실패. `tr -d '\r'` 추가 (TUNNEL_IP 2곳, PSK SM 조회 1곳)
  - **PSK 조회 로직 재설계**: 기존 ipsec.secrets에서 sed로 PSK 추출하는 방식 제거 → VPN_PSK 환경변수(우선순위 1) / Secrets Manager(우선순위 2) / 없으면 exit 1
  - **ipsec.secrets 업데이트 방식 변경**: sed 패턴 매칭 → printf+tee 전체 교체 (sed는 매칭 실패 시 exit 0 반환으로 오류 감지 불가)
- docs/control-node-deploy-guide.md 최초 작성 완료 (14a/14b/14c 3단계 배포 가이드, 트러블슈팅, 주요 경로 표)

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
- Ansible 14a/14b/14c IaC 분석 — SSH 키 미생성 원인 파악
  - 14b UserData 실행 순서: git clone → SSH 키 생성. set -euo pipefail + git clone 실패 시 exit 1 → SSH 키 생성 미실행
  - git clone 실패 원인: Management VPC private subnet에서 CodeCommit 퍼블릭 엔드포인트 접근 불가 (NAT GW 없음)
  - 14a IAM: codecommit:GitPush 불필요 (Ansible이 CodeCommit에 push하는 케이스 없음) — 제거 권고
  - deploy-control-node.sh 불일치 항목 확인: CF Output 키(`InstanceId` → `AnsibleControlInstanceId`), 완료 확인 파일(`/tmp/control-node-ready` — 14b에 없음)
- Management VPC 네트워크 경로 분석
  - TGW→VPN은 온프레미스↔AWS 경로, Ansible EC2→CodeCommit 경로와 무관
  - 기존 01b-lifesync-vpc-endpoints.yaml: LifeSync VPC(ECS)용, CodeCommit/SSM 엔드포인트 없음
  - Management VPC는 별도 VPC → 전용 VPC Endpoints 파일 신규 작성 필요
- 01c-management-vpc-endpoints.yaml 작성 완료
  - S3 Gateway(무료) + SSM×3 + CodeCommit×2 인터페이스 엔드포인트
  - 예상 비용 ~$36/월 (1 AZ) / NAT GW 있으면 선택사항
- Ansible 14a/14b/14c IaC 수정 완료
  - 14a: codecommit:GitPush 제거
  - 14b: SSH 키 생성 블록을 git clone 앞으로 이동 (순서 역전 버그 수정)
  - 14b: sudo -u ansible git → sudo -u ansible /usr/bin/git 전체 경로 지정 (sudo env_reset PATH 문제 해결)
  - 14b: ManagementSubnetId 파라미터 설명 NAT GW → VPC Endpoints 참조로 업데이트
  - 14c: aws sts get-caller-identity 사전 체크 제거 (STS VPC Endpoint 없이도 동작)
- 재배포 순서: 14a → 14b → 14b 출력(AnsibleControlInstanceId) 확인 → 14c

---

## 트러블슈팅

### Ansible Control Node SSH 키 미생성 (2026-05-11)

**증상**
- `/home/ansible/.ssh/id_rsa` 파일이 생성되지 않음
- 14c SSM Association이 공개키를 SSM Parameter Store에 올리지 못함

**원인 1 — 14b UserData 실행 순서 버그**
- 원래 순서: `git clone` → `SSH 키 생성`
- `set -euo pipefail` 상태에서 git clone 실패 시 `exit 1` → SSH 키 생성 코드 미실행
- 수정: SSH 키 생성 블록을 git clone **앞으로** 이동

**원인 2 — sudo env_reset으로 인한 git PATH 문제**
- UserData에서 `sudo -u ansible git clone ...` 실행 시 sudo가 PATH 초기화
- git이 `/usr/bin/git`에 설치돼 있어도 초기화된 PATH에서 못 찾아 `env: 'git': No such file or directory` 발생
- 수정: `sudo -u ansible git` → `sudo -u ansible /usr/bin/git` 전체 경로 지정

**원인 3 — 14c에서 STS 엔드포인트 필요**
- `aws sts get-caller-identity` 호출이 퍼블릭 STS 엔드포인트로 나가 VPC Endpoint 없이 실패 가능
- 수정: 해당 사전 체크 제거 (ssm:PutParameter 자체가 IAM 없으면 어차피 실패)

**확인 방법**
```bash
# SSM 세션 접속
aws ssm start-session --target <AnsibleControlInstanceId> --region ap-northeast-2

# UserData 로그 확인
sudo tail -100 /var/log/ansible-bootstrap.log

# 키 존재 여부
ls -la /home/ansible/.ssh/

# SSM에 공개키 올라갔는지
aws ssm get-parameter \
  --name /lifesync/dev/ansible/public-key \
  --region ap-northeast-2 \
  --query Parameter.Value --output text
```

**재배포 순서**
```
14a → 14b → 14b 출력(AnsibleControlInstanceId) 확인 → 14c
```

---

### SSM start-session 오류 모음 (2026-05-11)

| 에러 | 원인 | 해결 |
|------|------|------|
| `Could not connect to endpoint URL: ssm.ap-northease-2...` | 리전명 오타 (`northease` → `northeast`) | `aws configure set region ap-northeast-2` |
| `403 Forbidden` | 로컬 IAM 자격증명에 `ssm:StartSession` 권한 없음 | IAM 정책에 ssm:StartSession 추가 또는 admin 프로파일 사용 |
| `Session Manager plugin not found` | Session Manager Plugin 미설치 | [SessionManagerPluginSetup.exe](https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe) 설치 후 터미널 재시작 |

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
| Lambda TGW Attachment (Platform VPC) | IaC 담당자 | lambda-to-onprem-network.md |
| onprem_customer_query Lambda IaC 배포 (Platform VPC / SG outbound 172.16.1.73:80 / PRIVATE_API_URL) | IaC 담당자 | lambda-to-onprem-network.md |
| ECS Task Role lambda:InvokeFunction 권한 추가 (lifesync-EcsPlatformTaskRole) | IaC 담당자 | taskdef.json ONPREM_QUERY_LAMBDA 참고 |
| On-prem ipsec.conf rightsubnet Platform VPC CIDR 추가 + strongswan 재시작 | 온프레미스 담당자 | aws-vpn-setup.md |
| private_api Ansible 재배포 (werkzeug 추가 + 인증 엔드포인트 4개) | 온프레미스 담당자 | roles/private_api/ |
| 동의 고객 선별 Lambda 구현 | 개발 | ETL 파이프라인 AWS→GCP 전송 전 consent 필터링 |
| Aurora users_ref 동기화 테이블 구축 (어드민 유저목록 이름/이메일, total_users 정확도) | 개발 | on-prem users → Aurora 주기 동기화 |
| /api/my-products 운영 연결 | 개발 | Aurora consent 테이블 체크 |
| upgrade_actions 운영 연결 | 개발 | DynamoDB/Aurora 실데이터 ctx |

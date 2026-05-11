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
| ls-vpngw | 192.168.56.10 | Ansible Control Node | 1GB | 20GB |
| ls-db    | 192.168.56.11 | MySQL | 2GB | 50GB |
| ls-token | 192.168.56.12 | Tokenization Service | 1GB | 20GB |
| ls-api   | 192.168.56.13 | Private API + Cron | 1GB | 20GB |

공통 설정: Ubuntu 22.04 / 어댑터1=NAT / 어댑터2=Host-Only(192.168.56.x 고정 IP)

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
```

---

### Step 3 — SSH 키 생성 및 배포 (개발 PC 또는 ls-vpngw)

```bash
# SSH 키 생성 (최초 1회)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lifesync360-onprem.pem -N ""

# 각 VM에 공개키 등록
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.11
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.12
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.13
```

---

### Step 4 — Ansible 초기 설정 및 연결 확인 (ls-vpngw)

```bash
ssh ansible@192.168.56.10

# Ansible 설치
sudo apt update && sudo apt install -y ansible python3-pip

# 레포 클론
git clone <repo_url> /opt/ansible/onprem-prod-repo
cd /opt/ansible/onprem-prod-repo

# SSH 키 복사 (개발 PC → ls-vpngw는 공유 폴더 또는 scp 이용)
mkdir -p ~/.ssh
cp /mnt/downloads/lifesync360-onprem.pem ~/.ssh/
chmod 600 ~/.ssh/lifesync360-onprem.pem

# 연결 확인 — 3개 VM 모두 pong 이면 정상
ansible all -m ping -i ansible/inventory/hosts.yml
```

---

### Step 5 — Ansible 첫 배포

```bash
# ls-vpngw에서
cd /opt/ansible/onprem-prod-repo
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml
```

배포 후 서비스 상태 확인:
```bash
ssh ansible@192.168.56.11 "sudo systemctl status mysql"
ssh ansible@192.168.56.12 "sudo systemctl status tokenization"
ssh ansible@192.168.56.13 "sudo systemctl status private-api nginx"
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

`pii-encryption-guide.md` 를 보고 순서대로 진행.

---

### Step 9 — Ansible Vault 암호화

```bash
# ls-vpngw에서
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

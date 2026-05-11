# IaC 담당자 인수인계

---

## 완료된 항목 (인수인계 시점 기준)

| 항목 | 내용 |
|------|------|
| taskdef.json ACCOUNT_ID 치환 | platform 5곳, admin 6곳 완료 (354493396671) |
| Ansible Control Node SSH 키 | EC2에서 신규 생성 완료, VM 등록 테스트 중 |
| Dockerfile gunicorn 전환 | platform, admin 모두 완료 |
| PII 암호화 | 온프레미스 DB 100만 건 암호화 완료 |
| Ansible Vault | private_api, tokenization 암호화 완료 |
| EC2 Control Node IaC | infra/compute/control-node.yaml (CloudFormation) 작성 완료 |
| Deploy Server | infra/deploy-server/ — Flask 9000, systemd, SSH 키 배포 스크립트 |
| DEPLOY_TOKEN 보안 처리 | Secrets Manager(lifesync/deploy-token) → /etc/deploy-server/env 분리 |
| hosts.yml ProxyJump | ls-db / ls-token ansible_ssh_common_args 추가 (ls-api 경유) |

---

## 1. Secrets Manager 생성 목록

CloudFormation/Terraform 스택 배포 후 Aurora, Redis 엔드포인트 확정되면 입력.

| Secret 이름 | 키 구조 | 사용처 |
|-------------|---------|--------|
| `lifesync/aurora` | `{"host":"...","user":"...","password":"..."}` | platform, admin, Lambda |
| `lifesync/jwt` | `{"secret":"..."}` | platform |
| `lifesync/redis` | `{"host":"..."}` | platform |
| `lifesync/admin` | `{"username":"...","password":"...","secret_key":"..."}` | admin |
| `lifesync/ansible-vault` | `{"password":"..."}` | Control Node UserData — vault.yml 복호화 |
| `lifesync/ansible-vm` | `{"password":"..."}` | Control Node UserData — ssh-copy-id 초기 배포 |
| `lifesync/deploy-token` | `{"token":"..."}` | Control Node Deploy Server — X-Deploy-Token 인증 |

```bash
# 플랫폼/어드민
aws secretsmanager create-secret \
  --name lifesync/aurora \
  --secret-string '{"host":"<Aurora 엔드포인트>","user":"<DB 유저>","password":"<DB 패스워드>"}'

aws secretsmanager create-secret \
  --name lifesync/jwt \
  --secret-string '{"secret":"<JWT 서명 키>"}'

aws secretsmanager create-secret \
  --name lifesync/redis \
  --secret-string '{"host":"<ElastiCache 엔드포인트>"}'

aws secretsmanager create-secret \
  --name lifesync/admin \
  --secret-string '{"username":"<관리자 계정>","password":"<관리자 패스워드>","secret_key":"<Flask 세션 키>"}'

# Control Node (IaC 배포 전 필수)
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

---

## 2. Ansible Control Node EC2 초기 설정

```bash
# Ansible 설치
sudo apt-get install -y ansible git python3-pip

# 배포 디렉토리 생성
sudo mkdir -p /opt/ansible
sudo chown ubuntu:ubuntu /opt/ansible

# SSH 키 생성 (온프레미스 VM 접속용)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lifesync360-onprem.pem -N ""
cat ~/.ssh/lifesync360-onprem.pem.pub  # → 3번에서 VM에 등록

# 레포 클론
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone https://git-codecommit.ap-northeast-2.amazonaws.com/v1/repos/onprem-prod-repo /opt/ansible/onprem-prod-repo

# Vault 파일 실제 값으로 덮어쓰기 (값은 4번 참고)
cat > /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/private_api/vault.yml << 'EOF'
vault_pii_aes_key: "<전달받은 Fernet 키>"
vault_mysql_app_password: "<전달받은 MySQL 패스워드>"
EOF

cat > /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/tokenization/vault.yml << 'EOF'
vault_mysql_app_password: "<전달받은 MySQL 패스워드>"
EOF

ansible-vault encrypt /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/private_api/vault.yml
ansible-vault encrypt /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/tokenization/vault.yml
```

---

## 3. 온프레미스 VM SSH 공개키 등록

VPN 연결 완료 후 EC2에서 실행:

```bash
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.11
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.12
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.13

# 확인
ansible all -m ping -i /opt/ansible/onprem-prod-repo/ansible/inventory/hosts.yml
```

---

## 4. 보안 채널로 별도 전달 필요한 값

이메일/슬랙 평문 전송 금지.

| 항목 | 용도 |
|------|------|
| Fernet PII 키 | vault_pii_aes_key — 온프레미스 DB 복호화 키 |
| MySQL lifesync 패스워드 | vault_mysql_app_password |
| Ansible Vault 패스워드 | ansible-playbook `--ask-vault-pass` 입력값 |

---

## 5. 배포 순서

1. CloudFormation/Terraform 스택 배포 (Aurora, Redis, ECS 등)
2. Secrets Manager 값 입력 (1번)
3. EC2 Control Node 초기 설정 (2번)
4. VPN 연결 확인 후 온프레미스 VM SSH 키 등록 (3번)
5. Ansible 첫 배포:
   ```bash
   ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --ask-vault-pass
   ```

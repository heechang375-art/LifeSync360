# IaC 담당자 인수인계

---

## 1. ACCOUNT_ID 치환 (배포 전 필수)

`taskdef.json` 2개 파일에서 AWS 계정 ID로 교체:
- `lifesync360-platform/taskdef.json` — 5곳
- `admin-platform/taskdef.json` — 6곳

```bash
# 계정 ID 확인
aws sts get-caller-identity --query Account --output text

# 일괄 치환
sed -i 's/ACCOUNT_ID/실제계정ID/g' lifesync360-platform/taskdef.json
sed -i 's/ACCOUNT_ID/실제계정ID/g' admin-platform/taskdef.json
```

---

## 2. Secrets Manager 생성 목록

Aurora, Redis 생성 후 실제 값으로 입력.

| Secret 이름 | 키 구조 | 사용처 |
|-------------|---------|--------|
| `lifesync/aurora` | `{"host":"...","user":"...","password":"..."}` | platform, admin, Lambda |
| `lifesync/jwt` | `{"secret":"..."}` | platform |
| `lifesync/redis` | `{"host":"..."}` | platform |
| `lifesync/admin` | `{"username":"...","password":"...","secret_key":"..."}` | admin |

```bash
# 예시 (Aurora 생성 후 실제 값으로)
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
```

---

## 3. Ansible Control Node EC2 초기 설정

EC2 접속 후 순서대로 실행:

```bash
# Ansible 설치
sudo apt-get install -y ansible git python3-pip

# 배포 디렉토리 생성
sudo mkdir -p /opt/ansible
sudo chown ubuntu:ubuntu /opt/ansible

# SSH 키 생성 (온프레미스 VM 접속용)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lifesync360-onprem.pem -N ""

# 공개키 출력 → 온프레미스 VM 3대에 등록 필요 (4번 참고)
cat ~/.ssh/lifesync360-onprem.pem.pub

# 레포 클론
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone https://git-codecommit.ap-northeast-2.amazonaws.com/v1/repos/onprem-prod-repo /opt/ansible/onprem-prod-repo

# Vault 파일 생성 (값은 5번 항목 참고)
cat > /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/private_api/vault.yml << 'EOF'
vault_pii_aes_key: "<전달받은 Fernet 키>"
vault_mysql_app_password: "<전달받은 MySQL 패스워드>"
EOF

cat > /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/tokenization/vault.yml << 'EOF'
vault_mysql_app_password: "<전달받은 MySQL 패스워드>"
EOF

# Vault 암호화
ansible-vault encrypt /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/private_api/vault.yml
ansible-vault encrypt /opt/ansible/onprem-prod-repo/ansible/inventory/group_vars/tokenization/vault.yml
```

---

## 4. 온프레미스 VM SSH 공개키 등록

3번에서 생성한 공개키를 온프레미스 VM 3대에 등록. VPN 연결 완료 후 EC2에서 실행:

```bash
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.11
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.12
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.13
```

등록 확인:
```bash
ansible all -m ping -i /opt/ansible/onprem-prod-repo/ansible/inventory/hosts.yml
```

---

## 5. 보안 채널로 별도 전달 필요한 값

아래 값은 이메일/슬랙 평문 전송 금지. 팀 시크릿 툴 또는 직접 전달.

| 항목 | 용도 |
|------|------|
| Fernet PII 키 | vault_pii_aes_key — 온프레미스 DB 복호화 키 |
| MySQL lifesync 패스워드 | vault_mysql_app_password |
| Ansible Vault 패스워드 | ansible-playbook 실행 시 `--ask-vault-pass` 입력값 |

---

## 6. 배포 순서 요약

1. CloudFormation/Terraform 스택 배포 (Aurora, Redis, ECS 등)
2. Aurora 엔드포인트 확인 후 Secrets Manager 값 입력 (2번)
3. ACCOUNT_ID 치환 후 git push (1번)
4. EC2 Control Node 초기 설정 (3번)
5. VPN 연결 확인 후 온프레미스 VM SSH 키 등록 (4번)
6. Ansible 첫 배포: `ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --ask-vault-pass`

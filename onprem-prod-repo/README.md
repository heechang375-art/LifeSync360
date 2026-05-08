# On-Prem CI/CD (Ansible 배포)

MySQL / Tokenization / Private API 배포 파이프라인.

## 파이프라인 흐름

```
Developer Push (GitHub)
    → GitHub Actions (Unit Test / Security Scan / Ansible Syntax Check)
    → 테스트 통과 시 자동 승인
    → CodeCommit Mirror
    → CodePipeline 트리거
    → CodeBuild (SSM Send Command 실행)
    → Ansible Control Node (git pull → ansible-playbook)
    → MySQL / Tokenization / Private API 배포
```

---

## 파일 역할

| 파일 | 역할 |
|------|------|
| `.github/workflows/ci.yml` | GitHub Actions: 테스트 + CodeCommit 미러링 |
| `buildspec.yml` | CodeBuild: SSM으로 Ansible Control Node 호출 |
| `ansible/site.yml` | Ansible 전체 실행 진입점 |
| `ansible/inventory/hosts.yml` | 배포 대상 서버 IP 목록 |
| `ansible/inventory/group_vars/` | 역할별 변수 및 Vault 시크릿 |
| `ansible/roles/mysql/` | MySQL 스키마 마이그레이션 + 백업 설정 |
| `ansible/roles/tokenization/` | 토크나이저 서비스 배포 |
| `ansible/roles/private_api/` | FastAPI + systemd 배포 |

---

## 사전 준비

### 1. Ansible Control Node EC2 초기 설정

Ansible Control Node EC2에 SSH로 접속 후 1회 실행:

```bash
# Ansible 설치
sudo apt-get install -y ansible git python3-pip

# 배포 디렉토리 생성
sudo mkdir -p /opt/ansible
sudo chown ubuntu:ubuntu /opt/ansible

# SSH 배포 키 생성 (대상 서버 접속용)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lifesync360-onprem.pem -N ""

# 생성된 공개키 출력 → 대상 서버 authorized_keys에 등록 필요
cat ~/.ssh/lifesync360-onprem.pem.pub

# CodeCommit에서 초기 클론
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone https://git-codecommit.ap-northeast-2.amazonaws.com/v1/repos/onprem-prod-repo /opt/ansible/onprem-prod-repo
```

### 2. Vault 파일 실제 값 입력 (Control Node에서 1회)

git에 플레이스홀더가 암호화된 상태로 포함돼 있음. 실제 값으로 덮어쓰고 재암호화:

```bash
cd /opt/ansible/onprem-prod-repo

# private_api vault — 실제 값으로 덮어쓰기
cat > ansible/inventory/group_vars/private_api/vault.yml << 'EOF'
vault_pii_aes_key: "<전달받은 Fernet 키>"
vault_mysql_app_password: "<전달받은 MySQL 패스워드>"
EOF

# tokenization vault — 실제 값으로 덮어쓰기
cat > ansible/inventory/group_vars/tokenization/vault.yml << 'EOF'
vault_mysql_app_password: "<전달받은 MySQL 패스워드>"
EOF

# 암호화
ansible-vault encrypt ansible/inventory/group_vars/private_api/vault.yml
ansible-vault encrypt ansible/inventory/group_vars/tokenization/vault.yml
```

### 3. 대상 서버 SSH 키 등록

MySQL / Tokenization / Private API 각각에 접속 후:

```bash
echo "<Control Node 공개키>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 4. GitHub Secrets 등록

GitHub Repo → Settings → Secrets and variables → Actions

| Secret 이름 | 값 |
|------------|-----|
| `AWS_ACCESS_KEY_ID` | CodeCommit + SSM 권한을 가진 IAM User Access Key |
| `AWS_SECRET_ACCESS_KEY` | 위 Key의 Secret |

### 5. Ansible Control Node IAM Role 설정

Ansible Control Node EC2에 아래 권한을 가진 IAM Role 연결:

```json
{
  "Effect": "Allow",
  "Action": [
    "codecommit:GitPull"
  ],
  "Resource": "*"
}
```

### 6. AWS 리소스 생성 (Terraform으로 관리)

- CodePipeline: Source(CodeCommit) → Build(CodeBuild)
- CodeBuild 서비스 역할에 SSM SendCommand 권한 추가:

```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:SendCommand",
    "ssm:GetCommandInvocation"
  ],
  "Resource": "*"
}
```

---

## 배포 방법

### 일반 배포 (자동)

```bash
git add .
git commit -m "feat: 변경 내용"
git push origin main
```

GitHub Actions → CodeCommit 미러 → CodePipeline → CodeBuild → SSM → Ansible 자동 실행.

### Ansible 단독 실행 (테스트 또는 긴급 시)

Ansible Control Node EC2에 SSH 접속 후:

```bash
cd /opt/ansible/onprem-prod-repo

# 전체 배포
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --ask-vault-pass

# 특정 역할만 배포
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --tags mysql --ask-vault-pass
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --tags tokenization --ask-vault-pass
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --tags private_api --ask-vault-pass

# 특정 서버만 배포
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --limit ls-api --ask-vault-pass

# dry-run
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --check --ask-vault-pass
```

### Ansible Syntax 검사

```bash
ansible-playbook ansible/site.yml --syntax-check -i ansible/inventory/hosts.yml
```

---

## 배포 상태 확인

```bash
# SSM 명령 상태 확인
aws ssm list-command-invocations \
  --filter "key=DocumentName,value=AWS-RunShellScript" \
  --details \
  --region ap-northeast-2

# Ansible 배포 로그 확인 (Ansible Control Node에서)
cat /var/log/ansible-deploy.log

# 서비스 상태 확인 (대상 서버에서)
systemctl status tokenization
systemctl status private-api
systemctl status mysqld
```

---

## 역할별 배포 내용

### mysql role
| 작업 | 내용 |
|------|------|
| schema.sql 적용 | lifesync_onprem DB 테이블 생성/변경 |
| backup.sh 등록 | 매일 새벽 2시 자동 백업 크론 |

### tokenization role
| 작업 | 내용 |
|------|------|
| token_service.py 배포 | `/opt/tokenization/` 에 복사 |
| masking_rules.yml 배포 | 마스킹 대상 필드 설정 |
| 서비스 재시작 | `systemctl restart tokenization` |

### private_api role
| 작업 | 내용 |
|------|------|
| app.py 배포 | `/opt/private-api/` 에 복사 |
| PII 복호화 | representative_name, birth_dt Fernet 복호화 적용 |
| DB 연결 | 환경변수(DB_HOST, DB_USER, DB_PASS)로 MySQL 접속 |
| systemd 등록 | 서버 재부팅 시 자동 시작 |

---

## 트러블슈팅

### SSM Send Command 실패
```
원인: Ansible Control Node에 SSM Agent 미설치 또는 IAM Role 미연결
해결:
  1. EC2 콘솔에서 해당 인스턴스 IAM Role 확인
  2. sudo systemctl status amazon-ssm-agent
  3. sudo systemctl start amazon-ssm-agent
```

### Ansible SSH 접속 실패
```
원인: 대상 서버 authorized_keys에 Control Node 공개키 미등록
해결:
  cat ~/.ssh/lifesync360-onprem.pem.pub
  → 출력된 공개키를 대상 서버 ~/.ssh/authorized_keys 에 추가
```

### Ansible Vault 오류
```
원인: vault.yml 파일이 Control Node에 없거나 패스워드 불일치
해결:
  ls ansible/inventory/group_vars/private_api/vault.yml
  ls ansible/inventory/group_vars/tokenization/vault.yml
  → 없으면 "사전 준비 2단계" 참고해서 생성
```

### MySQL 마이그레이션 실패
```
원인: schema.sql 문법 오류 또는 기존 테이블 충돌
해결:
  sudo mysql lifesync_onprem < /tmp/schema.sql
  → 직접 실행해서 에러 메시지 확인
```

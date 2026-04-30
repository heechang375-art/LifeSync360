# On-Prem CI/CD (Ansible 배포)

MySQL / Tokenization / Private API EC2 배포 파이프라인.

## 파이프라인 흐름

```
Developer Push (GitHub)
    → GitHub Actions (Unit Test / Security Scan / Ansible Syntax Check)
    → 테스트 통과 시 자동 승인
    → CodeCommit Mirror
    → CodePipeline 트리거
    → CodeBuild (SSM Send Command 실행)
    → Ansible Control Node (git pull → ansible-playbook)
    → MySQL / Tokenization / Private API EC2 배포
```

---

## 파일 역할

| 파일 | 역할 |
|------|------|
| `.github/workflows/ci.yml` | GitHub Actions: 테스트 + CodeCommit 미러링 |
| `buildspec.yml` | CodeBuild: SSM으로 Ansible Control Node 호출 |
| `ansible/site.yml` | Ansible 전체 실행 진입점 |
| `ansible/inventory/hosts` | 배포 대상 서버 IP 목록 |
| `ansible/roles/mysql/` | MySQL 스키마 마이그레이션 + 백업 설정 |
| `ansible/roles/tokenization/` | 토크나이저 서비스 배포 |
| `ansible/roles/private_api/` | FastAPI + Nginx + systemd 배포 |

---

## 사전 준비

### 1. Terraform EC2 태그 확인

Dynamic Inventory를 사용하므로 IP 수정 불필요.
Terraform에서 EC2 생성 시 아래 태그가 반드시 있어야 함:

```hcl
# MySQL EC2
tags = { Project = "lifesync360", Role = "mysql" }

# Tokenization EC2
tags = { Project = "lifesync360", Role = "tokenization" }

# Private API EC2
tags = { Project = "lifesync360", Role = "private_api" }
```

IaC 재구축으로 IP가 바뀌어도 태그 기반으로 자동 탐색.

### 2. Ansible Control Node EC2 초기 설정

Ansible Control Node EC2에 SSH로 접속 후 1회 실행:

```bash
# Ansible 설치
sudo yum install -y ansible git python3-pip

# Dynamic Inventory용 컬렉션 및 라이브러리 설치
ansible-galaxy collection install amazon.aws
pip3 install boto3 botocore

# 배포 디렉토리 생성
sudo mkdir -p /opt/ansible
sudo chown ec2-user:ec2-user /opt/ansible

# SSH 배포 키 생성 (대상 서버 접속용)
mkdir -p /opt/ansible/.ssh
ssh-keygen -t rsa -b 4096 -f /opt/ansible/.ssh/deploy_key -N ""

# 생성된 공개키 출력 → 대상 서버 authorized_keys에 등록 필요
cat /opt/ansible/.ssh/deploy_key.pub

# CodeCommit에서 초기 클론
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone https://git-codecommit.ap-northeast-2.amazonaws.com/v1/repos/onprem-prod-repo /opt/ansible
```

### 3. 대상 서버 SSH 키 등록

MySQL / Tokenization / Private API EC2 각각에 접속 후:

```bash
# Ansible Control Node의 공개키를 authorized_keys에 추가
echo "ssh-rsa AAAA..." >> ~/.ssh/authorized_keys
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
    "secretsmanager:GetSecretValue",
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
cd /opt/ansible

# 전체 배포
ansible-playbook site.yml -i inventory/hosts

# 특정 역할만 배포
ansible-playbook site.yml -i inventory/hosts --tags mysql
ansible-playbook site.yml -i inventory/hosts --tags tokenization
ansible-playbook site.yml -i inventory/hosts --tags private_api

# 실제 적용 전 dry-run (변경사항 미리보기)
ansible-playbook site.yml -i inventory/hosts --check

# 특정 서버만 배포
ansible-playbook site.yml -i inventory/hosts --limit mysql
```

### Ansible Syntax 검사

```bash
ansible-playbook ansible/site.yml --syntax-check -i ansible/inventory/hosts
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
| schema.sql 적용 | lifesync360 DB 테이블 생성/변경 |
| backup.sh 등록 | 매일 새벽 2시 자동 백업 크론 |
| 자격증명 | Secrets Manager `lifesync/db` 에서 조회 |

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
| Nginx 설정 | 포트 80 → 8000 리버스 프록시 |
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
  cat /opt/ansible/.ssh/deploy_key.pub
  → 출력된 공개키를 대상 서버 ~/.ssh/authorized_keys 에 추가
```

### Secrets Manager 접근 실패
```
원인: Ansible Control Node IAM Role에 권한 없음
해결: IAM Role Policy에 secretsmanager:GetSecretValue 추가
```

### MySQL 마이그레이션 실패
```
원인: schema.sql 문법 오류 또는 기존 테이블 충돌
해결:
  mysql -u root -p lifesync360 < /tmp/schema.sql
  → 직접 실행해서 에러 메시지 확인
```

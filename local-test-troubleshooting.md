# 온프레미스 트러블슈팅 — LifeSync360

증상별 즉시 해결 가이드.

---

## 증상: ansible all -m ping 전부 UNREACHABLE

```
Permission denied (publickey,password)
```

**원인**: 공개키를 터미널에서 수동 복붙할 때 개행/공백이 붙어 `authorized_keys` 키 손상.

**해결**:
```bash
# 키 파일로 직접 등록 (ls-vpngw에서)
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.11
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.12
ssh-copy-id -i ~/.ssh/lifesync360-onprem.pem.pub ansible@192.168.56.13

# 홈 디렉토리 권한 문제일 때 (각 VM에서)
chmod 755 /home/ansible
chmod 700 /home/ansible/.ssh
chmod 600 /home/ansible/.ssh/authorized_keys
```

---

## 증상: MySQL root 비밀번호 변경 태스크 실패

```
ERROR 1045 (28000): Access denied for user 'root'@'localhost'
```

**원인**: Ubuntu 24.04 MySQL 신규 설치 시 root에 비밀번호가 설정돼 있고, unix socket 인증도 차단됨.

**해결**: `/etc/mysql/debian.cnf`의 `debian-sys-maint` 계정으로 먼저 접속 후 root 비밀번호 변경.

```bash
# ls-db VM에서
sudo cat /etc/mysql/debian.cnf | grep password | head -1
# → password = xxxxxxxx  (이 값 사용)

mysql -u debian-sys-maint -p<위의_패스워드> \
  -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '<설정할_패스워드>'; FLUSH PRIVILEGES;"
```

Ansible task에 적용된 해결 코드 (`mysql/tasks/main.yml`):
```yaml
- name: Get debian-sys-maint password
  shell: awk '/^password/{print $3; exit}' /etc/mysql/debian.cnf
  register: debian_maint_password
  no_log: true

- name: Set MySQL root password
  shell: |
    mysql -u debian-sys-maint -p"{{ debian_maint_password.stdout }}" \
    -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{{ mysql_root_password }}'; FLUSH PRIVILEGES;"
  no_log: true
```

---

## 증상: pip install 태스크 실패 (externally-managed-environment)

```
error: externally-managed-environment
This environment is externally managed
```

**원인**: Ubuntu 24.04 Python 3.12부터 PEP 668로 시스템 pip 직접 설치 차단.

**해결**: venv 생성 후 venv 경로로 설치. systemd ExecStart도 venv 경로로 변경.

```yaml
- name: Install python3-venv
  apt:
    name: python3-venv
    state: present

- name: Create virtualenv
  command: python3 -m venv /opt/tokenization/venv
  args:
    creates: /opt/tokenization/venv

- name: Install Python dependencies
  pip:
    name:
      - fastapi
      - uvicorn
    virtualenv: /opt/tokenization/venv
```

systemd 서비스 파일:
```
# 변경 전
ExecStart=/usr/local/bin/uvicorn token_service:app ...

# 변경 후
ExecStart=/opt/tokenization/venv/bin/uvicorn token_service:app ...
```

---

## 증상: curl http://192.168.56.13/health → 404

```
<html><body><h1>404 Not Found</h1></body></html>
```

포트 8000 직접 호출은 정상(`curl http://192.168.56.13:8000/health → {"status":"ok"}`).

**원인**: Ubuntu Nginx 기본 설치 시 `sites-enabled/default`가 80포트를 먼저 점유. `conf.d/private-api.conf`가 배포됐어도 `default`에 가로막혀 적용 안 됨.

**해결**:
```bash
# ls-api VM에서 즉시 해결
sudo rm /etc/nginx/sites-enabled/default
sudo systemctl reload nginx
curl http://127.0.0.1/health
# → {"status":"ok"}
```

Ansible task에 영구 반영 (`private_api/tasks/main.yml`):
```yaml
- name: Remove default Nginx site
  file:
    path: /etc/nginx/sites-enabled/default
    state: absent
  notify: Reload nginx
```

---

## 증상: Ansible 재배포 시 MySQL 비밀번호 태스크 충돌

```
ERROR 1045: Access denied (재배포 시 구 패스워드로 접속 시도)
```

**원인**: 이미 비밀번호가 설정된 상태에서 Ansible이 재실행되면 `debian-sys-maint`로 다시 비밀번호 변경 시도.

**해결**: 비밀번호 설정 태스크에 `when` 조건 추가.

```yaml
- name: Set MySQL root password
  shell: ...
  when: mysql_password_changed is not defined
```

---

## 증상: ls-token 서비스 재배포 후 DB 자격증명 초기화

**원인**: Ansible이 systemd 서비스 파일을 덮어쓰면서 수동으로 설정했던 `DB_USER`, `DB_PASS` 환경변수 사라짐.

**해결**: `tokenization.service.j2`에 Ansible 변수로 환경변수 주입.

`tokenization.service.j2`:
```
Environment="DB_USER={{ mysql_app_user }}"
Environment="DB_PASS={{ mysql_app_password }}"
```

`inventory/hosts.yml`:
```yaml
ls-token:
  ansible_host: 192.168.56.12
  mysql_app_user: lifesync
  mysql_app_password: "{{ vault_mysql_app_password }}"
```

---

## 증상: trigger_ansible.sh 실행 시 호스트 변수 undefined

```
fatal: [ls-api]: FAILED! => {"msg": "The task includes an option with an undefined variable..."}
```

**원인**: `ansible-playbook` 명령에 `-i` 플래그 누락. 인벤토리 지정 없으면 호스트 변수 전부 undefined.

**해결**: `trigger_ansible.sh`에 `-i ansible/inventory/hosts.yml` 추가.

```bash
# 변경 전
ansible-playbook ansible/site.yml

# 변경 후
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.yml --vault-password-file ~/.vault_pass
```

---

## 증상: Ansible 실행 시 ImportError: No module named 'six.moves'

```
ImportError: No module named 'six.moves'
TASK [Gathering Facts] FAILED
```

**원인**: Amazon Linux + Python 3.8 환경에서 특정 Ansible 버전이 `six` 패키지에 의존하는데, Python 3 환경에는 기본 포함이 안 된 경우.

**해결**:
```bash
# Control Node에서 six 설치
pip3 install six

# 또는 ansible_python_interpreter 명시 (hosts.yml)
# vars:
#   ansible_python_interpreter: /usr/bin/python3
# → 이미 설정돼 있으면 python3 경로에 six 설치

# Ubuntu 22.04 Control Node 사용 시 Ansible 버전 최신화 권장
sudo apt-get install -y ansible  # Ubuntu 레포 기본 버전
# 또는
pip3 install ansible --upgrade
```

**참고**: EC2 Control Node는 Ubuntu 22.04 기준으로 IaC가 작성됨. Amazon Linux 환경이면 위 방법으로 해결하되, 장기적으로 Ubuntu로 전환 고려.

---

## 증상: Deploy Server 기동 실패 — EnvironmentFile not found

```
systemctl status deploy-server
● deploy-server.service — LifeSync360 Deploy Server
   Active: failed
   ...
   deploy-server.service: Failed to load environment files: /etc/deploy-server/env: No such file or directory
```

**원인**: `deploy-server.service`가 `EnvironmentFile=/etc/deploy-server/env`를 참조하는데, 파일이 생성되지 않은 상태에서 서비스 시작 시도.

**해결**: Secrets Manager에서 토큰을 가져와 파일 생성 후 서비스 재시작.
```bash
# EC2 Control Node에서
sudo mkdir -p /etc/deploy-server

DEPLOY_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id lifesync/deploy-token \
  --region ap-northeast-2 \
  --query SecretString --output text \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "DEPLOY_TOKEN=${DEPLOY_TOKEN}" | sudo tee /etc/deploy-server/env > /dev/null
sudo chmod 600 /etc/deploy-server/env

sudo systemctl daemon-reload
sudo systemctl start deploy-server
sudo systemctl status deploy-server
```

---

## 증상: LOAD DATA INFILE 실패 — Table doesn't exist

```
ERROR 1146 (42S02): Table 'lifesync_onprem.master_customer' doesn't exist
```

**원인**: 스키마 적용 전에 데이터 적재 시도.

**해결**: 스키마 먼저 적용 후 LOAD DATA 실행.

```bash
# 스키마 적용
mysql -u root -p lifesync_onprem < /mnt/downloads/onprem_schema.sql

# 이후 데이터 적재
mysql -u root -p lifesync_onprem
```

```sql
LOAD DATA INFILE '/var/lib/mysql-files/customer_master.csv' ...
```

---

## 증상: LOAD DATA INFILE 실패 — secure_file_priv 경로 오류

```
ERROR 1290: --secure-file-priv option
```

**원인**: MySQL `secure_file_priv` 기본값이 `/var/lib/mysql-files/`. 다른 경로 파일은 읽기 거부.

**해결**: 파일을 `/var/lib/mysql-files/`로 복사 후 실행.

```bash
sudo cp /mnt/downloads/customer_master.csv /var/lib/mysql-files/
sudo cp /mnt/downloads/customer_identity_map.csv /var/lib/mysql-files/
sudo cp /mnt/downloads/customer_profile.csv /var/lib/mysql-files/
```

---

## 증상: Ansible 배포 후 서비스 파일 환경변수 미치환

```
Environment=DEPLOY_TOKEN=배포 트리거 토큰 입력
```

서비스 재시작해도 토큰 값이 리터럴 텍스트로 남아 있음.

**원인**: Ansible이 `service.j2` 템플릿을 배포할 때 `{{ deploy_token }}` 변수가 치환되지 않은 채 저장됨. vars.yml 값은 로컬에서 정상이어도 EC2 Control Node의 레포가 `git pull`되지 않은 상태면 구버전 템플릿이 사용됨.

**확인**:
```bash
# ls-api VM에서
sudo cat /etc/systemd/system/private-api.service | grep DEPLOY_TOKEN
# 리터럴 텍스트가 보이면 미반영 상태
```

**해결**:
```bash
# EC2 Control Node에서
cd /opt/ansible/onprem-prod-repo
git pull

ansible-playbook ansible/site.yml \
  -i ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass \
  --limit ls-api

# ls-api에서 확인
sudo systemctl status private-api
```

---

## 증상: ansible ping UNREACHABLE — ls-db / ls-token (during banner)

```
UNREACHABLE! => {"msg": "Failed to connect to the host via ssh: ssh: connect to host 192.168.56.11 port 22: Connection timed out\nReceived disconnect from ... during banner exchange"}
```

ls-api(192.168.56.13)는 정상인데 ls-db / ls-token만 UNREACHABLE.

**원인**: EC2 Control Node에서 192.168.56.11 / 192.168.56.12는 직접 라우팅이 안 되고 ls-api를 경유해야 함. `hosts.yml`에 ProxyJump 설정 없으면 SSH가 직접 연결 시도하다 타임아웃.

**해결**: `hosts.yml`에 `ansible_ssh_common_args` 추가.

```yaml
mysql:
  hosts:
    ls-db:
      ansible_host: 192.168.56.11
      ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o ProxyJump=ansible@172.16.1.73'
tokenization:
  hosts:
    ls-token:
      ansible_host: 192.168.56.12
      ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o ProxyJump=ansible@172.16.1.73'
```

ProxyJump가 동작하려면 ls-api에 SSH 키가 먼저 배포돼 있어야 함 (setup-ssh-keys.sh 실행 순서 참고).

---

## 증상: PII 복호화 실패 (500 에러)

```
cryptography.fernet.InvalidToken
```

**원인**: `PII_AES_KEY` 환경변수가 서비스에 반영되지 않았거나, 마이그레이션에 사용한 키와 다른 키로 복호화 시도.

**확인**:
```bash
# ls-api에서
sudo systemctl status private-api
sudo journalctl -u private-api -n 30

# 환경변수 확인
sudo cat /etc/systemd/system/private-api.service | grep PII
```

**해결**:
```bash
# 서비스 재시작 (환경변수 반영)
sudo systemctl daemon-reload
sudo systemctl restart private-api
```

키가 다를 경우 → 마이그레이션 때 사용한 키로 `vault.yml` 수정 후 Ansible 재배포.

---

## 증상: 회원가입 후 JWT에 global_id가 NULL / 빈값

**발생 조건**: `USE_MOCK=false` 클라우드 연동 모드에서 회원가입 시.

**원인 1 — global_id 미생성**
`api_register`에서 `global_id`를 생성하는 코드가 없어 DB에 NULL로 저장됨.

**원인 2 — master_customer INSERT 누락**
`users` 테이블에만 INSERT하고 `master_customer`는 건너뜀. `master_customer.representative_name NOT NULL` 제약으로 온프레미스 스키마 무결성 위반.

**원인 3 — JWT gid 클레임 오입력**
`make_jwt(ls_user_id, global_id)` 호출 시 두 번째 인자에 `ls_user_id`를 넣어 `gid` 클레임이 틀린 값으로 발급됨.

**수정 내용** (`app.py` `api_register` 함수):
```python
ls_user_id = f"LS-{datetime.datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
global_id  = f"G-{uuid.uuid4().hex[:12].upper()}"

cur.execute('INSERT INTO master_customer (global_id, representative_name) VALUES (%s, %s)',
            (global_id, name))
cur.execute('INSERT INTO users (ls_user_id, global_id, email, name, password_hash) VALUES (%s, %s, %s, %s, %s)',
            (ls_user_id, global_id, email, name, generate_password_hash(password)))
db.commit()

token = make_jwt(ls_user_id, global_id)   # global_id 올바르게 전달
```

**확인 방법**:
```bash
# 회원가입 후 JWT 디코드 (base64로 payload 부분 확인)
TOKEN="eyJ..."
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
# → "gid" 값이 "G-XXXX..." 형태여야 함 (ls_user_id 형태 LS-YYYYMMDD-XXXX면 버그)

# DB 직접 확인 (ls-db VM)
mysql -u lifesync -p lifesync_onprem \
  -e "SELECT ls_user_id, global_id, name FROM users ORDER BY created_at DESC LIMIT 5;"

mysql -u lifesync -p lifesync_onprem \
  -e "SELECT global_id, representative_name FROM master_customer ORDER BY created_at DESC LIMIT 5;"
```

---

## 증상: 회원가입 시 온프레미스 users 테이블 없음 오류

```
Table 'lifesync_onprem.users' doesn't exist
```

**원인**: `onprem-prod-repo/ansible/roles/mysql/files/schema.sql` (실제 배포 파일)에 `users` 테이블이 없었음. `db/onprem_schema.sql`에는 있었지만 Ansible이 배포하는 파일은 별개.

**해결**: Ansible 배포 파일에 users 테이블 추가 후 재배포.
```bash
# EC2 Control Node에서
cd /opt/ansible/onprem-prod-repo
git pull

ansible-playbook ansible/site.yml \
  -i ansible/inventory/hosts.yml \
  --vault-password-file ~/.vault_pass \
  --limit ls-db

# ls-db에서 테이블 확인
mysql -u lifesync -p lifesync_onprem -e "SHOW TABLES;"
# users 테이블이 목록에 있어야 함
```

이미 배포된 DB에는 Ansible 재배포로 자동 추가됨 (`CREATE TABLE IF NOT EXISTS` 사용 중).

---

## 증상: IaC 재배포 후 VPN 터널 끊김

매일 9AM IaC 재배포로 AWS VPN Connection이 재생성되면 터널 IP가 바뀌어 StrongSwan 연결이 끊김.

**원인**: `/etc/ipsec.conf`의 `right=` 값이 구 터널 IP로 남아있어 AWS 측 응답이 없음.

**해결**: 로컬 PC에서 `scripts/update-vpn-tunnel.sh` 실행.

```bash
# 사전 조건: AWS CLI 설치 및 인증 완료 (aws configure)
cd /path/to/LS
bash scripts/update-vpn-tunnel.sh

# VPN Connection ID를 직접 지정하는 경우
VPN_CONNECTION_ID=vpn-xxxxxxxxx bash scripts/update-vpn-tunnel.sh
```

스크립트 동작:
1. `aws ec2 describe-vpn-connections`로 새 터널 IP 조회
2. ls-api SSH → `/etc/ipsec.conf` `right=` 업데이트
3. `/etc/ipsec.secrets` IP 업데이트
4. `sudo systemctl restart strongswan-starter`
5. `sudo ipsec status` 출력으로 ESTABLISHED 확인

**PSK 문제 (IaC 팀 고정 전)**: IaC 재배포 시 PSK도 바뀌는 경우 스크립트가 ls-api 기존 ipsec.secrets에서 PSK를 읽지만 이미 무효화된 값임. 이 경우:
```bash
# CF 설정 파일 다운로드(AWS 콘솔 → VPN Connection → Download Config)에서 PSK 확인 후
# ls-api에서 직접 수정
sudo nano /etc/ipsec.secrets
# <leftid> <새터널IP> : PSK "<새PSK값>"
sudo systemctl restart strongswan-starter
```

**근본 해결**: IaC팀이 CF에서 `PreSharedKey`를 Secrets Manager 고정값으로 지정하면 PSK는 불변 → 스크립트만으로 완전 자동화.

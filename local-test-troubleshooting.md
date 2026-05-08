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

**원인**: `ansible-pull` 명령에 `-i` 플래그 누락. 인벤토리 지정 없으면 호스트 변수 전부 undefined.

**해결**: `trigger_ansible.sh`에 `-i ansible/inventory/hosts.yml` 추가.

```bash
# 변경 전
ansible-pull -U <repo_url> ansible/site.yml

# 변경 후
ansible-pull -U <repo_url> -i ansible/inventory/hosts.yml ansible/site.yml
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

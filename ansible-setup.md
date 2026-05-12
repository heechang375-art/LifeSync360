# Ansible Control Node 설정 가이드

## 구조

```
EC2 (Ansible Control Node)
    ↓ SSH (VPN 터널 경유)
ls-api VM (172.16.1.73)      ← 브리지 IP (VPN 터널 엔드포인트)
server2 (192.168.56.x)       ← ls-api를 Jump Host로 경유
server3 (192.168.56.x)       ← ls-api를 Jump Host로 경유
```

> **VPN-gw는 로컬 테스트용으로만 사용, 실제 운영은 EC2가 Ansible Control Node**

---

## Ansible 통신 방향

```
EC2 (Control Node) → 각 서버 (단방향)
```

- EC2가 각 서버에 접속해서 명령 실행
- EC2 → VM 방향만 되면 됨
- EC2 pub키를 각 서버 authorized_keys에 등록

---

## 1단계 — EC2에서 SSH 키 생성

```bash
ssh-keygen -t rsa -b 4096

# 생성된 pub키 확인
cat ~/.ssh/id_rsa.pub

# 개인키 권한 확인 (600 이어야 함)
ls -la ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa
```

---

## 2단계 — 각 서버에 EC2 pub키 등록

### ls-api VM
```bash
echo "ssh-rsa AAAA....ec2-user@ip-xxx" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 755 /home/<유저명>    # 홈 디렉토리 권한 중요
```

### server2, server3도 동일하게 적용

---

## 3단계 — SSH 권한 체크리스트

| 항목 | 정상값 | 확인 명령어 |
|------|--------|------------|
| 홈 디렉토리 | 755 | `ls -la /home/<유저명>` |
| .ssh 디렉토리 | 700 | `ls -la ~/.ssh/` |
| authorized_keys | 600 | `ls -la ~/.ssh/authorized_keys` |
| id_rsa (EC2) | 600 | `ls -la ~/.ssh/id_rsa` |
| PubkeyAuthentication | yes | `grep PubkeyAuthentication /etc/ssh/sshd_config` |

> **주의:** 홈 디렉토리가 750이면 SSH 키 인증 거부됨 → 755로 변경 필요

---

## 4단계 — SSH config 설정 (Jump Host)

ls-api를 Jump Host로 사용해서 나머지 서버 접속:

```bash
nano ~/.ssh/config
```

```
Host ls-api
    HostName 172.16.1.73
    User ls-api
    IdentityFile ~/.ssh/id_rsa

Host server2
    HostName 192.168.56.x
    User <유저명>
    ProxyJump ls-api
    IdentityFile ~/.ssh/id_rsa

Host server3
    HostName 192.168.56.x
    User <유저명>
    ProxyJump ls-api
    IdentityFile ~/.ssh/id_rsa
```

---

## 5단계 — ansible.cfg 설정

```bash
sudo nano /etc/ansible/ansible.cfg
```

```ini
[defaults]
private_key_file = ~/.ssh/id_rsa
host_key_checking = False
```

---

## 6단계 — inventory 설정

```bash
sudo nano /etc/ansible/hosts
```

```ini
[local_vms]
ls-api ansible_host=172.16.1.73 ansible_user=ls-api

[jump_hosts]
server2 ansible_host=192.168.56.x ansible_user=<유저명> ansible_ssh_common_args='-o ProxyJump=ls-api@172.16.1.73'
server3 ansible_host=192.168.56.x ansible_user=<유저명> ansible_ssh_common_args='-o ProxyJump=ls-api@172.16.1.73'
```

> **주의:**
> - ls-api는 브리지 IP(172.16.1.73)로만 등록 (Host-only IP 192.168.56.13은 VPN 터널 못 탐)
> - server2, server3는 Host-only IP로 등록 (ls-api Jump Host 경유)

---

## 7단계 — 접속 테스트

```bash
# SSH 직접 접속 테스트
ssh ls-api@172.16.1.73
ssh server2  # SSH config 기준

# Ansible ping 테스트
ansible all -m ping

# 상세 로그
ansible all -m ping -vvv
```

---

## 트러블슈팅

### Permission denied
```bash
# 1. 홈 디렉토리 권한 확인
ls -la /home/<유저명>
chmod 755 /home/<유저명>

# 2. authorized_keys 권한 확인
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# 3. EC2 pub키가 정확히 등록됐는지 확인
cat ~/.ssh/authorized_keys
# EC2의 id_rsa.pub 내용과 정확히 일치하는지 대조
cat ~/.ssh/id_rsa.pub  # EC2에서
```

### SSH 타임아웃
```bash
# EC2 → ls-api 통신 확인
ping 172.16.1.73
nc -zv 172.16.1.73 22

# VPN 터널 상태 확인
sudo ipsec status | grep ESTABLISHED

# AWS 콘솔 확인
# EC2 Security Group Outbound → SSH(22) 허용
# TGW 라우팅 → 172.16.1.73/32 → VPN Attachment
```

### during banner 에러
```bash
# SSH 배너 비활성화
sudo nano /etc/ssh/sshd_config
# Banner none 추가

sudo systemctl restart sshd
```

### Ansible이 다른 키로 접속하는 경우
```bash
# Ansible이 사용하는 키 확인
ansible all -m ping -vvv 2>&1 | grep "identity"

# ansible.cfg에 키 경로 명시
sudo nano /etc/ansible/ansible.cfg
# private_key_file = ~/.ssh/id_rsa
```

### ansible all -m ping 실행 위치
```
반드시 EC2 (Ansible Control Node)에 로그인한 상태에서 실행
```

---

## Ansible 멱등성

Ansible은 **멱등성(Idempotency)** 기반으로 동작:
- 현재 상태와 다른 것만 변경
- 이미 원하는 상태면 skip

| 모듈 | 멱등성 |
|------|--------|
| `apt`, `yum` | ✅ 보장 |
| `copy`, `template` | ✅ 보장 |
| `service` | ✅ 보장 |
| `command`, `shell` | ❌ 매번 실행 |

`command`/`shell` 멱등성 유지:
```yaml
- name: 파일 없을때만 실행
  command: ./setup.sh
  args:
    creates: /etc/myapp/config
```

# 온프렘 로컬 테스트 — 잔여 항목

프로젝트: LifeSync360 | 작성자: 황희창 | 작성일: 2026-04-30

---

## 환경 정보

| VM | IP | 역할 |
|---|---|---|
| ls-vpngw | 192.168.56.10 | 임시 Ansible Control Node |
| ls-db | 192.168.56.11 | MySQL |
| ls-token | 192.168.56.12 | Tokenization Service |
| ls-api | 192.168.56.13 | Private API + Cron |

Ansible Control Node에서 실행 (ls-vpngw SSH 접속 후 진행)
```bash
ssh ansible@192.168.56.10
cd /opt/ansible/onprem-prod-repo/ansible
```

---

## ✅ 완료 — ls-api private_api role 배포 + Nginx 확인
## ✅ 완료 — 크로스 VM MySQL 연결 (환경변수, 포트, app user 접속)

---

## 테스트 1 — 크로스 VM tokenize 실제 호출 (ls-token 서비스 기동 후 진행)

```bash
# tokenization 서비스 상태 확인
ssh ansible@192.168.56.12
sudo systemctl status tokenization
```

### 크로스 VM tokenize 호출

ls-vpngw 또는 ls-token에서:
```bash
curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "phone_number", "value": "01012345678"}'
# 기대값: {"token_id": "xxxx-xxxx-..."}
```

---

## 테스트 2 — 엣지 케이스

### 2-1. 동일 값 중복 tokenize (dedup 확인)

```bash
# 같은 값으로 두 번 호출
curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "phone_number", "value": "01099999999"}'

curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "phone_number", "value": "01099999999"}'

# 기대값: 두 응답의 token_id가 동일해야 함
```

### 2-2. 허용되지 않은 field 요청

```bash
curl -X POST http://192.168.56.12:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"field": "address", "value": "서울시 강남구"}'

# 기대값: HTTP 400 + {"detail": "Field 'address' not in allowed fields"}
```

허용 필드 목록: `resident_number`, `phone_number`, `account_number`, `card_number`, `email`

### 2-3. 존재하지 않는 token_id로 detokenize

```bash
curl http://192.168.56.12:8000/detokenize/00000000-0000-0000-0000-000000000000

# 기대값: HTTP 404 + {"detail": "Token not found"}
```

---

## 완료 기준

| 항목 | 기대값 |
|---|---|
| ls-api private_api 배포 | ✅ 완료 |
| /health (Nginx 경유) | ✅ 완료 |
| 크로스 VM MySQL 포트 | ✅ 완료 |
| app user 접속 | ✅ 완료 |
| 크로스 VM tokenize | token_id 반환 |
| 중복 tokenize | 동일한 token_id 반환 |
| 잘못된 field | HTTP 400 |
| 없는 token_id detokenize | HTTP 404 |

---

## 이 이후 — IaC 완성 후 테스트 (로컬 불가)

- AWS Secrets Manager 실제 연동 (boto3 secretsmanager 호출)
- trigger_ansible.sh production 모드 (SSM SendCommand 실제 호출)
- EC2 Ansible Control Node → VM SSH 배포
- VPN 터널 경유 통신 전체 확인

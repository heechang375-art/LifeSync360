# Lambda `lifesync-onprem-customer-query` 배포 가이드

> **목적**: LifeSync VPC에 TGW Attachment 추가 + Lambda 배포 + ECS 권한 + 로그인 검증
> **사전 확인 완료 사항**
> - VPC: `vpc-0a002fc33f22824ad` (`lifesync-dev-lifesync-vpc`, 10.0.0.0/16)
> - Private Subnet A: `subnet-0d2c0938c858fa844` (10.0.10.0/24)
> - Private Subnet B: `subnet-047cd3d241c9831a7` (10.0.11.0/24)
> - Private RT: `rtb-0c34549c1138b8119`
> - 현재 RT는 NAT만 있고 온프레 라우팅 없음 → TGW Attachment 신규 필요
> - 온프레 private_api: `http://172.16.1.73`
> - Account ID: `354493396671`
> - Region: `ap-northeast-2`

---

## STEP 0 — 변수 채우기 (조회 4개)

```bash
TGW_ID=$(aws ec2 describe-transit-gateways \
  --query 'TransitGateways[0].TransitGatewayId' --output text \
  --region ap-northeast-2)
echo "TGW_ID=$TGW_ID"

TGW_RT_ID=$(aws ec2 describe-transit-gateway-route-tables \
  --query 'TransitGatewayRouteTables[?DefaultPropagationRouteTable==`true`].TransitGatewayRouteTableId | [0]' \
  --output text --region ap-northeast-2)
echo "TGW_RT_ID=$TGW_RT_ID"

ATTACH_ID=$(aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=vpc-id,Values=vpc-0a002fc33f22824ad" \
  --query 'TransitGatewayVpcAttachments[?State==`available`].TransitGatewayAttachmentId | [0]' \
  --output text --region ap-northeast-2)
echo "ATTACH_ID=$ATTACH_ID"

aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RT_ID \
  --filters "Name=state,Values=active" \
  --query 'Routes[].[DestinationCidrBlock,Type]' --output table \
  --region ap-northeast-2
```

→ 마지막 출력에서 온프레 CIDR(보통 `172.16.x.x`) 확인 후:

```bash
ONPREM_CIDR="172.16.1.0/24"   # ← 실제 출력값으로 교체
```

---

## STEP 1 — LifeSync VPC TGW Attachment 추가 (ATTACH_ID가 `None`일 때만)

```bash
if [ "$ATTACH_ID" = "None" ] || [ -z "$ATTACH_ID" ]; then
  ATTACH_ID=$(aws ec2 create-transit-gateway-vpc-attachment \
    --transit-gateway-id $TGW_ID \
    --vpc-id vpc-0a002fc33f22824ad \
    --subnet-ids subnet-0d2c0938c858fa844 subnet-047cd3d241c9831a7 \
    --query 'TransitGatewayVpcAttachment.TransitGatewayAttachmentId' --output text \
    --region ap-northeast-2)
  echo "신규 ATTACH_ID=$ATTACH_ID"
  aws ec2 wait transit-gateway-vpc-attachment-available \
    --transit-gateway-attachment-ids $ATTACH_ID --region ap-northeast-2
fi
```

---

## STEP 2 — LifeSync VPC Private RT에 온프레 라우팅 추가

```bash
aws ec2 create-route \
  --route-table-id rtb-0c34549c1138b8119 \
  --destination-cidr-block $ONPREM_CIDR \
  --transit-gateway-id $TGW_ID \
  --region ap-northeast-2

aws ec2 describe-route-tables --route-table-ids rtb-0c34549c1138b8119 \
  --query 'RouteTables[0].Routes[]' --output table \
  --region ap-northeast-2
```

→ `${ONPREM_CIDR} → tgw-xxx` 라우팅 추가 확인.

---

## STEP 3 — TGW Route Table propagation 활성화

```bash
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id $TGW_RT_ID \
  --transit-gateway-attachment-id $ATTACH_ID \
  --region ap-northeast-2 2>/dev/null || echo "이미 propagation 등록됨"

aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id $TGW_RT_ID \
  --filters "Name=state,Values=active" \
  --query 'Routes[?DestinationCidrBlock==`10.0.0.0/16`]' --output table \
  --region ap-northeast-2
```

→ `10.0.0.0/16` 라우팅이 propagated로 보여야 OK.

---

## STEP 4 — 온프레 ipsec.conf 수정 (ls-api에서 실행, 온프레 담당자)

```bash
ssh ansible@192.168.56.13   # ls-api

sudo sed -i 's|^rightsubnet=.*|&,10.0.0.0/16|' /etc/ipsec.conf
sudo cat /etc/ipsec.conf | grep rightsubnet   # 확인: 콤마로 CIDR 추가됨

sudo systemctl restart strongswan-starter
sleep 3
sudo ipsec status   # ESTABLISHED 확인
```

---

## STEP 5 — Lambda 전용 SG 생성

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name lifesync-onprem-query-lambda-sg \
  --description "Lambda outbound to onprem private_api" \
  --vpc-id vpc-0a002fc33f22824ad \
  --query 'GroupId' --output text \
  --region ap-northeast-2)

# default outbound 제거 + 명시 outbound만 허용
aws ec2 revoke-security-group-egress --group-id $SG_ID \
  --protocol all --port -1 --cidr 0.0.0.0/0 \
  --region ap-northeast-2 2>/dev/null

aws ec2 authorize-security-group-egress --group-id $SG_ID \
  --protocol tcp --port 80 --cidr 172.16.1.73/32 \
  --region ap-northeast-2

echo "SG_ID=$SG_ID"
```

---

## STEP 6 — Lambda IAM Role 생성

```bash
cat > /tmp/lambda-trust.json << 'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role \
  --role-name lifesync-onprem-query-lambda-role \
  --assume-role-policy-document file:///tmp/lambda-trust.json

aws iam attach-role-policy \
  --role-name lifesync-onprem-query-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name lifesync-onprem-query-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

ROLE_ARN=$(aws iam get-role \
  --role-name lifesync-onprem-query-lambda-role \
  --query 'Role.Arn' --output text)
echo "ROLE_ARN=$ROLE_ARN"
```

---

## STEP 7 — Lambda ZIP 빌드 + 함수 생성

```bash
cd C:/users/campus3S026/ls/lambda/onprem_customer_query
bash build.sh   # → onprem_customer_query.zip 생성

aws lambda create-function \
  --function-name lifesync-onprem-customer-query \
  --runtime python3.11 \
  --handler handler.handler \
  --role $ROLE_ARN \
  --zip-file fileb://onprem_customer_query.zip \
  --vpc-config "SubnetIds=subnet-0d2c0938c858fa844,subnet-047cd3d241c9831a7,SecurityGroupIds=$SG_ID" \
  --environment "Variables={PRIVATE_API_URL=http://172.16.1.73}" \
  --timeout 8 \
  --memory-size 256 \
  --region ap-northeast-2

# Active 상태 대기
aws lambda wait function-active \
  --function-name lifesync-onprem-customer-query \
  --region ap-northeast-2
```

---

## STEP 8 — ECS Task Role에 `lambda:InvokeFunction` 권한 추가

```bash
cat > /tmp/lambda-invoke-policy.json << 'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"lambda:InvokeFunction","Resource":"arn:aws:lambda:ap-northeast-2:354493396671:function:lifesync-onprem-customer-query"}]}
EOF

aws iam put-role-policy --role-name lifesync-EcsPlatformTaskRole \
  --policy-name LambdaInvokeOnpremQuery \
  --policy-document file:///tmp/lambda-invoke-policy.json

aws iam put-role-policy --role-name lifesync-EcsAdminTaskRole \
  --policy-name LambdaInvokeOnpremQuery \
  --policy-document file:///tmp/lambda-invoke-policy.json
```

---

## STEP 9 — Lambda 단독 테스트 (인프라 전체 검증)

```bash
cat > /tmp/test-event.json << 'EOF'
{"action": "get_consent", "global_id": "G000000001"}
EOF

aws lambda invoke \
  --function-name lifesync-onprem-customer-query \
  --cli-binary-format raw-in-base64-out \
  --payload file:///tmp/test-event.json \
  /tmp/output.json \
  --region ap-northeast-2

cat /tmp/output.json
```

### 결과 해석

| 결과 | 의미 | 다음 |
|---|---|---|
| `{"statusCode": 200, "body": "{...consents...}"}` | ✅ Lambda + VPN + private_api 다 OK | STEP 10 진행 |
| `{"statusCode": 502, "body": "...timeout..."}` | VPN/private_api 미동작 | STEP 4 ipsec 재확인 |
| `{"statusCode": 502, "body": "...connection refused..."}` | private_api 프로세스 다운 | ls-api에서 `systemctl status private-api` |
| `{"errorMessage": "Task timed out"}` | Lambda timeout (8초) | timeout 15초로 늘리기 |
| `{"errorType": "ResourceNotFoundException"}` | (생기면 인프라 미적용) | STEP 1~3 재확인 |

---

## STEP 10 — 푸시 + ECS 재배포 + 로그인 검증

### 10-1. 코드 푸시

```bash
git -C C:/users/campus3S026/ls add \
  lifesync360-platform/app.py \
  lifesync360-platform/taskdef.json \
  lifesync360-platform/templates/login.html \
  admin-platform/taskdef.json

git -C C:/users/campus3S026/ls commit -m "fix: _call_onprem 예외 보강 + taskdef DB_NAME=lifesync360 + admin ONPREM_QUERY_LAMBDA env"
git -C C:/users/campus3S026/ls push
```

### 10-2. ECS 강제 재배포 (CodePipeline 미동작 시)

```bash
aws ecs update-service --cluster lifesync-cluster \
  --service lifesync-platform-service \
  --force-new-deployment --region ap-northeast-2

aws ecs update-service --cluster lifesync-cluster \
  --service lifesync-admin-service \
  --force-new-deployment --region ap-northeast-2
```

→ 2~3분 대기 (Blue/Green 또는 Rolling 완료).

### 10-3. 로그인 재시도

브라우저에서 ALB URL `/login` 접속 → 로그인 시도

### 결과 해석

| 화면 메시지 | 의미 | 대응 |
|---|---|---|
| `이메일 또는 비밀번호가 올바르지 않습니다.` | ✅ Lambda → 온프레 흐름 OK. 단 100만 유저는 `_seed_hash` 패턴이라 로그인 불가 | STEP 11 패스워드 수동 재설정 또는 신규 가입 |
| `로그인 처리 중 오류 — Read timed out` | VPN/private_api 도달 실패 | STEP 9 다시 |
| `로그인 처리 중 오류 — AccessDeniedException` | Task Role 권한 미반영 | ECS 재배포 |
| `서버 응답 오류 (status: 502)` | Lambda 응답 오류 | CloudWatch Logs 확인 |

---

## STEP 11 — 시뮬레이션 유저 패스워드 수동 재설정 (로그인 검증용)

100만 유저는 `_seed_hash` 패턴(이메일 기반 해시)이라 평문 모름. 한 명 골라서 평문 SHA256 hex로 교체:

```bash
ssh ansible@192.168.56.11   # ls-db

mysql -u root -p lifesync_onprem << 'SQL'
-- user1@lifesync-test.com에 'test1234' 평문 설정
UPDATE users
SET password_hash = SHA2('test1234', 256)
WHERE login_email = 'user1@lifesync-test.com';

-- 확인 (64자 SHA256 hex)
SELECT login_email, LENGTH(password_hash), password_hash
FROM users
WHERE login_email = 'user1@lifesync-test.com';
SQL
```

→ 브라우저 `/login`에서 `user1@lifesync-test.com` / `test1234`로 로그인.

---

## 검증 체크리스트

- [ ] STEP 0: TGW_ID, TGW_RT_ID, ATTACH_ID, ONPREM_CIDR 변수 채워짐
- [ ] STEP 1: LifeSync VPC TGW Attachment 생성 (`available`)
- [ ] STEP 2: Private RT에 온프레 CIDR 라우팅 추가
- [ ] STEP 3: TGW RT에서 `10.0.0.0/16` propagated
- [ ] STEP 4: ipsec status `ESTABLISHED`
- [ ] STEP 5: SG `lifesync-onprem-query-lambda-sg` 생성
- [ ] STEP 6: IAM Role `lifesync-onprem-query-lambda-role` 생성
- [ ] STEP 7: Lambda `lifesync-onprem-customer-query` Active
- [ ] STEP 8: ECS Task Role에 Lambda invoke 권한
- [ ] STEP 9: `aws lambda invoke` 결과 200
- [ ] STEP 10: 푸시 + ECS 재배포 + 로그인 401 (=흐름 통과)
- [ ] STEP 11: user1 패스워드 재설정 후 정상 로그인

---

## 트러블슈팅 빠른 명령

### Lambda 로그 보기
```bash
aws logs tail /aws/lambda/lifesync-onprem-customer-query --since 10m --follow --region ap-northeast-2
```

### ECS 로그 보기
```bash
aws logs tail /ecs/lifesync-platform --since 10m --follow --region ap-northeast-2
aws logs tail /ecs/lifesync-admin --since 10m --follow --region ap-northeast-2
```

### Lambda VPC config 확인
```bash
aws lambda get-function-configuration --function-name lifesync-onprem-customer-query \
  --query '[VpcConfig,Environment.Variables]' --region ap-northeast-2
```

### Lambda Timeout 늘리기
```bash
aws lambda update-function-configuration \
  --function-name lifesync-onprem-customer-query \
  --timeout 15 --region ap-northeast-2
```

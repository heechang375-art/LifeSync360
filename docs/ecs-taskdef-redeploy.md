# ECS Task Definition 재등록 + 강제 재배포 가이드 (platform)

> **확정된 환경 정보**
> - Cluster: `lifesync-service-ecs`
> - Service: `lifesync-dev-21-lifesync-ecs-existing-vpc-v4-svc`
> - Task Definition family: `lifesync-dev-21-lifesync-ecs-existing-vpc-v4-td`
> - Container Name: `app` (Service LB가 가리키는 이름)
> - Container Port: `80` (Gunicorn binding 포트)
> - DynamoDB 테이블: `lifesync_customer_result`
> - Region: `ap-northeast-2`
>
> **taskdef.json + appspec.yaml에 이미 위 설정 박혀있음** (family/name/port 정합 완료)
>
> **상황**: 현재 ECS에 등록된 Task Definition revision이 옛날 거라 env에 USE_MOCK만 있음. taskdef.json 기준으로 새 revision 등록해서 env 7개 + secrets 5개 다 채워야 함.
>
> **소요**: 2~3분
> **환경**: PowerShell (Windows)

---

## STEP 1 — 현재 이미지 URI 가져오기

```powershell
$IMAGE = (aws ecs describe-task-definition --task-definition lifesync-dev-21-lifesync-ecs-existing-vpc-v4-td --query 'taskDefinition.containerDefinitions[0].image' --output text --region ap-northeast-2)
```

```powershell
echo "현재 이미지: $IMAGE"
```

---

## STEP 2 — taskdef.json 읽고 `<IMAGE1_NAME>` 치환 + 임시 파일 저장 (BOM 없이)

```powershell
(Get-Content C:/users/campus3S026/ls/lifesync360-platform/taskdef.json -Raw) -replace '<IMAGE1_NAME>', $IMAGE | Set-Content -Path $env:TEMP\td-platform.json -Encoding ASCII
```

> PowerShell 5.1 `Out-File -Encoding utf8`은 BOM이 붙어서 AWS CLI가 못 읽음. ASCII 인코딩(taskdef.json에 한글 없음) 또는 .NET `UTF8Encoding($false)` 사용.
>
> (family는 이미 `lifesync-dev-21-lifesync-ecs-existing-vpc-v4-td`로 박혀있음)

---

## STEP 3 — Task Definition 새 revision 등록

```powershell
aws ecs register-task-definition --cli-input-json file://$env:TEMP\td-platform.json --region ap-northeast-2 --query 'taskDefinition.revision'
```

→ 출력에 새 revision 번호 (예: `13`).

---

## STEP 4 — Service 강제 재배포

```powershell
aws ecs update-service --cluster lifesync-service-ecs --service lifesync-dev-21-lifesync-ecs-existing-vpc-v4-svc --task-definition lifesync-dev-21-lifesync-ecs-existing-vpc-v4-td --force-new-deployment --region ap-northeast-2
```

---

## STEP 5 — 배포 진행 상황 확인 (2~3분 후)

```powershell
aws ecs describe-services --cluster lifesync-service-ecs --services lifesync-dev-21-lifesync-ecs-existing-vpc-v4-svc --query 'services[0].deployments[].[status,taskDefinition,desiredCount,runningCount]' --output table --region ap-northeast-2
```

→ `PRIMARY` 상태에서 `runningCount == desiredCount` 되면 새 컨테이너 RUNNING.

---

## STEP 6 — 새 revision에 env 정상 반영 확인

```powershell
aws ecs describe-task-definition --task-definition lifesync-dev-21-lifesync-ecs-existing-vpc-v4-td --query 'taskDefinition.containerDefinitions[0].environment' --output table --region ap-northeast-2
```

→ 7개 env 다 보여야 함:
- AWS_REGION = ap-northeast-2
- DB_NAME = lifesync360
- DYNAMO_TABLE = `lifesync_customer_result`
- REDIS_PORT = 6379
- USE_MOCK = false
- PROFILE_SYNC_LAMBDA = customer-profile-sync
- ONPREM_QUERY_LAMBDA = lifesync-onprem-customer-query

---

## STEP 7 — DynamoDB에 Mock 유저 데이터 추가

`test@lifesync.com` 로그인 시 토큰의 `gid='G000000001'`로 발급되므로, 그 ID로 데이터 있어야 점수/등급 표시.

```powershell
aws dynamodb put-item --table-name lifesync_customer_result --item "{\"global_id\":{\"S\":\"G000000001\"},\"dynamic_grade\":{\"S\":\"VIP\"},\"dynamic_score\":{\"S\":\"92.4\"},\"health_score\":{\"S\":\"88\"},\"vip_prob\":{\"S\":\"0.85\"},\"signup_prob\":{\"S\":\"0.72\"},\"rec_prob\":{\"S\":\"0.91\"},\"next_best_action\":{\"S\":\"건강검진 받기\"},\"update_time\":{\"S\":\"2026-05-14T06:00:00\"}}" --region ap-northeast-2
```

확인:
```powershell
aws dynamodb get-item --table-name lifesync_customer_result --key '{\"global_id\":{\"S\":\"G000000001\"}}' --region ap-northeast-2
```

→ Item에 데이터 보이면 OK.

---

## STEP 8 — 로그인 재시도

브라우저에서 ALB URL `/login` → `test@lifesync.com` / `password123`

**기대하는 화면**:
- 헤더 등급 뱃지: `VIP`
- 홈 점수 게이지: 종합 `92.4`, 건강 `88`
- 추천 탭 / 홈 추천 미리보기: Aurora `product_master` 1,200건 기반 조회

---

## 트러블슈팅

### `An error occurred (InvalidParameterException): The container XXX does not exist in the task definition.`
- Service의 LoadBalancer가 기대하는 container name과 taskdef `containerDefinitions[].name`이 다름
- → taskdef.json의 `"name"`을 service가 기대하는 이름(여기선 `app`)으로 변경 후 register
- appspec.yaml의 `ContainerName`도 같이 정정

### `An error occurred (InvalidParameterException): The container XXX did not have a container port YYY defined.`
- Service LB가 기대하는 container port와 taskdef `portMappings[].containerPort`가 다름
- → taskdef.json의 `containerPort`를 service가 기대하는 포트(여기선 `80`)로 변경 후 register
- appspec.yaml의 `ContainerPort`도 같이 정정

### `ParamValidation ... text contents could not be decoded`
- PowerShell `Out-File -Encoding utf8`이 BOM을 붙여서 AWS CLI가 못 읽음
- → `Set-Content -Encoding ASCII` 사용 (한글 없는 파일에 한해)
- 또는 `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`

### Task가 START 못 하면

```powershell
aws ecs describe-services --cluster lifesync-service-ecs --services lifesync-dev-21-lifesync-ecs-existing-vpc-v4-svc --query 'services[0].events[:5]' --region ap-northeast-2
```

→ events에 실패 사유 (Secrets Manager 권한, AURORA_HOST 못 찾음 등).

### CloudWatch Logs 실시간

```powershell
aws logs tail /ecs/lifesync-platform --since 5m --follow --region ap-northeast-2
```

(log group 이름이 다르면 `/aws/ecs/...` 등으로 변경)

### Service의 현재 Task Definition 확인

```powershell
aws ecs describe-services --cluster lifesync-service-ecs --services lifesync-dev-21-lifesync-ecs-existing-vpc-v4-svc --query 'services[0].taskDefinition' --region ap-northeast-2
```

→ revision 번호가 STEP 3에서 받은 번호와 같으면 정상.

---

## 체크리스트

- [ ] STEP 3: register 후 새 revision 번호 출력
- [ ] STEP 4: update-service 트리거
- [ ] STEP 5: PRIMARY RUNNING (runningCount == desiredCount)
- [ ] STEP 6: env 7개 다 보임 (특히 DYNAMO_TABLE=lifesync_customer_result)
- [ ] STEP 7: DynamoDB G000000001 데이터 put + get 성공
- [ ] STEP 8: 로그인 → 점수/등급 화면 표시

---

## admin (뒤로 미룬 작업)

admin도 동일 패턴으로 처리:
1. `aws ecs list-task-definitions` 로 admin family 이름 확인
2. `admin-platform/taskdef.json`의 `family` 값을 그 이름으로 수정
3. 위 STEP 1~5 동일 패턴 (admin service 이름으로)

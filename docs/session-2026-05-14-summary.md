# 2026-05-14 작업 세션 요약

## 1. 큰 흐름

- **목적**: ECS 시연 환경에서 Cloud 데이터(DynamoDB) 기반 로그인/점수/등급 화면 동작
- **결과**: Mock 모드로 시연 가능한 상태 + ECS 인프라 정합 진행 중

---

## 2. 작업 흐름 (시간순)

### 2-1. 시연용 화면 정리 (`feat(cloud)` 푸시)
- 플랫폼 점수 토글: 4개(종합/건강/금융/행동) → 2개(종합/건강)
  - DynamoDB에 `fin_score`/`behavior_score` 컬럼 없음
- MY 탭 가입상품 드릴다운 제거 (Aurora `customer_recommend_history` 데이터 없음)
- settings.html 회원번호 행 제거 (PII 최소화)
- settings.html 등급 업그레이드 가이드 섹션 제거 (`/api/upgrade-actions` 빈 배열)
- `/api/dashboard` 응답에서 `fin_score`/`behavior_score` 제거
- `product.html` `product_id` 전달 (`customer_recommend_history.clicked_flag/purchased_flag` UPDATE 동작 보장)

### 2-2. ECS Task Definition 정합 (`fix(ecs)` 푸시)
- 실 환경 정합 5가지 수정:
  - `family`: `lifesync-platform` → `lifesync-dev-21-lifesync-ecs-existing-vpc-v4-td`
  - `containerDefinitions[0].name`: `platform` → `app`
  - `portMappings[0].containerPort`: `8000` → `80`
  - `environment` `DB_NAME`: `lifesync` → `lifesync360`
  - `environment` `DYNAMO_TABLE`: `lifesync-scores` → `lifesync_customer_result`
- `appspec.yaml` 동일 정정
- `taskRoleArn`/`executionRoleArn` 실 IaC 생성 Role로 정정
  - `lifesync-dev-21-lifesync-ecs-exist-EcsExecutionRole-A2eQoeWGranp`
  - `lifesync-dev-21-lifesync-ecs-existing-v-EcsTaskRole-3EkSGfTWb9ZF`

### 2-3. CodePipeline `taskdef.json` 반영
- buildspec.yml이 `imagedefinitions.json`만 만들어서 ECS env/secrets는 옛 revision 복제 → taskdef.json 무시됨
- `lifesync360-platform/deploy/buildspec.yml`에 `register-task-definition` + `update-service --force-new-deployment` 단계 추가
- CONTAINER_NAME `platform` → `app` 정합
- `docs/codebuild-role-policy.json`에 `ecs:RegisterTaskDefinition`/`UpdateService`/`iam:PassRole` 권한 추가

### 2-4. JWT_SECRET 정합
- ECS env에 JWT 없으면 코드 dev fallback 사용 → 컨테이너 재배포마다 키 다를 수 있음 우려
- `taskdef.json` `secrets`에 SSM Parameter Store ARN으로 박음:
  - `valueFrom: arn:aws:ssm:ap-northeast-2:354493396671:parameter/lifesync360/jwt-secret`
- `/health`에 디버그 정보 추가 (`jwt_from_env`/`jwt_len`/`jwt_prefix`/`use_mock`/`dynamo_table`)

### 2-5. 인증 흐름 (`api_login`/`api_register`) Mock 강제
- `lifesync-onprem-customer-query` Lambda 미배포 상태
- 시연용으로 인증은 `MOCK_USERS` 기반 검증, 토큰 발급 (Lambda 우회)
- `api_me`는 `_call_onprem` 실패 시 Mock fallback 처리 (`name`/`email`)
- `grade`는 DynamoDB `get_item(global_id).dynamic_grade`에서 가져옴
- `/api/event`는 `product_id` 없으면 즉시 200, Aurora try/except로 보강

### 2-6. USE_MOCK env 기반 복귀 (옵션 C 패턴)
- `USE_MOCK = False` 강제 → `os.environ.get('USE_MOCK', 'true').lower() != 'false'` 복귀
- `mock_data` import 전체 복원 (인증 + USE_MOCK 분기 둘 다에서 사용)
- 로컬 (env 없으면 USE_MOCK=true): 모든 라우트 mock 데이터
- ECS (env=false): 인증만 Mock, 데이터는 Cloud DynamoDB/Aurora
- admin-platform도 동일 패턴

### 2-7. mock_data global_id를 DynamoDB 실 적재값에 매핑
- `G000000001`/`G000000002`/`G000000003` → `G000297409`/`G000672689`/`G000115282`
- Mock 토큰의 `gid` 클레임이 DynamoDB 실데이터와 매칭 → 로그인 후 점수/등급 표시

### 2-8. ECS 재배포 흐름 트러블슈팅
- 옛 revision 사용 중 (revision 44가 USE_MOCK=true 하나만 + secrets 빈 배열) → CodePipeline 흐름 정정 후 새 revision 등록
- "ECS unable to assume role" → Role ARN 정정
- "container `app` does not exist" → `name` 정합
- "container `app` did not have port 80" → `containerPort` 정합
- BOM 인코딩 에러 → PowerShell `Set-Content -Encoding ASCII` 사용
- CodeBuild Role 권한 추가 → `lifesync-dev-svcplt-codebuild-role`에 `ecs:RegisterTaskDefinition` 등 inline 정책 추가

### 2-9. 미해결 (사용자 자리 비웠을 때 진행 멈춤)
- ECS Task Execution Role(`lifesync-dev-21-lifesync-ecs-exist-EcsExecutionRole-A2eQoeWGranp`)에 SSM 권한 추가 필요
  - `ssm:GetParameters` on `arn:aws:ssm:ap-northeast-2:354493396671:parameter/lifesync360/*`
- ECS Task Role(`lifesync-dev-21-lifesync-ecs-existing-v-EcsTaskRole-3EkSGfTWb9ZF`)에 DynamoDB 권한 추가 필요
  - `dynamodb:GetItem/Query/Scan` on `lifesync_customer_result`
- 새 task가 PENDING 상태로 멈춤 (SSM 권한 부재로 추정)

---

## 3. 작성한 문서 파일

| 파일 | 내용 |
|---|---|
| `docs/lambda-onprem-query-deploy.md` | Lambda + VPN 배포 가이드 |
| `docs/ecs-taskdef-redeploy.md` | ECS Task Definition 수동 register/force-deploy 가이드 |
| `docs/iac-ecs-taskdef-spec.md` | IaC 영구 반영 명세 (CloudFormation 형식) |
| `docs/demo-removed-items-rollout.md` | 시연용 제거 항목 + 운영 전환 가이드 |
| `docs/codebuild-role-policy.json` | CodeBuild Role 정책 (ECS 권한 포함) |
| `service_db_reference.md` | Aurora Service-DB 11개 테이블 정합 |

---

## 4. 푸시된 커밋 (시간순)

| 커밋 | 메시지 |
|---|---|
| `fec4e20` | `feat(auth+pii)`: 실DB 기준 PII/auth 흐름 정비 |
| `814b793` | `chore`: admin Aurora 정합 + Service-DB 자산 |
| `4dc4c13` | `chore`: `.gitignore`에서 `.DS_Store` 제거 |
| `ef3d1e4` | `feat(cloud)`: Mock 비활성 + 화면 정리 + Service-DB 레퍼런스 |
| `c046562` | `fix(temp)`: 인증 Mock 강제 + api_me fallback |
| `97a47c5` | `fix(ecs)`: taskdef family/container/port + docs |
| `fc03540` | `fix(ecs)`: taskdef secrets 통째로 비움 |
| `74f49d6` | `fix(demo)`: USE_MOCK=True + mock_data global_id 매핑 |
| `8fcaca6` | `fix`: USE_MOCK=False 복귀 + api_event 안전 처리 |
| `5af0e0c` | `fix`: JWT_SECRET을 SSM에서 주입 |
| `2ac58aa` | `fix`: JWT_SECRET env 평문 + grade null JS 안전 |
| `831fdad` | `debug`: `/health`에 JWT/USE_MOCK env 확인 |
| `3c5593d` | `fix`: JWT_SECRET을 SSM에서 주입 (평문 제거) |
| `715e420` | `fix`: USE_MOCK env 기반 + CodeBuild ECS 권한 |
| `8f257c4` | `fix(ci)`: buildspec에서 taskdef.json으로 register |
| `1a4487d` | `fix(ecs)`: execution/task Role ARN 실 IaC Role로 정정 |

---

## 5. 시연 진행 시점 핵심 결정

1. **DynamoDB도 더미 데이터** — 온프레미스 연동 없이 시뮬레이션 적재. mock 모드 == DynamoDB 모드 본질적으로 동일.
2. **운영 전환 시 ETL 파이프라인 구축이 핵심** — 온프레 customer_360_profile → ETL/Glue → GCP Vertex AI 분석 → S3 → gcp_result_ingest Lambda → DynamoDB
3. **JWT_SECRET을 Parameter Store에서 주입** (SecretsManager에 lifesync/jwt 시크릿 없음)
4. **인증 Mock 강제는 임시 우회** — Lambda 배포 후 원복 (`docs/lambda-onprem-query-deploy.md` STEP 1~9)

---

## 6. 남은 작업 (우선순위)

### 즉시 (시연 진행용)
- [ ] ECS Task Execution Role에 SSM 권한 추가 → 새 task 부팅 정상화
- [ ] ECS Task Role에 DynamoDB 권한 추가 → 점수/등급 조회 정상화

### 단기 (시연 완수 후)
- [ ] Lambda 배포 (`docs/lambda-onprem-query-deploy.md`)
- [ ] 온프레 private_api 재배포 (Ansible)
- [ ] 인증 Mock 강제 코드 원복

### 중기 (운영 전환)
- [ ] IaC 측 ECS Task Definition 정합 (`docs/iac-ecs-taskdef-spec.md`)
- [ ] gcp_result_ingest Lambda 운영
- [ ] ETL/Glue/Vertex AI 파이프라인 구축

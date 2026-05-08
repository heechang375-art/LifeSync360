================================================================
  LifeSync360 — IaC 담당자 전달 패키지
  작성일: 2026-05-07
  목적: Aurora 스키마 / 상품 카탈로그 / DynamoDB / 데이터 적재 프로세스
================================================================

이 패키지는 LifeSync360 플랫폼의 데이터 인프라 구성에 필요한 파일을
카테고리별로 정리한 것입니다. IaC 스택 구성 및 초기 데이터 적재 시
아래 설명을 참고하여 순서에 맞게 실행하세요.

================================================================
  1. AURORA 스키마
================================================================

[db/aurora_schema.sql]
  - 용도: LifeSync360 플랫폼 Aurora MySQL 8.0 메인 스키마 DDL
  - 대상 DB: AWS Aurora MySQL (Cloud)
  - 포함 테이블:
      · users              — LifeSync 가입자 (ls_user_id, global_id, grade 등)
      · consent            — 계열사별 데이터 활용 동의 (Y/N)
      · company_master     — 계열사 코드 및 명칭 (bank, card, insurance 등)
      · category_master    — 상품 카테고리 (계열사별 하위 분류)
      · product_master     — 상품 카탈로그 (product_id, 이름, 설명, 태그, 등급 조건)
      · product_option     — 상품 상세 옵션 (금리, 한도, 조건 등 key-value)
      · recommend_rule     — 추천 룰 (등급/나이/건강점수 조건 기반)
  - 실행 순서: 1번 (가장 먼저 실행)
  - 주의: Aurora 클러스터 생성 완료 후 실행. charset=utf8mb4 확인.

[db/onprem_schema.sql]
  - 용도: On-Prem MySQL 스키마 DDL (ls-db VM에 적용)
  - 대상 DB: On-Prem ls-db 서버 (onprem-prod-repo 배포 대상)
  - 포함 테이블:
      · master_customer        — 고객 기본정보 (global_id, 이름, 생년월일, 성별, 국적)
      · customer_identity_map  — global_id ↔ 계열사 ID 매핑 (bank: BNK-XXXXXXXX 등)
      · customer_pii_secure    — 민감 개인정보 (암호화 저장, 접근 제한)
      · matching_audit_log     — global_id 매핑 이력 감사 로그
  - 실행 순서: 1번 (aurora_schema.sql과 독립적으로 별도 실행)
  - 주의: Ansible roles/mysql 통해 배포됨. 직접 실행 시 On-Prem DB 접속 필요.

[onprem-prod-repo/ansible/roles/mysql/files/schema.sql]
  - 용도: Ansible 배포 경로의 On-Prem 스키마 파일 (onprem_schema.sql과 동일 내용)
  - 대상: Ansible roles/mysql 태스크가 ls-db VM에 자동 적용
  - 비고: Ansible 배포 시 이 파일이 실제로 사용됨. onprem_schema.sql은 참조용.

================================================================
  2. 상품 카탈로그
================================================================

[data/product_catalog_seed.json]
  - 용도: Aurora 상품 카탈로그 전체 Seed 데이터 (148개 상품)
  - 연관 테이블: company_master, category_master, product_master, product_option, recommend_rule
  - 구조: { "companies": [...], "categories": [...], "products": [...], "recommend_rules": [...] }
  - 적재 방법: scripts/seed_products.py 실행 (아래 4번 참조)
  - 주의: product_master INSERT 전 company_master, category_master 먼저 적재.

[data/products/bank.json]
  - 용도: LS 은행 상품 원본 데이터 (35개 — 예금, 적금, 대출)
  - 주요 필드: product_name, 기준금리(연), 최고금리(연), 우대금리조건, AI 추천 조건
  - 적재 대상: product_master + product_option
  - category: deposit_product, savings_product, loan_product

[data/products/card.json]
  - 용도: LS 카드 상품 원본 데이터 (20개 — 신용/체크카드)
  - 주요 필드: product_name, 연회비(원), 기본적립률(%), 포인트 적립 조건
  - category: card_product

[data/products/insurance.json]
  - 용도: LS 보험 상품 원본 데이터 (30개 — 건강/실손/생명보험)
  - 주요 필드: product_name, 월 보험료(평균), 대상고객, 주요 보장 내용, 카버리지
  - category: insurance_product

[data/products/internet_insurance.json]
  - 용도: LS 온라인보험 상품 원본 데이터 (29개 — 다이렉트 상품)
  - 주요 필드: product_name, 월 보험료(평균), 대상고객, 가입기간
  - category: internet_insurance_product

[data/products/securities.json]
  - 용도: LS 증권 포트폴리오 상품 원본 데이터 (19개)
  - 주요 필드: product_name, 투자성향, 연수익률(평균/목표), 주요 ETF 구성
  - category: portfolio_product

[data/products/healthcare.json]
  - 용도: LS 헬스케어 운동 추천 및 관리 서비스 데이터 (15개)
  - 주요 필드: product_name, 운동유형, 활동강도(분/칼로리), 추천 시 조건
  - category: exercise_recommendation, health_checkup

[data/products/hospital.json]
  - 용도: LS 병원 건강검진 패키지 데이터
  - 주요 필드: product_name, 항목수, 패키지트리거, 권장타겟그룹, 가격트랙
  - category: health_checkup

================================================================
  3. DYNAMODB
================================================================

[infra/data/dynamodb.yaml]
  - 용도: CloudFormation 템플릿 — DynamoDB 테이블 프로비저닝
  - 테이블명: lifesync-scores
  - 파티션 키: global_id (String)
  - 빌링: On-Demand (PAY_PER_REQUEST)
  - 기타: PITR(특정시점복구) 활성화, TTL 속성 설정
  - 실행 순서: IaC 스택 배포 시 infra/data/ 스택에 포함
  - 연관: infra/data/aurora.yaml과 같은 스택 또는 별도 스택으로 배포 가능

[scripts/create_dynamodb.py]
  - 용도: DynamoDB 테이블 직접 생성 스크립트 (CloudFormation 미사용 시 대안)
  - 실행 환경: Python 3.x + boto3, AWS CLI 설정 완료
  - 생성 테이블: lifesync-scores (ap-northeast-2)
  - 실행 방법: python scripts/create_dynamodb.py
  - 주의: CloudFormation으로 관리하는 경우 이 스크립트는 사용 불필요.
          중복 실행 시 ResourceInUseException 발생 (이미 존재하는 경우 무시).

[scripts/seed_dynamodb.py]
  - 용도: DynamoDB 초기 더미 데이터 적재 (개발/테스트용)
  - 적재 항목: 4개 고객 레코드 (G000000001~G000000004)
      · dynamic_score, health_score, fin_score, behavior_score
      · loyalty_grade, next_best_action
      · vip_probability
      · TTL: 적재 시점 기준 30일 후 자동 만료
  - 실행 방법: python scripts/seed_dynamodb.py
  - 주의: 프로덕션에는 Lambda(gcp_result_ingest)가 실시간 적재. 이 스크립트는 초기 테스트 전용.

================================================================
  4. 데이터 적재 프로세스
================================================================

[lambda/gcp_result_ingest/handler.py]
  - 용도: GCP Vertex AI 분석 결과 수신 및 AWS 각 스토리지 적재 Lambda 함수
  - 트리거: API Gateway POST /ingest
  - 처리 흐름:
      1. GCP Pub/Sub → API Gateway → 이 Lambda 호출
      2. DynamoDB PUT — global_id 기준 스코어 실시간 저장
         (dynamic_score, health_score, fin_score, behavior_score, loyalty_grade)
      3. Aurora UPDATE — users 테이블 grade 갱신 (등급 변경 시)
      4. Redis SET — 추천 product_id 리스트 캐싱 (TTL 24h)
  - 환경변수: AURORA_SECRET_ARN, REDIS_HOST, DYNAMO_TABLE (Secrets Manager 연동)
  - 배포: lambda/gcp_result_ingest/build.sh 실행 후 S3 업로드 → CloudFormation 배포
  - 연관 IaC: infra/compute/lambda.yaml, infra/compute/api-gateway.yaml

[lambda/customer_profile_sync/handler.py]
  - 용도: LifeSync 신규 로그인 시 On-Prem에서 global_id 조회 및 Aurora 동기화 Lambda
  - 트리거: ECS platform 서비스(app.py)에서 직접 invoke (로그인 시 global_id 미설정 유저)
  - 처리 흐름:
      1. ls_user_id + email 수신
      2. On-Prem Private API(/internal/identity) 호출 → global_id 조회
      3. Aurora users.global_id 업데이트
  - 환경변수: ONPREM_API_URL, ONPREM_API_TOKEN (Secrets Manager 연동)
  - 배포: lambda/customer_profile_sync/build.sh 실행 후 S3 → CloudFormation

[scripts/seed_products.py]
  - 용도: data/products/*.json → Aurora product_master / product_option 테이블 적재
  - 실행 환경: Python 3.x + pymysql, Aurora 직접 접속 필요 (또는 Bastion 경유)
  - 실행 방법: python scripts/seed_products.py [--company bank|card|insurance|...]
              옵션 없이 실행 시 전체 계열사 상품 일괄 적재
  - 실행 순서: aurora_schema.sql 실행 후, product_catalog_seed.json 적재 전 또는 후
  - 주의: 중복 실행 방지 로직 포함 (INSERT IGNORE 또는 ON DUPLICATE KEY UPDATE).

[scripts/lifesync360_pre_customer_data.py]
  - 용도: STEP 1 — 100만명 고객 기본 프로파일 생성 및 적재용 CSV 출력
  - 입력: 없음 (시드(SEED=42) 기반 난수 생성)
  - 출력 (data/output/):
      · customer_profile.csv       — 100만행 39컬럼 (전체 고객 프로파일)
      · customer_master.csv        — On-Prem master_customer 적재용
      · customer_identity_map.csv  — On-Prem customer_identity_map 적재용 (계열사 ID 매핑)
      · aurora_users.csv           — Aurora users 테이블 적재용 (LifeSync 가입자 30만명)
  - 분포 기준 (아키텍처 PPTX 동일):
      · 연령: 20대 15% / 30대 25% / 40대 30% / 50대 20% / 60대+ 10%
      · 계열사 가입율: 은행 100% / 카드 70% / 보험 50% / 온라인보험 25%
                       병원 20% / 헬스케어 30% / 증권 25% / 웨어러블 30%
      · LifeSync 가입자: 30% (300,000명)
  - 실행 방법: python scripts/lifesync360_pre_customer_data.py
  - 소요 시간: 약 2~3분

[scripts/lifesync360_bq_features.py]
  - 용도: STEP 2 — Glue + EMR 처리 시뮬레이션 → BigQuery / Vertex AI 피처 생성
  - 입력: data/output/customer_profile.csv, data/output/aurora_users.csv
  - 출력 (data/output/):
      · bq_curated_unified.csv    — BigQuery 큐레이션 뷰 (1M행 36컬럼)
      · vertex_feature_table.csv  — Vertex AI 피처 테이블 (entity_id=global_id 기준)
  - LifeSync Score 계산식 (PPTX 기준):
      건강 35% + 금융 35% + 소비 15% + 충성도 15%
  - 건강점수 세부 (심혈관 35pt + 활동 35pt + 신체지표 20pt + 임상 10pt = 100pt)
  - 실행 순서: lifesync360_pre_customer_data.py 완료 후 실행
  - 소요 시간: 약 3~5분

[scripts/dq_check.py]
  - 용도: Glue Data Quality 룰 시뮬레이션 — 생성된 CSV 4종 검증
  - 검증 대상: customer_profile.csv / customer_master.csv / customer_identity_map.csv / aurora_users.csv
  - 검증 항목 (총 21개):
      · 행 수 일치 여부 (profile/master: 100만, aurora: 30만)
      · 필수 필드 NULL 체크
      · global_id 중복 / 포맷 검증 (G{9자리})
      · ls_user_id 포맷 (LS-{8HEX}-{6자리})
      · 계열사 ID 포맷 (BNK-/CRD-/INS- 등 8자리)
      · 나이 범위 (20~79세), 성별 값, grade 값
      · orphan global_id (참조 무결성)
      · LS 가입 비율 (~30%)
  - 실행 방법: python scripts/dq_check.py
  - 기대 결과: PASS 21 / FAIL 0

================================================================
  5. 권장 실행 순서
================================================================

  [ On-Prem ]
  1. onprem-prod-repo/ansible/roles/mysql/files/schema.sql
     → Ansible 배포로 ls-db VM에 자동 적용

  [ AWS IaC 스택 배포 순서 ]
  2. infra/network/ 스택 (VPC, Subnet, IGW, NAT, RouteTable)
  3. infra/sg.yaml (Security Group)
  4. infra/iam.yaml (IAM Role)
  5. infra/data/secrets-manager.yaml (Secrets Manager)
  6. infra/data/aurora.yaml (Aurora 클러스터)
  7. infra/data/dynamodb.yaml (DynamoDB 테이블)
  8. infra/data/elasticache.yaml (Redis)
  9. infra/data/s3.yaml (S3 버킷)
  10. infra/compute/ 스택 (ECR, ECS, Lambda, ALB, API GW 등)
  11. infra/pipeline/ 스택 (CodeCommit, CodeBuild, CodePipeline)

  [ 초기 데이터 적재 순서 ]
  12. db/aurora_schema.sql → Aurora 실행
  13. scripts/seed_products.py → 상품 카탈로그 Aurora 적재
  14. scripts/lifesync360_pre_customer_data.py → 고객 데이터 CSV 생성
  15. scripts/dq_check.py → 생성 데이터 품질 검증
  16. scripts/lifesync360_bq_features.py → BQ/Vertex AI 피처 생성
  17. scripts/seed_dynamodb.py → DynamoDB 초기 테스트 데이터 적재 (개발 환경 전용)

================================================================
  6. 파일 목록 요약
================================================================

  [Aurora 스키마 — 3개]
  db/aurora_schema.sql
  db/onprem_schema.sql
  onprem-prod-repo/ansible/roles/mysql/files/schema.sql

  [상품 카탈로그 — 8개]
  data/product_catalog_seed.json
  data/products/bank.json
  data/products/card.json
  data/products/insurance.json
  data/products/internet_insurance.json
  data/products/securities.json
  data/products/healthcare.json
  data/products/hospital.json

  [DynamoDB — 3개]
  infra/data/dynamodb.yaml
  scripts/create_dynamodb.py
  scripts/seed_dynamodb.py

  [데이터 적재 프로세스 — 7개]
  lambda/gcp_result_ingest/handler.py
  lambda/customer_profile_sync/handler.py
  scripts/seed_products.py
  scripts/lifesync360_pre_customer_data.py
  scripts/lifesync360_bq_features.py
  scripts/dq_check.py
  infra/data/aurora.yaml

  총 21개 파일 + README_파일설명.txt (이 파일)

================================================================
  문의: LifeSync360 개발팀
  최종 업데이트: 2026-05-07
================================================================

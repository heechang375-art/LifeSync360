# 2026-05-14 자율 진행 결과 (사용자 부재 동안)

## 1. 진행한 작업

### A. 세션 요약 문서 작성
- `docs/session-2026-05-14-summary.md` 신규
- 오늘 작업 흐름 (시간순) + 푸시된 커밋 14개 + 작성한 문서 + 미해결 사항 정리

### B. UI 추가 데이터 분석 + mock_data 풍부화

`schema_reference.md` + `service_db_reference.md` + `files.zip 변경내역.txt` 조합 분석 결과:

**기존 화면이 활용 안 한 데이터**:
- DynamoDB: `vip_prob`, `signup_prob`, `rec_prob`, `next_best_action`
- onprem `customer_360_profile`: gender, age_band, region, income_grade, asset_grade, wearable_flag, risk_score, finance_score, asset_score, lifesync_score
- onprem `master_customer`: customer_status, vip_grade, customer_type, first_created_dt
- Aurora `campaign_master`: 등급별 활성 캠페인 배너
- Aurora `base_product_pool.base_description`: 풍부한 상품 설명 (files.zip 변경 반영)

**구현된 풍부화**:

#### `lifesync360-platform/mock_data.py`
- `MOCK_USERS` 3명에 다음 필드 추가:
  - 인구통계: `gender`, `age_band`, `region`, `income_grade`, `asset_grade`, `wearable_flag`
  - 마스터: `customer_status`, `vip_grade`, `customer_type`, `first_created_dt`, `last_login_dt`
  - ML 확률: `vip_prob`, `signup_prob`, `rec_prob`
  - NBA: `next_best_action`
- `_HEALTH_BY_USER` 3명에 다음 점수 추가:
  - `risk_score`, `finance_score`, `asset_score`, `lifesync_score` (customer_360_profile)
  - `vip_prob`, `signup_prob`, `rec_prob`, `next_best_action` (DynamoDB)
- `MOCK_CAMPAIGNS_BY_GRADE` 신규: 5개 등급(VIP/GOLD/SILVER/BASIC/CARE) × 각 3개 캠페인 (icon/title/desc/period/cta)
- `get_mock_campaigns(grade)` 헬퍼 함수

#### `lifesync360-platform/app.py`
- `from mock_data import` 에 `get_mock_campaigns` 추가
- `/api/me` Mock 분기 응답에 인구통계 + 마스터 필드 추가 (11개 필드)
- `/api/campaigns` 신규 엔드포인트
  - Mock 모드: `get_mock_campaigns(grade)` 반환
  - Cloud 모드: DynamoDB grade 조회 → Aurora `campaign_master`에서 active 캠페인 SELECT

#### `lifesync360-platform/templates/index.html` (홈 화면)
- **Next Best Action 카드** 신규 영역 (그라데이션 보라색)
  - `scores.next_best_action` 표시
  - vip_prob / signup_prob / rec_prob 백분율로 칩 형태 표시
- **등급 맞춤 캠페인 배너** 신규 영역 (가로 스크롤)
  - `/api/campaigns` 응답 카드 3개 표시 (등급별 다른 색상)
- JS: 새 fetch `/api/campaigns` 추가, 응답 처리 + 빈 응답 시 영역 숨김

#### `lifesync360-platform/templates/settings.html` (계정 정보 화면)
- 계정 정보 카드: 이름/이메일 외에 **가입일 + 최근 로그인** 추가
- 신규 카드 "분석 프로파일":
  - 연령대 (age_band) → 20대/30대/... 한글화
  - 지역 (region) → SEOUL/GYEONGGI → 서울/경기 한글화
  - 소득 등급 (income_grade) → LOW/MID/HIGH → 낮음/중간/높음
  - 자산 등급 (asset_grade) → 동일 한글화
  - 웨어러블 연동 (wearable_flag) → Y/N → "연동됨"/"미연동"
- JS: `/api/me` 응답에서 새 필드 읽어 채움

### C. 시연 시 보이는 추가 UI 요소 (mock 모드)

| 화면 영역 | 데이터 출처 | 비고 |
|---|---|---|
| 홈 NBA 카드 | `_HEALTH_BY_USER[uid].next_best_action` | 그라데이션 + 확률 칩 |
| 홈 NBA 확률 칩 | `vip_prob/signup_prob/rec_prob` | 백분율 표시 |
| 홈 캠페인 배너 (3개) | `MOCK_CAMPAIGNS_BY_GRADE[grade]` | 등급별 다른 캠페인 |
| settings 가입일/최근로그인 | `MOCK_USERS[email].first_created_dt/last_login_dt` | |
| settings 분석 프로파일 5종 | `MOCK_USERS[email].{gender/age_band/region/income/asset/wearable}` | 한글화 매핑 |

### D. 시연 동작 확인 매트릭스

| 계정 | grade | 보이는 NBA | 보이는 캠페인 |
|---|---|---|---|
| test@lifesync.com (김철수) | VIP | "프리미엄 건강검진 예약하기" + 확률 85/72/91% | VIP 자산관리 / 라이프케어 / 상속·절세 |
| test2@lifesync.com (이수진) | GOLD | "ETF 적립식 투자 시작" + 58/66/79% | 글로벌 투자 / 카드 혜택 / 건강보장 |
| test3@lifesync.com (박지훈) | SILVER | "실손 의료보험 가입 검토" + 32/51/64% | 생활금융 / 건강보장 시작 / 목적자금 |

### E. 미진행 (의도적)

- **admin-platform 풍부화** — 사용자가 "admin 뒤로 미뤄" 명시했음
- **점수 토글 5개로 확장** — `index.html` 종합/건강 2개 그대로. raw 점수 5종 표시는 후속 작업 (시각 부담)
- **상품 상세 페이지 풍부한 description** — `PRODUCTS_MAP`/`MOCK_RECOMMENDATIONS`에 이미 detail/desc 있어서 변경 없음. 운영 모드 추후 base_description 매핑

---

## 2. 변경 파일 목록

```
docs/session-2026-05-14-summary.md     (신규)
docs/session-2026-05-14-progress.md    (신규, 본 파일)
lifesync360-platform/mock_data.py
lifesync360-platform/app.py
lifesync360-platform/templates/index.html
lifesync360-platform/templates/settings.html
```

---

## 3. 푸시 결과

(다음 메시지에서 push 진행 후 commit hash 기록)

---

## 4. 시연 시 권장 흐름

1. ECS Service에서 `revision 24` (USE_MOCK=true mock 모드)로 force-deploy 유지 — 가장 안정적
2. 브라우저에서 ALB URL 접속 → `localStorage.clear(); location.reload();` 옛 토큰 제거
3. `test@lifesync.com / password123` (VIP) 로그인
4. 홈 화면 확인:
   - 헤더 등급 뱃지 `VIP`
   - 종합점수 게이지 `92.4`, 건강 `88`
   - 🎯 **AI 추천 다음 액션: 프리미엄 건강검진 예약하기** (확률 칩 3개)
   - 📜 **맞춤 캠페인 3개** (VIP 자산관리 / 라이프케어 / 상속·절세)
   - 나를 위한 추천 (mock 데이터)
5. settings 진입:
   - 계정 정보: 이름/이메일/가입일/최근 로그인
   - **분석 프로파일: 40대 / 서울 / 소득 높음 / 자산 높음 / 웨어러블 연동됨**
   - 등급 혜택, 데이터 활용 동의
6. 다른 계정으로 재로그인 → 캠페인/NBA가 등급별로 변하는 모습 시연

---

## 5. 이번 자율 진행 외 미해결 (사용자 복귀 시 결정 필요)

- [ ] ECS Task Execution Role에 SSM `ssm:GetParameters` 권한 추가 (직전 buildspec 흐름 정상화 위해)
- [ ] ECS Task Role에 DynamoDB `GetItem/Scan/Query` 권한 추가
- [ ] 새 push 후 CodePipeline이 어떤 revision으로 force-deploy 되는지 확인
- [ ] mock 모드 (revision 24) 유지하면서 시연만 진행할지, Cloud 모드 정합 마저 진행할지 결정

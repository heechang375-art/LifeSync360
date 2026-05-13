# Glue / EMR 동의 고객 필터 연동 스펙

> 작성일: 2026-05-13  
> 대상: Glue / EMR 담당자

---

## 개요

Glue / EMR 잡이 실행되기 전, **동의 고객 필터링 Lambda**(`consent_filter`)가 먼저 실행되어  
온프레미스 MySQL의 `consent` 테이블에서 `consent_yn = 'Y'` 고객을 추출하고 S3에 저장합니다.

Glue / EMR 잡은 이 파일을 입력으로 받아 **동의한 고객의 데이터만** 처리해야 합니다.

---

## 실행 흐름

```
EventBridge Scheduler
        ↓
consent_filter Lambda
  ├─ On-Prem MySQL(lifesync_onprem) consent 테이블 조회
  └─ S3 gzip CSV 저장
        ↓
S3: s3://<버킷>/consent-filter/YYYYMMDD/consented_customers.csv.gz
        ↓
Glue Job  (--consent_s3_path 인자로 S3 경로 수신)
EMR Step  (--consent_s3_path 인자로 S3 경로 수신)
```

Lambda가 Glue / EMR을 직접 트리거할 수도 있고 (Lambda가 `start_job_run` / `add_job_flow_steps` 호출),  
EventBridge Step Functions로 순서를 제어할 수도 있습니다.  
어느 방식이든 잡 실행 시점에는 **반드시 S3 파일이 존재한 후** 잡이 시작되어야 합니다.

---

## S3 파일 스펙

| 항목 | 값 |
|------|-----|
| 경로 패턴 | `s3://<버킷명>/consent-filter/{YYYYMMDD}/consented_customers.csv.gz` |
| 포맷 | gzip 압축 CSV |
| 인코딩 | UTF-8 |
| 헤더 | 있음 (첫 번째 행) |
| 생성 시점 | 매 실행일 UTC 기준 (Lambda 실행 시각) |

---

## 컬럼 구조

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `global_id` | String | 고객 통합 식별자 |
| `BANK` | String (`"0"` / `"1"`) | LS 은행 데이터 활용 동의 여부 |
| `CARD` | String (`"0"` / `"1"`) | LS 카드 데이터 활용 동의 여부 |
| `INS` | String (`"0"` / `"1"`) | LS 보험 데이터 활용 동의 여부 |
| `ONINS` | String (`"0"` / `"1"`) | LS 온라인보험 데이터 활용 동의 여부 |
| `SEC` | String (`"0"` / `"1"`) | LS 증권 데이터 활용 동의 여부 |
| `HLT` | String (`"0"` / `"1"`) | LS 헬스케어 데이터 활용 동의 여부 |
| `wearable` | String (`"0"` / `"1"`) | 웨어러블 데이터 활용 동의 여부 |

**예시 데이터:**

```
global_id,BANK,CARD,INS,ONINS,SEC,HLT,wearable
G-ABC123DEFG56,1,1,0,0,1,0,1
G-DEF456GHIJ78,1,0,0,0,0,0,0
G-GHI789KLMN90,0,0,1,1,0,1,0
```

- `G-ABC123DEFG56`: 은행·카드·증권·웨어러블 동의, 보험·온라인보험·헬스케어 미동의
- `G-DEF456GHIJ78`: 은행만 동의
- `G-GHI789KLMN90`: 보험·온라인보험·헬스케어 동의

> 파일에는 **최소 1개 계열사 이상 동의한 고객만** 포함됩니다.  
> 전체 미동의 고객은 행 자체가 없습니다.

---

## Glue Job 연동 (PySpark)

### 잡 인자 수신

Lambda가 Glue Job을 트리거할 때 아래 인자를 자동으로 전달합니다.

| 인자명 | 예시 값 |
|--------|---------|
| `--consent_s3_path` | `s3://lifesync-data/consent-filter/20260513/consented_customers.csv.gz` |
| `--job_date` | `20260513` |

추가 인자가 필요하면 Lambda 이벤트의 `glue_extra_args` 파라미터로 전달 가능합니다.

### 코드 예시

```python
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'consent_s3_path', 'job_date'])
gc   = GlueContext(SparkContext.getOrCreate())
spark = gc.spark_session

# 동의 고객 목록 로드
consent_df = spark.read.option('header', 'true').csv(args['consent_s3_path'])

# ── 계열사별 필터링 예시 ────────────────────────────────────────────────────

# 은행 데이터 잡 — BANK 동의 고객만
bank_global_ids = consent_df.filter(consent_df['BANK'] == '1').select('global_id')

# 헬스케어 데이터 잡 — HLT 동의 고객만
hlt_global_ids = consent_df.filter(consent_df['HLT'] == '1').select('global_id')

# 복수 계열사 동의 고객 (BANK AND CARD 모두 동의)
bank_card_ids = consent_df.filter(
    (consent_df['BANK'] == '1') & (consent_df['CARD'] == '1')
).select('global_id')

# ── 실제 데이터와 JOIN ──────────────────────────────────────────────────────

# 예: 은행 거래 데이터와 JOIN → 동의 고객 거래 내역만 처리
bank_transactions = spark.read.parquet('s3://lifesync-raw/bank/transactions/')
filtered = bank_transactions.join(bank_global_ids, on='global_id', how='inner')
```

---

## EMR Step 연동 (Spark)

Lambda가 EMR Step을 추가할 때 `--consent_s3_path` 인자가 Step args 끝에 자동으로 붙습니다.

### Lambda 이벤트 파라미터 예시

```json
{
  "emr_cluster_id": "j-XXXXXXXXXX",
  "emr_step_name":  "LifeSync360 고객 분석",
  "emr_step_args": [
    "spark-submit",
    "--deploy-mode", "cluster",
    "--class", "com.lifesync.CustomerAnalysis",
    "s3://lifesync-scripts/analysis.jar",
    "--input", "s3://lifesync-raw/",
    "--output", "s3://lifesync-processed/"
  ]
}
```

Lambda가 위 args 뒤에 `--consent_s3_path <S3경로>`를 자동으로 추가합니다.

### EMR Spark Job에서 인자 수신 예시

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--consent_s3_path', required=True)
parser.add_argument('--input',           required=True)
parser.add_argument('--output',          required=True)
args = parser.parse_args()

consent_df = spark.read.option('header', 'true').csv(args.consent_s3_path)
hlt_ids    = consent_df.filter(consent_df['HLT'] == '1').select('global_id')
```

---

## 계열사별 필터 컬럼 대응표

| 계열사 | 필터 컬럼 |
|--------|----------|
| LS 은행 | `BANK == '1'` |
| LS 카드 | `CARD == '1'` |
| LS 보험 | `INS == '1'` |
| LS 온라인보험 | `ONINS == '1'` |
| LS 증권 | `SEC == '1'` |
| LS 헬스케어 | `HLT == '1'` |
| 웨어러블 | `wearable == '1'` |

---

## 장애 대응

### S3 파일이 없을 때

Lambda 실패 또는 미실행 상태입니다. 잡을 시작하지 마세요.

```python
import boto3

s3  = boto3.client('s3')
key = f"consent-filter/{job_date}/consented_customers.csv.gz"

try:
    s3.head_object(Bucket='<버킷명>', Key=key)
except s3.exceptions.ClientError:
    raise RuntimeError(f"동의 고객 파일 없음: s3://<버킷명>/{key} — Lambda 실행 여부 확인 필요")
```

### 동의 고객 수가 0일 때

Lambda가 0명을 추출하면 S3 업로드 자체를 건너뛰므로 파일이 존재하지 않습니다.  
Lambda CloudWatch 로그에서 `"동의 고객이 0명"` 메시지 확인 후 온프레미스 DB 상태를 점검하세요.

### 특정 계열사 동의 고객이 예상보다 적을 때

온프레미스 MySQL `lifesync_onprem.consent` 테이블 직접 확인:

```sql
SELECT consent_key, COUNT(*) AS cnt
FROM consent
WHERE consent_yn = 'Y'
GROUP BY consent_key
ORDER BY cnt DESC;
```

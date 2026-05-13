import boto3
import json
import os
import subprocess
import pymysql
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI()

DEPLOY_TOKEN = os.environ['DEPLOY_TOKEN']
REGION = 'ap-northeast-2'
SECRET_ID = 'lifesync/onprem-db'
DB_NAME = 'lifesync_onprem'


def get_pii_key():
    key = os.environ.get('PII_AES_KEY')
    if not key:
        secret = boto3.client('secretsmanager', region_name=REGION).get_secret_value(SecretId=SECRET_ID)
        key = json.loads(secret['SecretString'])['pii_aes_key']
    return Fernet(key.encode())

def decrypt_pii(val):
    if not val:
        return None
    return get_pii_key().decrypt(val.encode()).decode('utf-8')


def get_db():
    return pymysql.connect(
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/internal/customer/{global_customer_id}')
def get_customer(global_customer_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT * FROM master_customer WHERE global_customer_id = %s', (global_customer_id,)
            )
            customer = cur.fetchone()
            if not customer:
                raise HTTPException(status_code=404, detail='Customer not found')

            cur.execute(
                'SELECT domain, source_customer_id, created_dt FROM customer_identity_map WHERE global_customer_id = %s',
                (global_customer_id,)
            )
            customer['identities'] = cur.fetchall()

            cur.execute(
                'SELECT lifesync_score, health_score, finance_score, asset_score, last_calc_dt FROM customer_360_profile WHERE global_customer_id = %s',
                (global_customer_id,)
            )
            customer['profile'] = cur.fetchone()
    finally:
        db.close()
    return customer


@app.get('/internal/consent/{global_customer_id}')
def get_consent(global_customer_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT domain, consent_flag, consent_version, revoke_dt, created_dt FROM consent WHERE global_customer_id = %s',
                (global_customer_id,)
            )
            rows = cur.fetchall()
    finally:
        db.close()
    return {'global_customer_id': global_customer_id, 'consents': rows}


@app.get('/internal/identity/{source_customer_id}')
def get_identity(source_customer_id: str, domain: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT global_customer_id FROM customer_identity_map WHERE source_customer_id = %s AND domain = %s',
                (source_customer_id, domain)
            )
            row = cur.fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404, detail='Identity mapping not found')
    return row


@app.post('/internal/deploy')
async def trigger_deploy(request: Request):
    if request.headers.get('X-Deploy-Token', '') != DEPLOY_TOKEN:
        raise HTTPException(status_code=401, detail='배포 토큰 불일치')
    subprocess.Popen(['/opt/private-api/trigger_ansible.sh'])
    return {'status': 'triggered'}


class MatchRequest(BaseModel):
    domain: str
    source_customer_id: str
    global_customer_id: str


@app.post('/internal/match')
def match_identity(req: MatchRequest):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                '''INSERT INTO customer_identity_map (global_customer_id, domain, source_customer_id)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE source_customer_id = VALUES(source_customer_id)''',
                (req.global_customer_id, req.domain, req.source_customer_id)
            )
            cur.execute(
                '''INSERT INTO matching_audit_log (request_id, ls_user_id, match_rule, result, matched_global_customer_id)
                   VALUES (%s, %s, %s, %s, %s)''',
                (
                    str(__import__('uuid').uuid4()),
                    req.source_customer_id,
                    req.domain,
                    'MATCH',
                    req.global_customer_id,
                )
            )
            db.commit()
    finally:
        db.close()
    return {'status': 'ok', 'global_customer_id': req.global_customer_id}

import boto3
import json
import pymysql
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

REGION = 'ap-northeast-2'
SECRET_ID = 'lifesync/onprem-db'
DB_NAME = 'lifesync_onprem'


def get_db():
    secret = boto3.client('secretsmanager', region_name=REGION).get_secret_value(SecretId=SECRET_ID)
    creds = json.loads(secret['SecretString'])
    return pymysql.connect(
        host=creds['host'],
        user=creds['username'],
        password=creds['password'],
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/internal/customer/{global_id}')
def get_customer(global_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT * FROM master_customer WHERE global_id = %s', (global_id,)
            )
            customer = cur.fetchone()
            if not customer:
                raise HTTPException(status_code=404, detail='Customer not found')

            cur.execute(
                'SELECT company_id, affiliate_customer_id, linked_at FROM customer_identity_map WHERE global_id = %s',
                (global_id,)
            )
            customer['identities'] = cur.fetchall()

            cur.execute(
                'SELECT grade, lifesync_score, updated_at FROM customer_360_profile WHERE global_id = %s',
                (global_id,)
            )
            customer['profile'] = cur.fetchone()
    finally:
        db.close()
    return customer


@app.get('/internal/consent/{global_id}')
def get_consent(global_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT consent_key, consent_yn, updated_at FROM consent WHERE global_id = %s',
                (global_id,)
            )
            rows = cur.fetchall()
    finally:
        db.close()
    return {'global_id': global_id, 'consents': rows}


@app.get('/internal/identity/{affiliate_customer_id}')
def get_identity(affiliate_customer_id: str, company_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT global_id FROM customer_identity_map WHERE affiliate_customer_id = %s AND company_id = %s',
                (affiliate_customer_id, company_id)
            )
            row = cur.fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404, detail='Identity mapping not found')
    return row


class MatchRequest(BaseModel):
    company_id: str
    affiliate_customer_id: str
    global_id: str


@app.post('/internal/match')
def match_identity(req: MatchRequest):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                '''INSERT INTO customer_identity_map (global_id, company_id, affiliate_customer_id)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE affiliate_customer_id = VALUES(affiliate_customer_id)''',
                (req.global_id, req.company_id, req.affiliate_customer_id)
            )
            cur.execute(
                '''INSERT INTO matching_audit_log (global_id, action_type, action_detail)
                   VALUES (%s, 'MATCH', %s)''',
                (req.global_id, json.dumps({'company_id': req.company_id, 'affiliate_customer_id': req.affiliate_customer_id}))
            )
            db.commit()
    finally:
        db.close()
    return {'status': 'ok', 'global_id': req.global_id}

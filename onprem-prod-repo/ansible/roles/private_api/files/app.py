import base64
import hashlib
import boto3
import json
import os
import subprocess
import pymysql
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

DEPLOY_TOKEN = os.environ['DEPLOY_TOKEN']
REGION = 'ap-northeast-2'
SECRET_ID = 'lifesync/onprem-db'
DB_NAME = 'lifesync_onprem'

_aesgcm = None

def get_aesgcm():
    global _aesgcm
    if _aesgcm is None:
        key_b64 = os.environ.get('TOKEN_AES_KEY_B64')
        if not key_b64:
            secret  = boto3.client('secretsmanager', region_name=REGION).get_secret_value(SecretId=SECRET_ID)
            key_b64 = json.loads(secret['SecretString'])['token_aes_key_b64']
        _aesgcm = AESGCM(base64.b64decode(key_b64))
    return _aesgcm

def encrypt_pii(value):
    if value is None or value == '':
        return None
    iv = os.urandom(12)
    ct = get_aesgcm().encrypt(iv, value.encode('utf-8'), None)
    return base64.b64encode(iv + ct).decode('ascii')

def decrypt_pii(enc_b64):
    if not enc_b64:
        return None
    raw = base64.b64decode(enc_b64)
    return get_aesgcm().decrypt(raw[:12], raw[12:], None).decode('utf-8')

def pii_token_of(global_id):
    return 'PII-' + hashlib.sha256(global_id.encode('utf-8')).hexdigest().upper()[:16]

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


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
                'SELECT domain, source_customer_id, created_dt FROM customer_identity_map WHERE global_id = %s',
                (global_id,)
            )
            customer['identities'] = cur.fetchall()

            cur.execute(
                'SELECT lifesync_score, health_score, finance_score, asset_score, last_calc_dt FROM customer_360_profile WHERE global_id = %s',
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
                'SELECT domain, consent_flag, consent_version, revoke_dt, created_dt FROM consent WHERE global_id = %s',
                (global_id,)
            )
            rows = cur.fetchall()
    finally:
        db.close()
    return {'global_id': global_id, 'consents': rows}


@app.get('/internal/identity/{source_customer_id}')
def get_identity(source_customer_id: str, domain: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT global_id FROM customer_identity_map WHERE source_customer_id = %s AND domain = %s',
                (source_customer_id, domain)
            )
            row = cur.fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404, detail='Identity mapping not found')
    return row


# ── 인증 엔드포인트 ───────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post('/internal/auth/login')
def auth_login(req: LoginRequest):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE login_email = %s', (req.email,))
            user = cur.fetchone()
    finally:
        db.close()
    if not user or hash_password(req.password) != user['password_hash']:
        raise HTTPException(status_code=401, detail='이메일 또는 비밀번호 불일치')
    return {
        'ls_user_id':   user['ls_user_id'],
        'global_id':    user['global_id'],
        'login_email':  user['login_email'],
    }


class RegisterRequest(BaseModel):
    ls_user_id:    str
    global_id:     str
    email:         str
    password_hash: str
    name:          Optional[str] = None
    mobile:        Optional[str] = None
    rrn:           Optional[str] = None
    address:       Optional[str] = None

@app.post('/internal/auth/register')
def auth_register(req: RegisterRequest):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'INSERT INTO master_customer (global_id) VALUES (%s)',
                (req.global_id,)
            )
            cur.execute(
                'INSERT INTO users (ls_user_id, global_id, login_email, password_hash, mobile) VALUES (%s, %s, %s, %s, %s)',
                (req.ls_user_id, req.global_id, req.email, req.password_hash, req.mobile)
            )
            cur.execute(
                '''INSERT INTO customer_pii_secure
                       (pii_token, global_id, customer_name_enc, rrn_enc, mobile_enc, email_enc, address_enc)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (
                    pii_token_of(req.global_id), req.global_id,
                    encrypt_pii(req.name), encrypt_pii(req.rrn), encrypt_pii(req.mobile),
                    encrypt_pii(req.email), encrypt_pii(req.address),
                )
            )
            db.commit()
    finally:
        db.close()
    return {'status': 'ok', 'ls_user_id': req.ls_user_id, 'global_id': req.global_id}


@app.get('/internal/pii/{global_id}')
def get_pii(global_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT customer_name_enc, rrn_enc, mobile_enc, email_enc, address_enc'
                ' FROM customer_pii_secure WHERE global_id = %s',
                (global_id,)
            )
            row = cur.fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404, detail='PII 정보 없음')
    return {
        'global_id': global_id,
        'name':      decrypt_pii(row['customer_name_enc']),
        'rrn':       decrypt_pii(row['rrn_enc']),
        'mobile':    decrypt_pii(row['mobile_enc']),
        'email':     decrypt_pii(row['email_enc']),
        'address':   decrypt_pii(row['address_enc']),
    }


@app.get('/internal/auth/user/{ls_user_id}')
def auth_get_user(ls_user_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT ls_user_id, global_id, login_email FROM users WHERE ls_user_id = %s',
                (ls_user_id,)
            )
            user = cur.fetchone()
    finally:
        db.close()
    if not user:
        raise HTTPException(status_code=404, detail='사용자 없음')
    return user


class ConsentSaveRequest(BaseModel):
    global_id: str
    consents:  list

ALL_CONSENT_KEYS = ['BANK', 'CARD', 'INSURANCE', 'SECURITIES', 'HEALTHCARE', 'HOSPITAL', 'WEARABLE']

@app.post('/internal/auth/consent')
def auth_save_consent(req: ConsentSaveRequest):
    checked = set(req.consents)
    db = get_db()
    try:
        with db.cursor() as cur:
            for key in ALL_CONSENT_KEYS:
                if key in checked:
                    cur.execute(
                        '''INSERT INTO consent (global_id, domain, consent_flag, consent_dt, revoke_dt)
                           VALUES (%s, %s, 'Y', NOW(), NULL)
                           ON DUPLICATE KEY UPDATE
                               consent_flag = 'Y',
                               consent_dt   = COALESCE(consent_dt, NOW()),
                               revoke_dt    = NULL''',
                        (req.global_id, key)
                    )
                else:
                    cur.execute(
                        '''INSERT INTO consent (global_id, domain, consent_flag)
                           VALUES (%s, %s, 'N')
                           ON DUPLICATE KEY UPDATE
                               consent_flag = 'N',
                               revoke_dt    = IF(consent_dt IS NOT NULL AND revoke_dt IS NULL, NOW(), revoke_dt)''',
                        (req.global_id, key)
                    )
            db.commit()
    finally:
        db.close()
    return {'status': 'ok'}


@app.post('/internal/deploy')
async def trigger_deploy(request: Request):
    if request.headers.get('X-Deploy-Token', '') != DEPLOY_TOKEN:
        raise HTTPException(status_code=401, detail='배포 토큰 불일치')
    subprocess.Popen(['/opt/private-api/trigger_ansible.sh'])
    return {'status': 'triggered'}


class MatchRequest(BaseModel):
    domain:             str
    source_customer_id: str
    global_id:          str


@app.post('/internal/match')
def match_identity(req: MatchRequest):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                '''INSERT INTO customer_identity_map (global_id, domain, source_customer_id)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE source_customer_id = VALUES(source_customer_id)''',
                (req.global_id, req.domain, req.source_customer_id)
            )
            cur.execute(
                '''INSERT INTO matching_audit_log (request_id, ls_user_id, match_rule, result, matched_global_id)
                   VALUES (%s, %s, %s, %s, %s)''',
                (
                    str(__import__('uuid').uuid4()),
                    req.source_customer_id,
                    req.domain,
                    'MATCH',
                    req.global_id,
                )
            )
            db.commit()
    finally:
        db.close()
    return {'status': 'ok', 'global_id': req.global_id}

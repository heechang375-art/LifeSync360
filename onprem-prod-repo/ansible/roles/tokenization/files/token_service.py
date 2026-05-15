import boto3
import hashlib
import json
import os
import uuid
import pymysql
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

REGION = 'ap-northeast-2'
SECRET_ID = 'lifesync/onprem-db'
DB_NAME = 'lifesync_onprem'
MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')

ALLOWED_FIELDS = {'resident_number', 'phone_number', 'account_number', 'card_number', 'email'}


def get_db():
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASS')
    if not db_user or not db_pass:
        secret = boto3.client('secretsmanager', region_name=REGION).get_secret_value(SecretId=SECRET_ID)
        creds = json.loads(secret['SecretString'])
        db_user = creds['username']
        db_pass = creds['password']
    return pymysql.connect(
        host=MYSQL_HOST,
        user=db_user,
        password=db_pass,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


class TokenizeRequest(BaseModel):
    field: str
    value: str
    global_id: str = None


class TokenizeResponse(BaseModel):
    token_id: str


@app.post('/tokenize', response_model=TokenizeResponse)
def tokenize(req: TokenizeRequest):
    if req.field not in ALLOWED_FIELDS:
        raise HTTPException(status_code=400, detail=f"Field '{req.field}' not in allowed fields")

    original_hash = hashlib.sha256(req.value.encode()).hexdigest()

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT token_id FROM token_map WHERE original_hash = %s', (original_hash,))
            row = cur.fetchone()
            if row:
                return TokenizeResponse(token_id=row['token_id'])

            token_id = str(uuid.uuid4())
            cur.execute(
                'INSERT INTO token_map (token_id, field_name, original_hash, global_id) VALUES (%s, %s, %s, %s)',
                (token_id, req.field, original_hash, req.global_id)
            )
            db.commit()
    finally:
        db.close()

    return TokenizeResponse(token_id=token_id)


@app.get('/detokenize/{token_id}')
def detokenize(token_id: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'SELECT field_name, global_id, created_at FROM token_map WHERE token_id = %s',
                (token_id,)
            )
            row = cur.fetchone()
    finally:
        db.close()

    if not row:
        raise HTTPException(status_code=404, detail='Token not found')
    return {'token_id': token_id, **row}


@app.get('/health')
def health():
    return {'status': 'ok'}

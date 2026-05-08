#!/usr/bin/env python3
"""
master_customer.representative_name, birth_dt 를 Fernet AES 암호화.

실행 전 환경변수 설정:
  export PII_AES_KEY=<pii-encryption-guide.md 1단계에서 생성한 키>
  export DB_PASS=<MySQL root 패스워드>
  export DB_HOST=127.0.0.1  (ls-db에서 실행 시 기본값)
  export DB_USER=root        (기본값)
"""
import os
import pymysql
from cryptography.fernet import Fernet

BATCH = 10_000
f     = Fernet(os.environ['PII_AES_KEY'].encode())


def enc(val):
    if val is None:
        return None
    return f.encrypt(str(val).encode('utf-8')).decode('utf-8')


conn = pymysql.connect(
    host=os.environ.get('DB_HOST', '127.0.0.1'),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ['DB_PASS'],
    database='lifesync_onprem',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) AS cnt FROM master_customer')
        total = cur.fetchone()['cnt']
        print(f'총 {total:,}건 처리 시작')

    offset, done = 0, 0
    while True:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT global_id, representative_name, birth_dt FROM master_customer LIMIT %s OFFSET %s',
                (BATCH, offset)
            )
            rows = cur.fetchall()
        if not rows:
            break

        with conn.cursor() as cur:
            cur.executemany(
                'UPDATE master_customer SET representative_name=%s, birth_dt=%s WHERE global_id=%s',
                [(enc(r['representative_name']),
                  enc(str(r['birth_dt']) if r['birth_dt'] else None),
                  r['global_id']) for r in rows]
            )
        conn.commit()
        done += len(rows)
        offset += BATCH
        print(f'{done:,} / {total:,}')
finally:
    conn.close()

print('암호화 완료')

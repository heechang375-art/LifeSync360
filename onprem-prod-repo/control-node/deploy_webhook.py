import json
import os
import subprocess
import threading
import urllib.error
import urllib.request
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

DEPLOY_TOKEN     = os.environ['DEPLOY_TOKEN']
CODECOMMIT_URL   = os.environ['CODECOMMIT_URL']
PRIVATE_API_URL  = os.environ.get('PRIVATE_API_URL', 'http://172.16.1.73')
INVENTORY        = 'ansible/inventory/hosts.yml'
PLAYBOOK         = 'ansible/site.yml'
LOG              = '/var/log/ansible-deploy.log'


def _api_get(path):
    try:
        with urllib.request.urlopen(f'{PRIVATE_API_URL}{path}', timeout=8) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=json.loads(e.read() or b'{}'))


def _api_post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f'{PRIVATE_API_URL}{path}',
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=json.loads(e.read() or b'{}'))


def _deploy():
    with open(LOG, 'a') as f:
        try:
            subprocess.run(
                ['ansible-pull', '-U', CODECOMMIT_URL, '-i', INVENTORY,
                 '--if-changed', PLAYBOOK],
                check=True, stdout=f, stderr=f,
            )
        except subprocess.CalledProcessError as e:
            f.write(f'배포 실패: {e}\n')


@app.post('/deploy')
async def deploy(request: Request):
    if request.headers.get('X-Deploy-Token', '') != DEPLOY_TOKEN:
        raise HTTPException(status_code=401, detail='토큰 불일치')
    threading.Thread(target=_deploy, daemon=True).start()
    return {'status': 'triggered'}


@app.post('/query')
async def query(request: Request):
    if request.headers.get('X-Deploy-Token', '') != DEPLOY_TOKEN:
        raise HTTPException(status_code=401, detail='토큰 불일치')

    body   = await request.json()
    action = body.get('action')

    if action == 'login':
        return _api_post('/internal/auth/login', {
            'email':    body['email'],
            'password': body['password'],
        })
    if action == 'register':
        return _api_post('/internal/auth/register', {
            'ls_user_id':    body['ls_user_id'],
            'global_id':     body['global_id'],
            'email':         body['email'],
            'password_hash': body['password_hash'],
        })
    if action == 'get_user':
        return _api_get(f'/internal/auth/user/{body["ls_user_id"]}')
    if action == 'get_consent':
        return _api_get(f'/internal/consent/{body["global_id"]}')
    if action == 'save_consent':
        return _api_post('/internal/auth/consent', {
            'global_id': body['global_id'],
            'consents':  body['consents'],
        })
    if action == 'get_profile':
        return _api_get(f'/internal/customer/{body["global_id"]}')
    if action == 'get_all':
        customer = _api_get(f'/internal/customer/{body["global_id"]}')
        consent  = _api_get(f'/internal/consent/{body["global_id"]}')
        return {
            'global_id': body['global_id'],
            'customer':  customer,
            'consents':  consent.get('consents', []),
        }
    raise HTTPException(status_code=400, detail=f'지원하지 않는 action: {action}')


@app.get('/health')
def health():
    return {'status': 'ok'}

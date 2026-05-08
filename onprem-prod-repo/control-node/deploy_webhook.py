import os
import subprocess
import threading
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

DEPLOY_TOKEN   = os.environ['DEPLOY_TOKEN']
CODECOMMIT_URL = os.environ['CODECOMMIT_URL']
INVENTORY      = 'ansible/inventory/hosts.yml'
PLAYBOOK       = 'ansible/site.yml'
LOG            = '/var/log/ansible-deploy.log'


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


@app.get('/health')
def health():
    return {'status': 'ok'}

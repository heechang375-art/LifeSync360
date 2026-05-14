"""
온프레미스 고객 데이터 조회 Lambda — Platform VPC 배치
VPN을 통해 온프레미스 Private API 직접 호출

event = {
    "action": "login"|"register"|"get_user"|"get_consent"|"save_consent"|"get_profile"|"get_pii"|"get_all",
    ...params
}
"""
import json
import os
import urllib.error
import urllib.request

PRIVATE_API_URL = os.environ['PRIVATE_API_URL']   # http://172.16.1.73


def _api_get(path):
    with urllib.request.urlopen(f'{PRIVATE_API_URL}{path}', timeout=8) as resp:
        return json.loads(resp.read())


def _api_post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f'{PRIVATE_API_URL}{path}',
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read())


def _resp(status, body):
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body, ensure_ascii=False),
    }


def handler(event, context):
    body   = json.loads(event['body']) if 'body' in event else event
    action = body.get('action')

    if not action:
        return _resp(400, {'error': '필수 필드 누락: action'})

    try:
        if action == 'login':
            result = _api_post('/internal/auth/login', {
                'email':    body['email'],
                'password': body['password'],
            })
        elif action == 'register':
            result = _api_post('/internal/auth/register', {
                'ls_user_id':    body['ls_user_id'],
                'global_id':     body['global_id'],
                'email':         body['email'],
                'password_hash': body['password_hash'],
                'name':          body.get('name'),
                'mobile':        body.get('mobile'),
                'rrn':           body.get('rrn'),
                'address':       body.get('address'),
            })
        elif action == 'get_user':
            result = _api_get(f'/internal/auth/user/{body["ls_user_id"]}')
        elif action == 'get_consent':
            result = _api_get(f'/internal/consent/{body["global_id"]}')
        elif action == 'save_consent':
            result = _api_post('/internal/auth/consent', {
                'global_id': body['global_id'],
                'consents':  body['consents'],
            })
        elif action == 'get_profile':
            result = _api_get(f'/internal/customer/{body["global_id"]}')
        elif action == 'get_pii':
            result = _api_get(f'/internal/pii/{body["global_id"]}')
        elif action == 'get_all':
            customer = _api_get(f'/internal/customer/{body["global_id"]}')
            consent  = _api_get(f'/internal/consent/{body["global_id"]}')
            result   = {
                'global_id': body['global_id'],
                'customer':  customer,
                'consents':  consent.get('consents', []),
            }
        else:
            return _resp(400, {'error': f'지원하지 않는 action: {action}'})

        return _resp(200, result)

    except urllib.error.HTTPError as e:
        code = e.code
        try:
            detail = json.loads(e.read())
        except Exception:
            detail = {'error': str(e)}
        return _resp(code if code in (400, 401, 404) else 502, detail)
    except Exception as e:
        return _resp(502, {'error': f'온프레미스 연결 실패: {str(e)}'})

import jwt
import datetime
from datetime import timezone

JWT_SECRET = 'dev-jwt-secret-lifesync360-32bytes!!'

token = jwt.encode({
    'sub': 'LS-AABBCC11-000001',
    'gid': 'G000000001',
    'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=24),
}, JWT_SECRET, algorithm='HS256')

print(token)

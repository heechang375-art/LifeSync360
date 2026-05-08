"""
DynamoDB 테이블 생성 스크립트
실행: python create_dynamodb.py
사전 조건: AWS CLI 설정 완료 (aws configure)
"""
import boto3

REGION = 'ap-northeast-2'
TABLE  = 'lifesync_customer_result'


def main():
    client = boto3.client('dynamodb', region_name=REGION)

    try:
        client.create_table(
            TableName=TABLE,
            AttributeDefinitions=[
                {'AttributeName': 'global_id', 'AttributeType': 'S'}
            ],
            KeySchema=[
                {'AttributeName': 'global_id', 'KeyType': 'HASH'}
            ],
            BillingMode='PAY_PER_REQUEST',
            Tags=[
                {'Key': 'Project', 'Value': 'lifesync360'},
                {'Key': 'Owner',   'Value': 'hwanghc'},
            ]
        )
        print(f"[OK] 테이블 생성 요청 완료: {TABLE}")

        waiter = client.get_waiter('table_exists')
        print("     ACTIVE 상태 대기 중...")
        waiter.wait(TableName=TABLE)
        print(f"[OK] 테이블 ACTIVE 확인")

        # TTL 활성화 (ttl 필드 기준 자동 삭제)
        client.update_time_to_live(
            TableName=TABLE,
            TimeToLiveSpecification={'AttributeName': 'ttl', 'Enabled': True}
        )
        print(f"[OK] TTL 활성화 완료 (필드: ttl)")

    except client.exceptions.ResourceInUseException:
        print(f"[SKIP] 테이블 이미 존재: {TABLE}")


if __name__ == '__main__':
    main()

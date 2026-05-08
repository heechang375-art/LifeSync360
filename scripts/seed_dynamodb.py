"""
DynamoDB 초기 더미 데이터 적재 스크립트
실행: python seed_dynamodb.py
사전 조건: create_dynamodb.py 실행 완료
"""
import boto3, time

REGION = 'ap-northeast-2'
TABLE  = 'lifesync_customer_result'

TTL = int(time.time()) + 86400 * 30  # 30일 후 만료

DUMMY = [
    {
        'global_id': 'G001', 'dynamic_score': '92.4', 'dynamic_grade': 'VIP',
        'next_best_action': 'PB_CENTER', 'vip_prob': '0.94',
        'signup_prob': '0.81', 'rec_prob': '0.77', 'health_score': '88.1',
    },
    {
        'global_id': 'G002', 'dynamic_score': '74.1', 'dynamic_grade': 'GOLD',
        'next_best_action': 'ETF_RECOMMEND', 'vip_prob': '0.61',
        'signup_prob': '0.55', 'rec_prob': '0.63', 'health_score': '72.0',
    },
    {
        'global_id': 'G003', 'dynamic_score': '55.2', 'dynamic_grade': 'SILVER',
        'next_best_action': 'HEALTH_CHECKUP', 'vip_prob': '0.21',
        'signup_prob': '0.40', 'rec_prob': '0.38', 'health_score': '48.0',
    },
    {
        'global_id': 'G004', 'dynamic_score': '38.7', 'dynamic_grade': 'BRONZE',
        'next_best_action': 'RETENTION_COUPON', 'vip_prob': '0.08',
        'signup_prob': '0.29', 'rec_prob': '0.21', 'health_score': '61.0',
    },
    {
        'global_id': 'G005', 'dynamic_score': '21.3', 'dynamic_grade': 'BASIC',
        'next_best_action': 'RETENTION_COUPON', 'vip_prob': '0.02',
        'signup_prob': '0.15', 'rec_prob': '0.10', 'health_score': '55.0',
    },
]


def main():
    table = boto3.resource('dynamodb', region_name=REGION).Table(TABLE)

    for d in DUMMY:
        d.update({
            'update_time': '2026-04-30T04:30:00Z',
            'source': 'INIT',
            'ttl': TTL,
        })
        table.put_item(Item=d)
        print(f"[OK] {d['global_id']} ({d['dynamic_grade']}, {d['dynamic_score']}점)")

    print(f"\n적재 완료: {len(DUMMY)}건")


if __name__ == '__main__':
    main()

from decimal import Decimal
import time
import json
import boto3
import os
import signal
import sys
import uuid

# --- [설정] ---
STREAM_NAME = os.environ.get('STREAM_NAME', 'paysim-stream')
REGION_NAME = os.environ.get('AWS_REGION', 'ap-northeast-2')
SHARD_ID = 'shardId-000000000000' # 샤드가 1개라고 가정 (비용 절약)

# AWS 클라이언트 (Pod에 IAM Role이 있으면 자동 인증됨)
kinesis = boto3.client('kinesis', region_name=REGION_NAME)

# --- [가짜 모델 로직] (나중에 팀원 코드로 교체) ---
def dummy_predict(data):
    # 단순 규칙: 5만원 넘으면 사기로 간주
    amount = data.get('amount', Decimal('0'))  # Decimal 처리
    if amount > Decimal('50000'):
        return True
    return False

def process_record(record):
    try:
        # Kinesis record를 안전하게 Decimal로 파싱 (핵심 수정!)
        payload = json.loads(record['Data'], parse_float=lambda x: Decimal(str(x)))
        
        # 1. 차단 리스트 확인
        dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
        block_table = dynamodb.Table('block-list')
        
        response = block_table.get_item(Key={'user_id': payload['nameOrig']})
        if 'Item' in response:
            print(f"🚫 BLOCKED: {payload['nameOrig']} is in block list")
            return
        
        # 2. 모델 예측 (amount 이미 Decimal)
        is_fraud = dummy_predict(payload)  # dummy_predict도 수정 필요 (아래)
        
        # 3. 거래 로그 저장 (모든 값 Decimal 안전)
        log_table = dynamodb.Table('transaction-logs')
        log_table.put_item(Item={
            'transaction_id': str(uuid.uuid4()),
            'timestamp': payload.get('step', 0),  # step을 timestamp 대신
            'amount': payload['amount'],  # 이미 Decimal
            'oldbalanceOrg': payload.get('oldbalanceOrg', Decimal('0')),
            'newbalanceOrig': payload.get('newbalanceOrig', Decimal('0')),
            'user_id': payload['nameOrig'],
            'is_fraud': is_fraud,
            'type': payload['type']
        })
        
        # 4. Fraud면 차단 + 알림
        if is_fraud:
            print(f"🚨 FRAUD DETECTED: {payload['amount']}")
            
            block_table.put_item(Item={
                'user_id': payload['nameOrig'],
                'reason': 'fraud_detection',
                'amount': payload['amount'],
                'timestamp': int(time.time()),
                'ttl': int(time.time()) + 86400
            })
            
            sns = boto3.client('sns', region_name='ap-northeast-2')
            sns.publish(
                TopicArn='arn:aws:sns:ap-northeast-2:306901005856:fraud-alerts',
                Message=f"Fraud Alert!\nUser: {payload['nameOrig']}\nAmount: {payload['amount']}\nType: {payload['type']}"
            )
        else:
            print(f"✅ NORMAL: {payload['amount']}")
            
    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        traceback.print_exc()  # 디버깅 위해 추가

def main():
    print(f"🚀 Starting Consumer for Stream: {STREAM_NAME}")
    
    # 샤드 이터레이터 가져오기 (LATEST: 지금부터 들어오는 데이터만)
    shard_iterator = kinesis.get_shard_iterator(
        StreamName=STREAM_NAME,
        ShardId=SHARD_ID,
        ShardIteratorType='LATEST'
    )['ShardIterator']
    
    # 무한 루프 (데이터 Polling)
    while True:
        try:
            response = kinesis.get_records(
                ShardIterator=shard_iterator,
                Limit=100  # 한 번에 최대 100개
            )
            
            records = response['Records']
            if records:
                print(f"Processing {len(records)} records...")
                for record in records:
                    process_record(record)
            
            # 다음 이터레이터 갱신
            shard_iterator = response['NextShardIterator']
            
            # 너무 빨리 돌면 비용/부하 문제 생기니 살짝 대기
            time.sleep(1) 
            
        except Exception as e:
            print(f"Kinesis Error: {e}")
            time.sleep(5) # 에러 나면 좀 오래 쉬었다 재시도

# 우아한 종료 처리 (Pod 삭제 시)
def signal_handler(sig, frame):
    print('Stopping consumer...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    main()

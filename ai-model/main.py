from decimal import Decimal
import time
import json
import boto3
import os
import signal
import sys
import uuid
#Heebird
import joblib
import numpy as np
# --- [설정] ---
STREAM_NAME = os.environ.get('STREAM_NAME', 'paysim-stream')
REGION_NAME = os.environ.get('AWS_REGION', 'ap-northeast-2')
SHARD_ID = 'shardId-000000000000' # 샤드가 1개라고 가정 (비용 절약)

# AWS 클라이언트 (Pod에 IAM Role이 있으면 자동 인증됨)
kinesis = boto3.client('kinesis', region_name=REGION_NAME)

# 모델 로드 (앱 초기화 시 1회만 실행)
# Dockerfile에서 COPY한 경로에 맞게 수정 ('/model.pkl')
model = joblib.load('/app/model.pkl')
'''
# --- [가짜 모델 로직] (나중에 팀원 코드로 교체) ---
def dummy_predict(data):
    # 단순 규칙: 5만원 넘으면 사기로 간주
    amount = data.get('amount', Decimal('0'))  # Decimal 처리
    if amount > Decimal('50000'):
        return True
    return False
'''

def ml_predict(payload):
    """
    Kinesis에서 들어오는 단일 거래 로그를 받아 사기 여부를 예측합니다.
    """
    tx_type = payload.get('type')
    
    # 1. TRANSFER, CASH_OUT이 아닌 거래는 사기가 아니므로 예측 생략 (속도 최적화)
    if tx_type not in ['TRANSFER', 'CASH_OUT']:
        return False
        
    # 2. 페이로드에서 값 추출 (원천 데이터 컬럼명 'oldbalanceOrg' 반영)
    step = int(payload.get('step', 0))
    amount = float(payload.get('amount', 0.0))
    old_orig = float(payload.get('oldbalanceOrg', payload.get('oldBalanceOrig', 0.0)))
    new_orig = float(payload.get('newbalanceOrig', 0.0))
    old_dest = float(payload.get('oldbalanceDest', 0.0))
    new_dest = float(payload.get('newbalanceDest', 0.0))
    
    # 3. type 인코딩
    type_encoded = 0 if tx_type == 'TRANSFER' else 1
    
    # 4. 결측치 처리 (노트북 로직 동일)
    if old_dest == 0 and new_dest == 0 and amount != 0:
        old_dest, new_dest = -1.0, -1.0
        
    if old_orig == 0 and new_orig == 0 and amount != 0:
        old_orig, new_orig = np.nan, np.nan
        
    # 5. 파생변수 (Feature Engineering) 계산
    error_orig = new_orig + amount - old_orig
    error_dest = old_dest + amount - new_dest
    
    # 6. 모델 입력 배열 구성 (학습 시 X 데이터프레임 컬럼 순서와 100% 일치해야 함)
    # [step, type, amount, oldBalanceOrig, newBalanceOrig, oldBalanceDest, newBalanceDest, errorBalanceOrig, errorBalanceDest]
    features = [[
        step, type_encoded, amount, 
        old_orig, new_orig, old_dest, new_dest, 
        error_orig, error_dest
    ]]
    
    # 7. 모델 예측 (사기 확률이 0.5 이상이면 True 반환)
    fraud_prob = model.predict_proba(features)[0][1]
    
    return bool(fraud_prob > 0.5)

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
        #is_fraud = dummy_predict(payload)  # dummy_predict도 수정 필요 (아래)
        is_fraud = ml_predict(payload)

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
                    time.sleep(5)#keda-autoscaling test용
            
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

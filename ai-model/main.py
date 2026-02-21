import time
import json
import boto3
import os
import signal
import sys

# --- [설정] ---
STREAM_NAME = os.environ.get('STREAM_NAME', 'paysim-stream')
REGION_NAME = os.environ.get('AWS_REGION', 'ap-northeast-2')
SHARD_ID = 'shardId-000000000000' # 샤드가 1개라고 가정 (비용 절약)

# AWS 클라이언트 (Pod에 IAM Role이 있으면 자동 인증됨)
kinesis = boto3.client('kinesis', region_name=REGION_NAME)

# --- [가짜 모델 로직] (나중에 팀원 코드로 교체) ---
def dummy_predict(data):
    # 단순 규칙: 5만원 넘으면 사기로 간주
    amount = float(data.get('amount', 0))
    if amount > 50000:
        return True
    return False

def process_record(record):
    try:
        # 1. 데이터 파싱 (JSON 문자열 -> 딕셔너리)
        payload = json.loads(record['Data'])
        
        # 2. 모델 예측
        is_fraud = dummy_predict(payload)
        
        # 3. 결과 로그 출력 (CloudWatch에서 확인 가능)
        status = "🚨 FRAUD" if is_fraud else "✅ NORMAL"
        print(f"[{status}] Amount: {payload.get('amount')} | User: {payload.get('nameOrig')}")

        # TODO: Phase 3에서 여기에 DynamoDB 저장 및 SNS 알림 로직 추가 예정

    except Exception as e:
        print(f"Error processing record: {e}")

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

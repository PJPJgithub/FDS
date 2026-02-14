import csv
import json
import time
import random
import boto3
import datetime
import uuid

# ==========================================
# [설정 영역] 비용 절약을 위해 처음엔 DRY_RUN을 True로 하세요!
# ==========================================
csv_file_path = 'paysim.csv'      # 데이터 파일명
kinesis_stream_name = 'paysim-stream'  # AWS Kinesis 스트림 이름 (나중에 생성할 것)
region_name = 'ap-northeast-2'    # 서울 리전

# True: 화면에만 출력 (무료/테스트용)
# False: 실제 AWS Kinesis로 전송 (유료/실전용)
DRY_RUN = False
# ==========================================

def get_kinesis_client():
    if DRY_RUN:
        return None
    try:
        # AWS 자격 증명은 ~/.aws/credentials 파일이나 환경변수에서 가져옵니다.
        return boto3.client('kinesis', region_name=region_name)
    except Exception as e:
        print(f"AWS 연결 오류: {e}")
        return None

def send_record(client, record):
    partition_key = str(record['nameOrig']) # 유저별로 순서를 보장하기 위해 송금자ID를 키로 사용
    data_json = json.dumps(record)

    if DRY_RUN:
        print(f"[TEST] 전송 데이터: {data_json}")
    else:
        try:
            response = client.put_record(
                StreamName=kinesis_stream_name,
                Data=data_json,
                PartitionKey=partition_key
            )
            # 성공 시 별도 출력 없이 넘어감 (속도 저하 방지)
        except Exception as e:
            print(f"전송 실패: {e}")

def main():
    kinesis_client = get_kinesis_client()
    
    print(f"🚀 트랜잭션 시뮬레이터 시작... (모드: {'TEST/무료' if DRY_RUN else 'LIVE/유료'})")
    
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # 무한 루프를 돌리고 싶다면 데이터를 메모리에 다 올리거나, 파일을 다시 열어야 함
            # 여기서는 파일 끝까지 읽으면 종료되는 구조
            for row in reader:
                
                # 1. 데이터 가공 (실시간 데이터처럼 보이기 위해 현재 시간 추가)
                # 원본 데이터의 타입에 맞게 변환
                record = {
                    'step': int(row['step']),
                    'type': row['type'],
                    'amount': float(row['amount']),
                    'nameOrig': row['nameOrig'],
                    'oldbalanceOrg': float(row['oldbalanceOrg']),
                    'newbalanceOrig': float(row['newbalanceOrig']),
                    'nameDest': row['nameDest'],
                    'oldbalanceDest': float(row['oldbalanceDest']),
                    'newbalanceDest': float(row['newbalanceDest']),
                    'isFraud': int(row['isFraud']),
                    'isFlaggedFraud': int(row['isFlaggedFraud']),
                    'timestamp': datetime.datetime.now().isoformat() # 현재 시간 추가 (중요)
                }

                # 2. 전송
                send_record(kinesis_client, record)

                # 3. 속도 조절 (초당 10개 ~ 100개 랜덤)
                # 1초에 10개 = 0.1초 대기
                # 1초에 100개 = 0.01초 대기
                sleep_time = random.uniform(0.01, 0.1)
                time.sleep(sleep_time)

    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {csv_file_path}")
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단되었습니다.")

if __name__ == "__main__":
    main()
import joblib
import numpy as np

# 1. 모델 로드 (앱 초기화 시 1회만 실행)
# Dockerfile에서 COPY한 경로에 맞게 수정 ('/app/model.pkl')
model = joblib.load('/app/model.pkl')

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

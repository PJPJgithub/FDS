# 가볍고 빠른 Python 이미지 사용
FROM python:3.11-slim

WORKDIR /app

# 팀원 ML 의존성 [file:66]
COPY requirements-ml.txt .
RUN pip install -r requirements-ml.txt

# 의존성 설치 (캐시 활용을 위해 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

'''
# 소스 코드 복사
COPY main.py .
COPY model.pkl /model.pkl  # 팀원 모델!
'''
# ai-model 폴더 전체 복사
COPY ai-model/ /app/

# 실행 명령어
CMD ["python", "-u", "main.py"] 
# -u 옵션: 로그가 버퍼링 없이 바로 출력되게 함 (중요)

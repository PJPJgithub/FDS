# 가볍고 빠른 Python 이미지 사용
FROM python:3.9-slim

WORKDIR /app

# 의존성 설치 (캐시 활용을 위해 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY main.py .

# 실행 명령어
CMD ["python", "-u", "main.py"] 
# -u 옵션: 로그가 버퍼링 없이 바로 출력되게 함 (중요)

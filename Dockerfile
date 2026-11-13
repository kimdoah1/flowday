FROM python:3.13-slim

# 작업 디렉토리 설정
# print() 출력이 docker logs 에 바로 보이도록 (stdout 버퍼링 해제)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# requirements.txt 파일을 컨테이너에 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Flask 애플리케이션 코드 복사
COPY . .

# 컨테이너에서 노출할 포트
EXPOSE 5001

# Flask 서버 실행
CMD ["python", "app.py"]

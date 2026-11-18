FROM python:3.12-slim

# print() 가 docker logs 에 바로 보이도록
ENV PYTHONUNBUFFERED=1 \
    WHISPER_MODEL=small \
    AUDIO_DIR=/data/audio \
    API_URL=http://api:8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Whisper 모델을 이미지에 미리 받아 둔다 (컨테이너 첫 실행이 느려지지 않게)
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

COPY main.py .

CMD ["python", "main.py"]

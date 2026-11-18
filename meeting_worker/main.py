"""meeting-worker — 회의 녹음을 Whisper 로 글로 바꾸는 컨테이너 (담당: 정혁)

Whisper 구현으로 faster-whisper(오픈소스, MIT)를 쓴다. ffmpeg 를 따로 설치하지 않아도 된다.

두 가지 방법으로 실행할 수 있다.

1) 단독 테스트 — 녹음 파일 하나를 바로 전사
       python main.py --file 녹음.wav

2) 서비스 모드 — api 에 쌓인 녹음을 계속 처리 (Docker 에서 기본)
       python main.py
   5초마다 GET  {API_URL}/api/meetings?status=waiting
   전사 후     POST {API_URL}/api/meetings/{meeting_id}/result  {"transcript": "..."} 또는 {"error": "..."}
   녹음 파일은 api 와 같이 쓰는 볼륨 AUDIO_DIR(/data/audio) 에서 읽는다.

환경 변수
   API_URL        기본 http://api:8000
   AUDIO_DIR      기본 /data/audio
   WHISPER_MODEL  기본 small (빠르게: base / tiny). 실제 사람 목소리는 base 로는 숫자·요일을 자주 틀린다.
   POLL_SECONDS   기본 5
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from faster_whisper import WhisperModel

API_URL = os.getenv("API_URL", "http://api:8000").rstrip("/")
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "/data/audio"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "5"))

_model = None


def get_model() -> WhisperModel:
    """모델은 처음 한 번만 불러온다 (첫 실행 때 자동 다운로드)."""
    global _model
    if _model is None:
        print(f"[worker] Whisper 모델 불러오는 중: {WHISPER_MODEL}", flush=True)
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    """녹음 파일 → 한국어 텍스트."""
    segments, _info = get_model().transcribe(audio_path, language="ko", vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()


def process_waiting_meetings() -> int:
    """대기 중인 회의를 한 번 훑어서 처리한다. 처리한 개수를 돌려준다."""
    res = requests.get(f"{API_URL}/api/meetings", params={"status": "waiting"}, timeout=10)
    res.raise_for_status()
    count = 0
    for item in res.json().get("meetings", []):
        meeting_id = item["meeting_id"]
        path = AUDIO_DIR / item["audio_filename"]
        print(f"[worker] 회의 {meeting_id} 전사 시작: {path}", flush=True)
        try:
            text = transcribe(str(path))
            body = {"transcript": text} if text else {"error": "녹음에서 말소리를 찾지 못했습니다."}
        except Exception as exc:  # 파일 손상 등
            body = {"error": f"전사 실패: {exc}"}
        requests.post(f"{API_URL}/api/meetings/{meeting_id}/result", json=body, timeout=30)
        print(f"[worker] 회의 {meeting_id} 완료: {'error' if 'error' in body else 'done'}", flush=True)
        count += 1
    return count


def run_forever() -> None:
    print(f"[worker] 시작. API={API_URL}, AUDIO_DIR={AUDIO_DIR}", flush=True)
    while True:
        try:
            process_waiting_meetings()
        except requests.RequestException as exc:
            print(f"[worker] api 연결 실패, 잠시 후 재시도: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flowday 회의 녹음 전사 worker")
    parser.add_argument("--file", help="이 녹음 파일 하나만 전사하고 끝낸다 (단독 테스트)")
    args = parser.parse_args()

    if args.file:
        started = time.time()
        text = transcribe(args.file)
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
        print(f"[worker] {time.time() - started:.1f}초 걸림", file=sys.stderr)
    else:
        run_forever()


if __name__ == "__main__":
    main()

"""회의 분석 API (담당: 정혁)

가이드 3장 계약
  POST /api/meetings              multipart: file, name  → {"meeting_id": 1, "status": "waiting"}
  GET  /api/meetings/{meeting_id}  → {"meeting_id", "status", "summary", "transcript", "events", "error"}
  status 는 waiting / done / failed 만 쓴다.

동작
- .txt 회의록을 올리면 바로 요약·일정 추출을 하고 status=done 으로 저장한다.
- 녹음 파일(mp3, m4a, wav, webm, ogg)은 AUDIO_DIR 에 저장하고 status=waiting.
  meeting-worker 가 Whisper 로 글로 바꾼 뒤 아래 내부용 API로 결과를 보내면 done/failed 가 된다.

meeting-worker 전용 (가이드에 없는 내부 API — 통합 전에 팀 확인 필요)
  GET  /api/meetings?status=waiting           → {"meetings": [{"meeting_id", "audio_filename"}]}
  POST /api/meetings/{meeting_id}/result      {"transcript": "..."} 또는 {"error": "..."}

※ 저장은 지금 메모리(dict)에만 한다. 서버를 끄면 사라진다.
   김도아 님의 DB(models.py)가 준비되면 meetings 테이블로 옮긴다.
"""

import os
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.meeting_ai import analyze_meeting_text, today_kst

# 팀 main.py 가 app.include_router(meetings.router, prefix="/api") 로 등록한다.
# → 실제 주소는 /api/meetings, /api/meetings/{meeting_id}
router = APIRouter(prefix="/meetings", tags=["회의 분석 (정혁)"])

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".webm", ".ogg"}
TEXT_EXTENSIONS = {".txt"}
MAX_BYTES = 50 * 1024 * 1024  # 50MB


def _audio_dir() -> Path:
    # Docker 에서는 AUDIO_DIR=/data/audio (공유 볼륨). 로컬 테스트는 임시 폴더를 쓴다.
    path = Path(os.getenv("AUDIO_DIR") or Path(tempfile.gettempdir()) / "flowday_audio")
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---- 임시 저장소 (DB 연결 전) ----
_lock = threading.Lock()
_meetings: dict[int, dict] = {}
_next_id = 1


def _new_meeting(name: str | None) -> dict:
    global _next_id
    with _lock:
        meeting = {
            "meeting_id": _next_id,
            "name": name,
            "status": "waiting",
            "summary": None,
            "transcript": None,
            "events": [],
            "error": None,
            "audio_filename": None,
            "base_date": today_kst(),
        }
        _meetings[_next_id] = meeting
        _next_id += 1
    return meeting


def _finish(meeting: dict, transcript: str) -> None:
    result = analyze_meeting_text(transcript, meeting["base_date"])
    meeting.update(status="done", transcript=transcript, summary=result["summary"],
                   events=result["events"], error=None)


def _public(meeting: dict) -> dict:
    """가이드 계약에 있는 키만 돌려준다."""
    keys = ("meeting_id", "status", "summary", "transcript", "events", "error")
    return {k: meeting[k] for k in keys}


# ---- 가이드 계약 API ----

@router.post("", status_code=201)
async def upload_meeting(file: UploadFile = File(...), name: str | None = Form(None)) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in AUDIO_EXTENSIONS | TEXT_EXTENSIONS:
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다: {ext or '확장자 없음'} "
                                 "(가능: txt, mp3, m4a, wav, webm, ogg)")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "파일은 50MB 이하만 올릴 수 있습니다.")

    meeting = _new_meeting(name or file.filename)

    if ext in TEXT_EXTENSIONS:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp949", errors="replace")  # 윈도우 메모장 기본 인코딩 대비
        _finish(meeting, text)
    else:
        filename = f"{meeting['meeting_id']}{ext}"
        (_audio_dir() / filename).write_bytes(data)
        meeting["audio_filename"] = filename

    return {"meeting_id": meeting["meeting_id"], "status": meeting["status"]}


@router.get("/{meeting_id}")
def get_meeting(meeting_id: int) -> dict:
    meeting = _meetings.get(meeting_id)
    if meeting is None:
        raise HTTPException(404, "회의를 찾을 수 없습니다.")
    return _public(meeting)


# ---- meeting-worker 전용 내부 API ----

@router.get("")
def list_meetings(status: str = "waiting") -> dict:
    items = [
        {"meeting_id": m["meeting_id"], "audio_filename": m["audio_filename"]}
        for m in _meetings.values()
        if m["status"] == status and m["audio_filename"]
    ]
    return {"meetings": items}


class WorkerResult(BaseModel):
    transcript: str | None = None
    error: str | None = None


@router.post("/{meeting_id}/result")
def save_worker_result(meeting_id: int, body: WorkerResult) -> dict:
    meeting = _meetings.get(meeting_id)
    if meeting is None:
        raise HTTPException(404, "회의를 찾을 수 없습니다.")
    if body.error or not body.transcript:
        meeting.update(status="failed", error=body.error or "전사 결과가 비어 있습니다.")
    else:
        try:
            _finish(meeting, body.transcript)
        except Exception as exc:  # 분석 실패도 failed 로 기록
            meeting.update(status="failed", transcript=body.transcript, error=str(exc))
    return _public(meeting)

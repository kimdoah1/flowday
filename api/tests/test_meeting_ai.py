"""정혁 담당: 일정 추출 · 회의 분석 테스트.

실행 (api 폴더에서):  pytest tests/test_meeting_ai.py
LLM 은 부르지 않는다 (LLM_MODE=rule). LLM 경로는 가짜 모델로 확인한다.
"""

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import meeting_ai
from app.routers import extract, meetings

BASE = date(2026, 11, 7)  # 토요일


@pytest.fixture(autouse=True)
def rule_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "rule")


# 팀 app/main.py 와 같은 방식(prefix="/api")으로 라우터를 등록한 테스트용 앱
app = FastAPI()
app.include_router(extract.router, prefix="/api")
app.include_router(meetings.router, prefix="/api")
client = TestClient(app)


# ---- 일정 추출 함수 ----

def test_guide_example():
    events = meeting_ai.extract_events("다음 주 월요일 오후 2시에 회의하자", BASE)
    assert events == [{
        "title": "회의",
        "start_at": "2026-11-09T14:00:00+09:00",
        "end_at": "2026-11-09T15:00:00+09:00",
    }]


@pytest.mark.parametrize("text", ["점심 뭐 먹지?", "언젠가 한번 회의하자", "2시에 회의하자", ""])
def test_no_event_or_unclear_date_returns_empty(text):
    assert meeting_ai.extract_events(text, BASE) == []


def test_weekday_without_week_word_means_next_occurrence():
    [event] = meeting_ai.extract_events("금요일 오후 2시에 팀 회의", BASE)
    assert event["title"] == "팀 회의"
    assert event["start_at"] == "2026-11-13T14:00:00+09:00"


def test_start_and_end_time():
    [event] = meeting_ai.extract_events("API 통합 회의는 다음 주 수요일 3시 반부터 5시까지", BASE)
    assert event["start_at"] == "2026-11-11T15:30:00+09:00"
    assert event["end_at"] == "2026-11-11T17:00:00+09:00"


def test_date_only_is_all_day():
    [event] = meeting_ai.extract_events("11월 13일 중간 발표", BASE)
    assert event["start_at"] == "2026-11-13T00:00:00+09:00"
    assert event["end_at"] == "2026-11-14T00:00:00+09:00"


def test_multiple_sentences():
    events = meeting_ai.extract_events("11월 13일 중간 발표. 내일까지 PPT 제출", BASE)
    assert [e["title"] for e in events] == ["중간 발표", "PPT 제출"]


def test_two_clauses_in_one_sentence():
    # 실제 녹음 전사문 (2026-11-09, 월요일 기준)
    events = meeting_ai.extract_events(
        "화요일에 오후 10시까지 회의 준비하시고 목요일에 3시까지 준비해주세요", date(2026, 11, 9))
    assert [e["start_at"] for e in events] == [
        "2026-11-10T22:00:00+09:00",
        "2026-11-12T15:00:00+09:00",
    ]


def test_original_flowday_html_example():
    # 원본 Flowday_오류수정_바로실행.html 의 회의록 예시
    text = (
        "팀 프로젝트 주간 회의\n참석: 개발팀 전원\n\n"
        "결정: 프론트엔드 시안은 11월 12일까지 완료한다.\n"
        "결정: API 명세는 11월 15일까지 공유한다.\n"
        "회의: 11월 18일 오후 3시에 다음 점검 회의를 진행한다.\n"
        "Docker Compose 구성은 이후 백엔드 작업과 병행한다."
    )
    events = meeting_ai.extract_events(text, date(2026, 11, 9))
    assert [(e["title"], e["start_at"][:16]) for e in events] == [
        ("프론트엔드 시안 완료", "2026-11-12T00:00"),
        ("API 명세 공유", "2026-11-15T00:00"),
        ("점검 회의", "2026-11-18T15:00"),
    ]


# ---- 회의 요약 ----

MEETING = (
    "오늘은 중간 발표 준비를 논의했다.\n"
    "프론트는 박수현이 맡기로 했다.\n"
    "다음 주 수요일 오후 3시에 리허설을 하자.\n"
    "점심은 학식으로 먹었다."
)


def test_summary_keeps_decisions():
    summary = meeting_ai.summarize_meeting(MEETING)
    assert "중간 발표 준비" in summary
    assert "맡기로" in summary
    assert "학식" not in summary


def test_analyze_meeting_text():
    result = meeting_ai.analyze_meeting_text(MEETING, BASE)
    assert result["events"] == [{
        "title": "리허설",
        "start_at": "2026-11-11T15:00:00+09:00",
        "end_at": "2026-11-11T16:00:00+09:00",
    }]


# ---- LLM 경로 (가짜 모델) ----

@pytest.fixture
def gemini_env(monkeypatch):
    """Gemini 를 쓰는 설정 (실제 호출은 하지 않는다)."""
    monkeypatch.setenv("LLM_MODE", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-test")


def test_llm_needs_gemini_key_and_model(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "auto")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "gemini-test")
    assert meeting_ai._llm_enabled() is False      # 키 없음 → 규칙 기반
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("LLM_MODEL")
    assert meeting_ai._llm_enabled() is False      # 모델 이름 없음 → 규칙 기반
    monkeypatch.setenv("LLM_MODEL", "gemini-test")
    assert meeting_ai._llm_enabled() is True


def test_llm_path_drops_unclear_dates(gemini_env, monkeypatch):
    fake = meeting_ai._LLMEvents(events=[
        meeting_ai._LLMEvent(title="팀 회의", date="2026-11-09", start_time="14:00", end_time=None),
        meeting_ai._LLMEvent(title="언젠가 회식", date=None, start_time=None, end_time=None),
    ])
    calls = []

    def fake_ask_llm(prompt, output_model):
        calls.append(output_model)
        return fake

    monkeypatch.setattr(meeting_ai, "_ask_llm", fake_ask_llm)
    assert meeting_ai.extract_events("아무 글", BASE) == [{
        "title": "팀 회의",
        "start_at": "2026-11-09T14:00:00+09:00",
        "end_at": "2026-11-09T15:00:00+09:00",
    }]
    assert calls == [meeting_ai._LLMEvents]  # 팀 ask_llm 과 같은 (prompt, output_model) 형태로 호출


def test_llm_summary_path(gemini_env, monkeypatch):
    monkeypatch.setattr(meeting_ai, "_ask_llm",
                        lambda prompt, model: meeting_ai._LLMSummary(summary="  리허설 일정 확정  "))
    assert meeting_ai.summarize_meeting("회의 내용") == "리허설 일정 확정"


def test_llm_error_falls_back_to_rules(gemini_env, monkeypatch):
    def broken(prompt, output_model):
        raise RuntimeError("network down")

    monkeypatch.setattr(meeting_ai, "_ask_llm", broken)
    assert meeting_ai.extract_events("다음 주 월요일 오후 2시에 회의하자", BASE)[0]["title"] == "회의"


def test_uses_team_ask_llm_when_available(gemini_env, monkeypatch):
    """팀 app/llm.py 가 있으면 그 ask_llm 을 쓴다."""
    import sys
    import types

    team_llm = types.ModuleType("app.llm")
    team_llm.ask_llm = lambda prompt, output_model: meeting_ai._LLMSummary(summary="팀 함수 사용")
    monkeypatch.setitem(sys.modules, "app.llm", team_llm)
    assert meeting_ai.summarize_meeting("회의 내용") == "팀 함수 사용"


# ---- API ----

def test_extract_api_contract():
    res = client.post("/api/ai/extract",
                      json={"text": "다음 주 월요일 오후 2시에 회의하자", "base_date": "2026-11-07"})
    assert res.status_code == 200
    assert res.json() == {"events": [{
        "title": "회의",
        "start_at": "2026-11-09T14:00:00+09:00",
        "end_at": "2026-11-09T15:00:00+09:00",
    }]}


def test_extract_api_no_event():
    res = client.post("/api/ai/extract", json={"text": "점심 뭐 먹지?", "base_date": "2026-11-07"})
    assert res.json() == {"events": []}


def test_meeting_text_upload_is_done_immediately():
    res = client.post("/api/meetings",
                      files={"file": ("meeting.txt", MEETING.encode("utf-8"), "text/plain")},
                      data={"name": "중간 발표 회의"})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "done"

    detail = client.get(f"/api/meetings/{body['meeting_id']}").json()
    assert set(detail) == {"meeting_id", "status", "summary", "transcript", "events", "error"}
    assert detail["status"] == "done"
    assert detail["events"][0]["title"] == "리허설"
    assert detail["error"] is None


def test_meeting_audio_upload_waits_for_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIO_DIR", str(tmp_path))
    res = client.post("/api/meetings", files={"file": ("rec.m4a", b"fake-audio", "audio/mp4")})
    meeting_id = res.json()["meeting_id"]
    assert res.json()["status"] == "waiting"

    detail = client.get(f"/api/meetings/{meeting_id}").json()
    assert detail == {"meeting_id": meeting_id, "status": "waiting", "summary": None,
                      "transcript": None, "events": [], "error": None}

    waiting = client.get("/api/meetings", params={"status": "waiting"}).json()["meetings"]
    assert {"meeting_id": meeting_id, "audio_filename": f"{meeting_id}.m4a"} in waiting

    done = client.post(f"/api/meetings/{meeting_id}/result",
                       json={"transcript": "내일 오후 4시에 회의하자"}).json()
    assert done["status"] == "done"
    assert done["events"][0]["start_at"].endswith("T16:00:00+09:00")


def test_meeting_worker_failure():
    res = client.post("/api/meetings", files={"file": ("rec.wav", b"x", "audio/wav")})
    meeting_id = res.json()["meeting_id"]
    failed = client.post(f"/api/meetings/{meeting_id}/result", json={"error": "Whisper 오류"}).json()
    assert failed["status"] == "failed"
    assert failed["error"] == "Whisper 오류"


def test_unknown_file_type_rejected():
    res = client.post("/api/meetings", files={"file": ("a.pdf", b"x", "application/pdf")})
    assert res.status_code == 400


def test_missing_meeting_404():
    assert client.get("/api/meetings/99999").status_code == 404

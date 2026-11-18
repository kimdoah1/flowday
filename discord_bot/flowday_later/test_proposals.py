"""후보 요청 테스트. 진짜 api·디스코드·LLM 없이 httpx.MockTransport로 검증한다."""
import asyncio
import json

import httpx

from api_client import (
    build_proposal_payload,
    create_proposal,
    make_external_id,
    process_message,
)

EVENT = {
    "title": "팀 회의",
    "start_at": "2026-11-09T14:00:00+09:00",
    "end_at": "2026-11-09T15:00:00+09:00",
}


def run_with(handler, content, message_id=123):
    """가짜 api를 붙여 process_message를 실행하고 (결과, 받은 요청 목록)을 돌려준다."""
    calls = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    async def go():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(wrapped), base_url="http://api:8000"
        ) as http:
            return await process_message(http, content, message_id, "2026-11-07")

    return asyncio.run(go()), calls


def normal_api(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/ai/extract":
        return httpx.Response(200, json={"events": [EVENT]})
    if request.url.path == "/api/proposals":
        return httpx.Response(201, json={"proposal_id": 1, "status": "pending"})
    return httpx.Response(404)


def test_external_id_format():
    assert make_external_id(123) == "discord-123"
    assert make_external_id(123, 1) == "discord-123-1"


def test_payload_matches_contract():
    payload = build_proposal_payload(EVENT, "월요일 2시에 회의하자", "discord-123")
    assert payload == {
        "title": "팀 회의",
        "start_at": "2026-11-09T14:00:00+09:00",
        "end_at": "2026-11-09T15:00:00+09:00",
        "source": "discord",
        "original_text": "월요일 2시에 회의하자",
        "external_id": "discord-123",
    }


def test_schedule_message_creates_proposal_only():
    created, calls = run_with(normal_api, "월요일 2시에 회의하자")
    assert created == ["팀 회의 (11/09 14:00)"]
    paths = [c.url.path for c in calls]
    assert paths == ["/api/ai/extract", "/api/proposals"]
    assert "/api/events" not in paths  # 확정 일정 API는 부르지 않는다
    body = json.loads(calls[1].content)
    assert body["source"] == "discord" and body["external_id"] == "discord-123"


def test_non_schedule_message_calls_nothing():
    created, calls = run_with(normal_api, "점심 뭐 먹지?")
    assert created == [] and calls == []


def test_empty_events_creates_no_proposal():
    def api(request):
        return httpx.Response(200, json={"events": []})

    created, calls = run_with(api, "내일 회의 어떻게 됐어?")
    assert created == []
    assert [c.url.path for c in calls] == ["/api/ai/extract"]


def test_duplicate_proposal_is_not_reported():
    def api(request):
        if request.url.path == "/api/ai/extract":
            return httpx.Response(200, json={"events": [EVENT]})
        return httpx.Response(409, json={"detail": "duplicate"})

    created, _ = run_with(api, "월요일 2시에 회의하자")
    assert created == []


def test_create_proposal_status():
    async def go():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(normal_api), base_url="http://api:8000"
        ) as http:
            return await create_proposal(http, {"external_id": "discord-1"})

    assert asyncio.run(go()) == "pending"

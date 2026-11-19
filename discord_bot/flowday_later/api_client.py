"""api 컨테이너(http://api:8000) 호출 함수 모음 (명세서 3장 API 계약 그대로).

- POST /api/ai/extract   : 메시지 → 일정 후보 추출 (정혁 담당 API)
- POST /api/proposals    : 후보 등록 (김도아 담당 API). 확정 일정 API(/api/events)는 절대 부르지 않는다.

모든 함수는 httpx.AsyncClient를 받는다. 테스트에서는 가짜(MockTransport) 클라이언트를 넣는다.
"""
from datetime import datetime

import httpx

from filter import is_schedule_message


def make_external_id(message_id: int, index: int = 0) -> str:
    """같은 디스코드 메시지의 중복 등록을 막는 값.

    메시지 하나에서 일정이 여러 개 나오면 두 번째부터 '-1', '-2'를 붙인다.
    예) discord-123456  /  discord-123456-1
    """
    base = f"discord-{message_id}"
    return base if index == 0 else f"{base}-{index}"


def is_valid_event(event: dict) -> bool:
    """계약에 맞는 일정인지 확인 (title, start_at, end_at 필수, 시간은 ISO 8601)."""
    try:
        if not event.get("title"):
            return False
        datetime.fromisoformat(event["start_at"])
        datetime.fromisoformat(event["end_at"])
        return True
    except (KeyError, TypeError, ValueError):
        return False


def format_when(event: dict) -> str:
    """'11/09 14:00' 형태의 표시용 문자열."""
    return datetime.fromisoformat(event["start_at"]).strftime("%m/%d %H:%M")


def build_proposal_payload(event: dict, original_text: str, external_id: str) -> dict:
    """POST /api/proposals 요청 본문 (3.1장 'Discord 후보 생성 예시' 그대로)."""
    return {
        "title": event["title"],
        "start_at": event["start_at"],
        "end_at": event["end_at"],
        "source": "discord",
        "original_text": original_text,
        "external_id": external_id,
    }


async def extract_events(http: httpx.AsyncClient, text: str, base_date: str) -> list[dict]:
    """POST /api/ai/extract → {"events": [...]} 의 events 배열. 일정이 없으면 []."""
    res = await http.post("/api/ai/extract", json={"text": text, "base_date": base_date, "suggest_if_uncertain": True})
    res.raise_for_status()
    return res.json().get("events", [])


async def create_proposal(http: httpx.AsyncClient, payload: dict) -> str:
    """POST /api/proposals. 결과: 'pending'(새로 등록) | 'duplicate'(이미 있음)."""
    res = await http.post("/api/proposals", json=payload)
    if res.status_code == 409:  # external_id 중복. 김도아가 다른 코드로 주면 협의 필요
        return "duplicate"
    res.raise_for_status()
    return res.json().get("status", "pending")


async def process_message(
    http: httpx.AsyncClient, content: str, message_id: int, base_date: str
) -> list[str]:
    """메시지 하나를 처리하고, 새로 만든 후보의 표시 문자열 목록을 돌려준다.

    1) 일정 얘기가 아니면 아무것도 부르지 않고 [] (AI 호출 비용 절약)
    2) /api/ai/extract 로 일정 추출 (없으면 [])
    3) 일정마다 /api/proposals 로 후보만 등록
    """
    if not is_schedule_message(content):
        return []

    events = [e for e in await extract_events(http, content, base_date) if is_valid_event(e)]

    created = []
    for index, event in enumerate(events):
        payload = build_proposal_payload(event, content, make_external_id(message_id, index))
        if await create_proposal(http, payload) == "pending":
            created.append(f"{event['title']} ({format_when(event)})")
    return created

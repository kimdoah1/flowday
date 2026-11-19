"""POST /api/ai/extract — 공통 일정 추출 API (담당: 정혁)

가이드 3장 계약
  요청: {"text": "다음 주 월요일 오후 2시에 회의하자", "base_date": "2026-11-07"}
  응답: {"events": [{"title": "회의", "start_at": "...+09:00", "end_at": "...+09:00"}]}
일정이 없거나 날짜가 불확실하면 {"events": []}.
Discord 봇(정세린)과 회의 화면(박수현)이 같은 API를 쓴다.
"""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.meeting_ai import extract_events, today_kst

# 팀 main.py 가 app.include_router(extract.router, prefix="/api") 로 등록한다.
# → 실제 주소는 /api/ai/extract
router = APIRouter(prefix="/ai", tags=["일정 추출 (정혁)"])


class ExtractRequest(BaseModel):
    text: str = Field(examples=["다음 주 월요일 오후 2시에 회의하자"])
    suggest_if_uncertain: bool = False
    base_date: date | None = Field(
        default=None,
        description="상대 날짜('내일', '다음 주')를 계산할 기준 날짜. 없으면 오늘(한국 시간).",
        examples=["2026-11-07"],
    )


class ExtractedEvent(BaseModel):
    title: str
    start_at: str
    end_at: str


class ExtractResponse(BaseModel):
    events: list[ExtractedEvent]


@router.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest) -> ExtractResponse:
    events = extract_events(req.text, req.base_date or today_kst())
    if not events and req.suggest_if_uncertain:
        from app.schedule_suggestion import period, suggest
        from app.db import connect
        base = req.base_date or today_kst()
        if period(req.text, base):
            with connect() as conn:
                busy = conn.execute("SELECT start_at, end_at FROM events UNION ALL SELECT start_at, end_at FROM proposals WHERE status='pending'").fetchall()
            events = suggest(req.text, base, busy)
    return ExtractResponse(events=events)

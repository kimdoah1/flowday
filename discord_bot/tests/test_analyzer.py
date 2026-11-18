"""AI를 부르지 않고 가짜 클라이언트로 analyzer·report를 검증한다."""
import asyncio
from datetime import datetime
from types import SimpleNamespace

from analyzer import ChatLine, analyze, build_transcript, calendar_hint, parse_analysis
from llm import LLMError, parse_json
from report import build_reply, split_message
from scheduler import KST
from validator import finalize

NOW = datetime(2026, 11, 7, 15, 30, tzinfo=KST)

DATA = {
    "summary": ["다음 주 팀 회의 시간 조율 중"],
    "decided_events": [{"title": "발표 리허설", "start_at": "2026-11-12T10:00:00+09:00",
                        "end_at": "2026-11-12T11:00:00+09:00"}],
    "duration_minutes": 60,
    "search_start": "2026-11-09",
    "search_end": "2026-11-10",
    "people": [
        {"name": "민수", "available": [{"start_at": "2026-11-09T14:00:00+09:00",
                                        "end_at": "2026-11-09T18:00:00+09:00"}]},
        {"name": "지민", "unavailable": [{"start_at": "2026-11-09T09:00:00+09:00",
                                          "end_at": "2026-11-09T16:00:00+09:00"}]},
        {"name": "깨진데이터", "available": [{"start_at": "이상한값"}]},
    ],
}


class FakeLLM:
    """Gemini 대신 미리 정한 JSON을 돌려주는 가짜 LLM."""

    def __init__(self):
        self.kwargs = None

    async def extract(self, **kwargs):
        self.kwargs = kwargs
        return DATA


def test_analyze_with_fake_llm():
    fake = FakeLLM()
    result = asyncio.run(analyze(fake, "test-model", "[11/07 15:00] 민수: 월요일 오후 돼요", "", NOW))
    assert fake.kwargs["model"] == "test-model" and "날짜표" in fake.kwargs["user"]
    assert [p.name for p in result.people] == ["민수", "지민", "깨진데이터"]
    assert result.people[2].has_info is False  # 형식이 깨진 항목은 버려진다


def test_calendar_hint():
    hint = calendar_hint(NOW, days=3)
    assert hint == "2026-11-07(토), 2026-11-08(일), 2026-11-09(월)"


def test_parse_json_tolerates_noise():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('결과입니다:\n{"a": 1}\n끝') == {"a": 1}
    try:
        parse_json("JSON 아님")
        assert False
    except LLMError:
        pass


def test_empty_strings_use_defaults():
    a = parse_analysis({"summary": [], "decided_events": [{"title": "x", "start_at": "2026-11-12T10:00:00+09:00", "end_at": ""}],
                        "search_start": "", "search_end": "", "people": []}, NOW)
    assert a.search_start == NOW.date() and a.decided[0][2] is None


def test_full_reply():
    result = finalize(parse_analysis(DATA, NOW), NOW)
    text = build_reply(result, ["민수", "지민", "철수"])
    assert "발표 리허설" in text                       # 확정 일정
    assert "민수 — 가능 11/9(월) 14:00~18:00" in text  # 사람별 정리(계산에 쓴 데이터 그대로)
    assert "2명 모두 가능한 시간" in text and "11/9(월) 16:00~18:00" in text
    assert "철수" in text                              # 아직 말하지 않은 사람


def test_conflict_shown_instead_of_confirmed():
    data = {**DATA, "decided_events": [{"title": "팀 회의", "start_at": "2026-11-09T14:00:00+09:00",
                                        "end_at": "2026-11-09T15:00:00+09:00"}]}
    result = finalize(parse_analysis(data, NOW), NOW)
    text = build_reply(result, ["민수", "지민"])
    assert "확인이 필요한 일정" in text and "✅" not in text  # 지민이 불가라고 한 시간이라 확정으로 안 나온다


def test_reset_note_and_all_day_format():
    data = {"summary": [], "decided_events": [], "people": [
        {"name": "A", "unavailable": [{"start_at": "2026-11-13T00:00:00+09:00", "end_at": "2026-11-14T00:00:00+09:00"}]},
        {"name": "B", "unavailable": []}]}
    # B는 정보가 없으므로 1명만 계산 불가 안내
    text = build_reply(finalize(parse_analysis(data, NOW), NOW), ["A", "B"], since=NOW)
    assert "11/13(금) 종일" in text and "초기화" in text


def test_nothing_found():
    result = finalize(parse_analysis({"summary": [], "decided_events": [], "people": []}, NOW), NOW)
    assert "찾지 못했어요" in build_reply(result, [])


def test_transcript_normalizes_times():
    text, _ = build_transcript([ChatLine(NOW, "민수", "오후 2시 또는 2PM, 14시 가능")])
    assert text.count("14:00") == 3


def test_build_transcript_truncates_old_lines():
    lines = [ChatLine(NOW, f"u{i}", "가" * 50) for i in range(100)]
    text, authors = build_transcript(lines, max_chars=1000)
    assert len(text) < 1500 and authors[-1] == "u99" and "u0" not in authors


def test_split_message():
    chunks = split_message("\n".join(["줄" * 100] * 50), limit=1900)
    assert all(len(c) <= 1900 for c in chunks) and len(chunks) > 1

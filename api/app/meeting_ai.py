"""회의 분석 · 공통 일정 추출 로직 (담당: 정혁)

Flowday 가이드 3장 API 계약을 따른다.
- extract_events(): 자연어 문장에서 일정을 찾아 [{"title", "start_at", "end_at"}] 목록으로 돌려준다.
- summarize_meeting(): 회의 텍스트를 짧게 요약한다.
- analyze_meeting_text(): 요약 + 일정 후보를 한 번에 만든다.

AI(LLM) 사용 규칙 — 팀 LLM 은 Gemini
- GEMINI_API_KEY 와 LLM_MODEL 이 설정되어 있으면 Gemini 를 쓴다.
  호출은 팀 공통 함수 app/llm.py 의 ask_llm(prompt, output_model) (김도아 담당)을 거친다.
  그 파일이 아직 없을 때(단독 실행)는 같은 방식으로 동작하는 이 파일 안의 대체 함수를 쓴다.
- 키가 없거나 "test"이면, 또는 LLM_MODE=rule 이면 규칙 기반(정규식) 분석으로 동작한다.
  → API 키 없이도 단독 테스트와 GitHub Actions 테스트가 가능하다.
- LLM 호출이 실패해도 규칙 기반 결과로 대신해서 서버가 멈추지 않게 한다.

날짜·시간 규칙 (가이드: "불확실한 날짜를 임의로 확정하지 않는다")
- 날짜를 확정할 수 없으면 그 일정은 버린다. 일정이 하나도 없으면 [] 를 돌려준다.
- 시각이 있으면 종료 시각이 없을 때 시작 + 1시간으로 둔다.
- 날짜만 있고 시각이 없으면 하루 종일 일정(그날 00:00 ~ 다음 날 00:00)으로 둔다.  ※ 팀 확인 필요
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
WEEKDAYS = "월화수목금토일"  # date.weekday(): 월=0 ... 일=6

# 제목에 쓸 일정 이름 단어. 문장에 있으면 "팀 회의"처럼 앞 단어와 붙여 제목으로 쓴다.
SCHEDULE_WORDS = [
    "회의", "미팅", "마감", "제출", "발표", "리허설", "모임", "스터디", "면담",
    "시험", "약속", "회식", "통합", "점검", "데모", "세미나", "수업", "과제",
]
# 일정 단서. 원본 Flowday HTML 의 회의록·채팅 분석 규칙과 같은 단어를 쓴다.
# 날짜와 함께 이 단어(또는 시각)가 있어야 일정으로 본다.
SCHEDULE_HINTS = (
    "회의", "까지", "예정", "마감", "완료", "공유", "진행", "리뷰", "점검", "제출",
    "일정", "하기로", "부탁",
)
# "결정: ..." 처럼 회의록 줄 앞에 붙는 머리말
_LINE_PREFIX = re.compile(r"^\s*(결정|회의|일정|액션|할\s*일|TODO)\s*[:：]\s*", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 공통: 결과 만들기
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    """2026-11-09T14:00:00+09:00 형식 문자열."""
    return dt.astimezone(KST).isoformat(timespec="seconds")


def _make_event(title: str, day: date, start: time | None, end: time | None = None) -> dict:
    """계약 형식의 일정 하나를 만든다."""
    if start is None:  # 날짜만 있음 → 하루 종일
        start_dt = datetime.combine(day, time(0, 0), KST)
        end_dt = start_dt + timedelta(days=1)
    else:
        start_dt = datetime.combine(day, start, KST)
        end_dt = datetime.combine(day, end, KST) if end else start_dt + timedelta(hours=1)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
    return {"title": title.strip() or "일정", "start_at": _iso(start_dt), "end_at": _iso(end_dt)}


def _dedupe(events: list[dict]) -> list[dict]:
    seen, result = set(), []
    for e in events:
        key = (e["title"], e["start_at"])
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"[\n.!?。]+|(?<=[다요자죠])\s+(?=\S)", text)
    return [p.strip() for p in parts if p and p.strip()]


def _split_clauses(sentence: str) -> list[str]:
    """'화요일에 회의 준비하고 목요일에 제출해' → 두 절. 일정 추출에만 쓴다."""
    parts = re.split(r"(?<=[고며])\s+|,\s*", sentence)
    return [p.strip() for p in parts if p and p.strip()]


# ---------------------------------------------------------------------------
# 규칙 기반 분석 (API 키 없이 동작)
# ---------------------------------------------------------------------------

_DATE_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_DATE_MD = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_DATE_SLASH = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])")
_DATE_REL = re.compile(r"(오늘|내일|모레|글피)")
_DATE_WEEK = re.compile(r"(이번\s*주|다음\s*주|다다음\s*주)?\s*([월화수목금토일])요일")
_TIME_KO = re.compile(r"(오전|오후|아침|낮|저녁|밤|새벽)?\s*(\d{1,2})\s*시\s*(반|(\d{1,2})\s*분)?")
_TIME_COLON = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")


def _find_date(sentence: str, base: date) -> date | None:
    """문장에서 날짜를 찾는다. 확실하지 않으면 None."""
    m = _DATE_ISO.search(sentence)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None

    m = _DATE_MD.search(sentence) or _DATE_SLASH.search(sentence)
    if m:
        try:
            d = date(base.year, int(m[1]), int(m[2]))
        except ValueError:
            return None
        # 기준일보다 한참 전이면 내년으로 본다 (예: 12월에 "1월 5일")
        if d < base - timedelta(days=60):
            d = date(base.year + 1, d.month, d.day)
        return d

    m = _DATE_REL.search(sentence)
    if m:
        return base + timedelta(days={"오늘": 0, "내일": 1, "모레": 2, "글피": 3}[m[1]])

    m = _DATE_WEEK.search(sentence)
    if m:
        target = WEEKDAYS.index(m[2])
        week_word = re.sub(r"\s", "", m[1] or "")
        monday = base - timedelta(days=base.weekday())
        if week_word == "이번주":
            return monday + timedelta(days=target)
        if week_word == "다음주":
            return monday + timedelta(days=7 + target)
        if week_word == "다다음주":
            return monday + timedelta(days=14 + target)
        # "금요일"처럼 주 표현이 없으면 기준일 이후 가장 가까운 그 요일 (오늘 포함)
        return base + timedelta(days=(target - base.weekday()) % 7)

    return None


def _find_times(sentence: str) -> list[time]:
    """문장에서 시각을 순서대로 찾는다 (최대 2개: 시작, 종료)."""
    found: list[tuple[int, time]] = []
    for m in _TIME_KO.finditer(sentence):
        ampm, hour = m[1], int(m[2])
        minute = 30 if m[3] == "반" else int(m[4] or 0)
        if hour > 24 or minute > 59:
            continue
        if ampm in ("오후", "저녁", "밤") and hour < 12:
            hour += 12
        elif ampm == "낮" and hour < 6:
            hour += 12
        elif ampm is None and 1 <= hour <= 7:
            # "2시 회의"처럼 오전/오후가 없고 1~7시면 보통 오후를 뜻한다.
            hour += 12
        if hour == 24:
            hour = 0
        found.append((m.start(), time(hour, minute)))
    for m in _TIME_COLON.finditer(sentence):
        found.append((m.start(), time(int(m[1]), int(m[2]))))
    found.sort(key=lambda x: x[0])
    return [t for _, t in found[:2]]


_TITLE_NOISE = re.compile(
    r"(오늘|내일|모레|글피|이번\s*주|다음\s*주|다다음\s*주|[월화수목금토일]요일|"
    r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s*월\s*\d{1,2}\s*일|\d{1,2}/\d{1,2}|"
    r"(오전|오후|아침|낮|저녁|밤|새벽)|\d{1,2}\s*시\s*(반|\d{1,2}\s*분)?|\d{1,2}:\d{2}|"
    r"쯤|정도)"
)
# 단어 끝에 붙은 조사만 지운다 (단어 중간의 글자는 건드리지 않음)
_PARTICLE = re.compile(r"(부터|까지|에서|에|은|는|이|가|을|를|의)(?=\s|$)")


# 문장 끝 서술어 (제목에서 뺀다)
_VERB_ENDING = re.compile(
    r"\s*(을|를)?\s*(하기로\s*(했다|함|하자)|할게요|하겠습니다|합시다|해\s*주세요|해주세요|부탁해요|부탁합니다|"
    r"한다|하자|해요|합니다|예정입니다|예정|입니다|이다|다)\s*$"
)


def _guess_title(sentence: str) -> str | None:
    """'금요일 오후 2시에 팀 회의' → '팀 회의'.
    일정 이름 단어가 없으면 '프론트엔드 시안은 11월 12일까지 완료한다' → '프론트엔드 시안 완료' 처럼
    날짜·시각·조사·서술어를 뺀 나머지를 제목으로 쓴다. 남는 글자가 없으면 None."""
    for word in SCHEDULE_WORDS:
        idx = sentence.find(word)
        if idx == -1:
            continue
        before = _PARTICLE.sub("", _TITLE_NOISE.sub(" ", sentence[:idx])).split()
        # 일정 단어 바로 앞 단어 하나만 붙인다 (예: "팀", "API 통합")
        prefix = before[-1] if before and len(before[-1]) <= 6 else ""
        return f"{prefix} {word}".strip()

    rest = _VERB_ENDING.sub("", sentence)
    rest = _PARTICLE.sub("", _TITLE_NOISE.sub(" ", rest))
    rest = re.sub(r"\s+", " ", rest).strip(" ,.")
    return rest[:30] or None


# "논의했다", "끝났습니다"처럼 이미 지난 일을 말하는 문장 끝
_PAST_TENSE = re.compile(r"(했|었|았|였|났|웠)(다|어|어요|습니다|음)?\s*$")


def _rule_extract(text: str, base: date) -> list[dict]:
    events = []
    clauses = [c for s in _split_sentences(text) for c in _split_clauses(s)]
    for sentence in clauses:
        if _PAST_TENSE.search(sentence):
            continue  # 지난 일은 일정이 아니다
        sentence = _LINE_PREFIX.sub("", sentence)
        day = _find_date(sentence, base)
        if day is None:
            continue  # 날짜를 모르면 만들지 않는다
        times = _find_times(sentence)
        has_hint = any(h in sentence for h in SCHEDULE_HINTS) or any(w in sentence for w in SCHEDULE_WORDS)
        if not has_hint and not times:
            continue  # 날짜만 있고 일정 단서가 없으면 일정이 아니라고 본다
        title = _guess_title(sentence)
        events.append(_make_event(title or "일정", day, times[0] if times else None,
                                  times[1] if len(times) > 1 else None))
    return _dedupe(events)


_DECISION_HINTS = ("하기로", "결정", "정했", "정함", "합시다", "하자", "까지", "담당", "맡")


def _rule_summary(transcript: str) -> str:
    sentences = _split_sentences(transcript)
    if not sentences:
        return ""
    picked = [sentences[0]]
    for s in sentences[1:]:
        if any(h in s for h in _DECISION_HINTS) and s not in picked:
            picked.append(s)
        if len(picked) >= 4:
            break
    return " / ".join(picked)


# ---------------------------------------------------------------------------
# LLM 분석 (Gemini — GEMINI_API_KEY 와 LLM_MODEL 이 있을 때)
# ---------------------------------------------------------------------------

class _LLMEvent(BaseModel):
    title: str = Field(description="짧은 일정 제목. 예: 팀 회의")
    date: str | None = Field(description="YYYY-MM-DD. 확실하지 않으면 null")
    start_time: str | None = Field(description="HH:MM (24시간). 언급이 없으면 null")
    end_time: str | None = Field(description="HH:MM (24시간). 언급이 없으면 null")


class _LLMEvents(BaseModel):
    events: list[_LLMEvent]


class _LLMSummary(BaseModel):
    summary: str = Field(description="회의 요약. 핵심 논의, 결정 사항, 할 일을 3~5문장으로")


def _llm_enabled() -> bool:
    if os.getenv("LLM_MODE", "auto").lower() == "rule":
        return False
    key = os.getenv("GEMINI_API_KEY", "")
    return bool(key) and key != "test" and bool(os.getenv("LLM_MODEL"))


def _fallback_ask_llm(prompt: str, output_model):
    """팀 app/llm.py 가 없을 때 쓰는 대체 함수. 팀 ask_llm 과 같은 방식(Gemini + 구조화 출력)."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=os.environ["LLM_MODEL"],
        google_api_key=os.environ["GEMINI_API_KEY"],
        temperature=0,
    )
    return llm.with_structured_output(output_model, method="json_schema").invoke(prompt)


def _ask_llm(prompt: str, output_model):
    """질문(prompt)을 보내고 output_model(Pydantic) 형식으로 답을 받는다."""
    try:
        from app.llm import ask_llm  # 팀 공통 함수 (김도아, Gemini)
    except ImportError:
        ask_llm = _fallback_ask_llm
    return ask_llm(prompt, output_model)


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return None
    return time(int(m[1]), int(m[2]))


def _llm_extract(text: str, base: date) -> list[dict]:
    prompt = (
        "다음 한국어 글에서 캘린더에 넣을 일정을 찾아라.\n"
        f"기준 날짜: {base.isoformat()} ({WEEKDAYS[base.weekday()]}요일), 시간대: Asia/Seoul\n"
        "규칙:\n"
        "- '다음 주 월요일' 같은 상대 날짜는 기준 날짜로 계산해 YYYY-MM-DD 로 바꾼다.\n"
        "- 날짜를 확실히 알 수 없으면 date 를 null 로 둔다. 추측해서 만들지 않는다.\n"
        "- 시각이 언급되지 않았으면 start_time 을 null 로 둔다.\n"
        "- 일정이 없으면 events 를 빈 배열로 둔다.\n\n"
        f"글:\n{text}"
    )
    result: _LLMEvents = _ask_llm(prompt, _LLMEvents)
    events = []
    for e in result.events:
        try:
            day = date.fromisoformat(e.date) if e.date else None
        except ValueError:
            day = None
        if day is None:
            continue  # 날짜 불확실 → 버림
        events.append(_make_event(e.title, day, _parse_hhmm(e.start_time), _parse_hhmm(e.end_time)))
    return _dedupe(events)


def _llm_summary(transcript: str) -> str:
    prompt = (
        "다음 회의 내용을 한국어로 요약하라. 핵심 논의, 결정 사항, 할 일을 3~5문장으로 쓴다. "
        "회의에 없는 내용은 쓰지 않는다.\n\n" + transcript
    )
    result: _LLMSummary = _ask_llm(prompt, _LLMSummary)
    return result.summary.strip()


# ---------------------------------------------------------------------------
# 외부에서 쓰는 함수
# ---------------------------------------------------------------------------

def extract_events(text: str, base_date: date) -> list[dict]:
    """자연어 → [{"title", "start_at", "end_at"}]. 일정이 없으면 []."""
    if not text or not text.strip():
        return []
    if _llm_enabled():
        try:
            return _llm_extract(text, base_date)
        except Exception:  # LLM 오류가 나도 서버는 계속 동작
            logger.exception("LLM 일정 추출 실패 → 규칙 기반으로 대신함")
    return _rule_extract(text, base_date)


def summarize_meeting(transcript: str) -> str:
    """회의 텍스트 → 요약 문자열."""
    if not transcript or not transcript.strip():
        return ""
    if _llm_enabled():
        try:
            return _llm_summary(transcript)
        except Exception:
            logger.exception("LLM 요약 실패 → 규칙 기반으로 대신함")
    return _rule_summary(transcript)


def analyze_meeting_text(transcript: str, base_date: date) -> dict:
    """회의 텍스트 → {"summary", "events"}."""
    return {
        "summary": summarize_meeting(transcript),
        "events": extract_events(transcript, base_date),
    }


def today_kst() -> date:
    return datetime.now(KST).date()

"""검증을 거친 결과(Result) → 디스코드 답장 문자열.

사람별 가능/불가 시간은 AI의 문장이 아니라 계산에 쓴 데이터에서 그대로 만들어서,
요약과 계산 결과가 어긋나지 않게 한다.
"""
from datetime import datetime, timedelta

from analyzer import WEEKDAYS
from scheduler import Interval
from validator import Result


def fmt_day(dt: datetime) -> str:
    return f"{dt.month}/{dt.day}({WEEKDAYS[dt.weekday()]})"


def fmt_range(start: datetime, end: datetime | None) -> str:
    if end is None:
        return f"{fmt_day(start)} {start:%H:%M}~"
    midnight = start.hour == start.minute == end.hour == end.minute == 0
    if midnight and end > start:  # 00:00 ~ 다음 날 00:00 → '종일'
        last = end - timedelta(days=1)
        if last.date() == start.date():
            return f"{fmt_day(start)} 종일"
        return f"{fmt_day(start)}~{fmt_day(last)} 종일"
    if start.date() == end.date():
        return f"{fmt_day(start)} {start:%H:%M}~{end:%H:%M}"
    return f"{fmt_day(start)} {start:%H:%M} ~ {fmt_day(end)} {end:%H:%M}"


def fmt_ranges(intervals: list[Interval], limit: int = 3) -> str:
    text = ", ".join(fmt_range(s, e) for s, e in intervals[:limit])
    extra = len(intervals) - limit
    return text + (f" 외 {extra}건" if extra > 0 else "")


def build_reply(result: Result, authors: list[str], since: datetime | None = None) -> str:
    a = result.analysis
    parts: list[str] = []

    if a.summary:
        parts.append("📋 **대화 요약**\n" + "\n".join(f"• {s}" for s in a.summary))

    if a.decided:
        parts.append("✅ **확정된 일정**\n" + "\n".join(
            f"• {title} — {fmt_range(s, e)}" for title, s, e in a.decided))

    if result.conflicts:
        parts.append("⚠️ **확인이 필요한 일정** (불가능하다고 말한 사람이 있어요)\n" + "\n".join(
            f"• {c.title} — {fmt_range(c.start, c.end)} · 어려운 사람: {', '.join(c.who)}"
            for c in result.conflicts))

    informed = [p for p in a.people if p.has_info]
    if informed:
        lines = []
        for p in informed:
            bits = []
            if p.available:
                bits.append("가능 " + fmt_ranges(p.available))
            if p.unavailable:
                bits.append("불가 " + fmt_ranges(p.unavailable))
            lines.append(f"• {p.name} — " + " / ".join(bits))
        parts.append("👥 **사람별 정리** (이 데이터로 계산했어요)\n" + "\n".join(lines))

    n = len(informed)
    if n >= 2:
        period = f"{a.search_start.month}/{a.search_start.day}~{a.search_end.month}/{a.search_end.day}"
        note = f"_(기간 {period}, 09:00~22:00, {a.duration_minutes}분 이상 기준)_"
        if result.everyone:
            body = "\n".join(f"• {fmt_range(s.start, s.end)}" for s in result.everyone)
            parts.append(f"🕒 **{n}명 모두 가능한 시간** {note}\n{body}")
        elif result.partial:
            body = "\n".join(
                f"• {fmt_range(s.start, s.end)} — {len(s.who)}/{n}명 가능 (불가: {', '.join(s.missing)})"
                for s in result.partial)
            parts.append(f"🕒 **{n}명이 모두 겹치는 시간은 없어요.** 가장 많이 가능한 시간:\n{body}")
        else:
            parts.append(f"🕒 **겹치는 시간을 찾지 못했어요.** {note}")
    elif n == 1:
        parts.append(f"🕒 가능 시간을 말한 사람이 {informed[0].name}님뿐이라 겹치는 시간을 계산할 수 없어요.")

    names = {p.name for p in informed}
    silent = [x for x in authors if x not in names]
    if informed and silent:
        parts.append("❓ **가능 시간을 아직 말하지 않은 사람**: " + ", ".join(silent))

    if not parts:
        return "최근 대화에서 일정과 관련된 내용을 찾지 못했어요."

    if result.warnings:
        parts.append("🔎 **검증 메모**\n" + "\n".join(f"• {w}" for w in result.warnings))
    if since:
        parts.append(f"_※ 마지막 초기화({since:%m/%d %H:%M}) 이후 대화만 분석했어요._")
    return "\n\n".join(parts)


def split_message(text: str, limit: int = 1900) -> list[str]:
    """디스코드 글자 수 제한(2000자)에 맞게 줄 단위로 나눈다."""
    chunks, cur = [], ""
    for line in text.split("\n"):
        line = line[:limit]
        if len(cur) + len(line) + 1 > limit and cur:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks

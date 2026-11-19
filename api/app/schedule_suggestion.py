"""Opt-in suggestions for vague Discord dates; never writes calendar events.

The fallback uses a visible, deterministic policy, not an LLM-generated date:
first free weekday 09:00–18:00, one hour, within the requested period.
"""
import calendar
import re
from datetime import date, datetime, time, timedelta
from app.meeting_ai import KST, _find_times, SCHEDULE_WORDS


def period(text: str, base: date):
    compact = re.sub(r'\s+', '', text)
    if '다음달' in compact:
        month = base.month % 12 + 1
        year = base.year + (base.month == 12)
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    if '이번달' in compact or '월말' in compact:
        return base, date(base.year, base.month, calendar.monthrange(base.year, base.month)[1])
    if '내년' in compact:
        return date(base.year + 1, 1, 1), date(base.year + 1, 12, 31)
    if any(word in compact for word in ['올해', '이번해', '연말']):
        return base, date(base.year, 12, 31)
    return None


def suggest(text: str, base: date, busy: list[dict], now: datetime | None = None):
    bounds = period(text, base)
    if not bounds or not any(word in text for word in SCHEDULE_WORDS + ['여행', '프로젝트']):
        return []
    # Do not overwrite explicit dates, constraints, deadlines, cancellations or recurrence.
    if re.search(r'\d+\s*(년|월|일)|요일|주말|주마다|매주|매일|취소|말자|안\s*해|말일|마지막|마감|제출|완료|끝내|까지|오전|오후|저녁|밤|아침|새벽|\d+\s*시간', text) or _find_times(text):
        return []
    now = now or datetime.now(KST)
    start, last = bounds
    day = max(start, now.astimezone(KST).date())
    intervals = []
    for item in busy:
        a, b = item['start_at'], item['end_at']
        intervals.append((datetime.fromisoformat(a) if isinstance(a, str) else a,
                          datetime.fromisoformat(b) if isinstance(b, str) else b))
    while day <= last:
        if day.weekday() < 5:
            slot = datetime.combine(day, time(9), KST)
            limit = datetime.combine(day, time(18), KST)
            while slot + timedelta(hours=1) <= limit:
                end = slot + timedelta(hours=1)
                if slot >= now and not any(slot < b and end > a for a, b in intervals):
                    return [{'title': '[시간 추천] ' + text.strip()[:100],
                             'start_at': slot.isoformat(), 'end_at': end.isoformat()}]
                slot += timedelta(minutes=30)
        day += timedelta(days=1)
    return []

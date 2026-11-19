from datetime import date, datetime
from app.meeting_ai import KST, _find_date
from app.schedule_suggestion import period, suggest


def test_relative_calendar_dates():
    base = date(2026, 12, 20)
    assert _find_date('다음 달 25일 회의', base) == date(2027, 1, 25)
    assert _find_date('올해 1월 5일 회의', base) == date(2026, 1, 5)
    assert _find_date('이번 달 마지막 날 제출', base) == date(2026, 12, 31)
    assert _find_date('내년 마지막 날까지 완료', base) == date(2027, 12, 31)
    assert _find_date('이번 달 31일 회의', date(2026, 2, 1)) is None
    assert period('다음 달 회의', base) == (date(2027, 1, 1), date(2027, 1, 31))


def test_suggestion_skips_busy_and_past_and_keeps_period():
    now = datetime(2026, 11, 20, 9, 0, tzinfo=KST)
    busy = [{'start_at': '2026-11-20T09:00:00+09:00', 'end_at': '2026-11-20T11:00:00+09:00'}]
    result = suggest('이번 달에 회의하자', now.date(), busy, now)
    assert result[0]['start_at'] == '2026-11-20T11:00:00+09:00'
    assert result[0]['title'].startswith('[시간 추천]')
    assert suggest('이번 달에 회의하자', now.date(), [], datetime(2026, 12, 1, tzinfo=KST)) == []


def test_no_suggestions_for_explicit_dates_or_unsupported_constraints():
    base = date(2026, 11, 20)
    for text in ['이번 달 25일 회의', '이번 달 회의 취소', '올해 날씨 좋다', '이번 달 오후 3시 회의', '올해 안에 프로젝트 끝내자', '이번 달 주말 회의']:
        assert suggest(text, base, []) == []


def test_weekend_and_all_day_busy_are_skipped():
    now = datetime(2026, 11, 20, 18, 0, tzinfo=KST)
    busy = [{'start_at': '2026-11-23T00:00:00+09:00', 'end_at': '2026-11-24T00:00:00+09:00'}]
    assert suggest('올해 회의하자', now.date(), busy, now)[0]['start_at'] == '2026-11-24T09:00:00+09:00'

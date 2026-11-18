from datetime import date, datetime

from scheduler import KST, Person, find_slots, merge, subtract


def t(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=KST)


def test_merge_and_subtract():
    assert merge([(t(9, 9), t(9, 12)), (t(9, 11), t(9, 14))]) == [(t(9, 9), t(9, 14))]
    assert subtract([(t(9, 9), t(9, 18))], [(t(9, 12), t(9, 13))]) == [
        (t(9, 9), t(9, 12)), (t(9, 13), t(9, 18))
    ]


def test_everyone_free_slot():
    # A는 월요일 14~18시만 가능, B는 월요일 9~15시 불가 → 15~18시가 겹친다
    a = Person("A", available=[(t(9, 14), t(9, 18))])
    b = Person("B", unavailable=[(t(9, 9), t(9, 15))])
    everyone, partial = find_slots([a, b], date(2026, 11, 9), date(2026, 11, 9), 60)
    assert [(s.start, s.end) for s in everyone] == [(t(9, 15), t(9, 18))]
    assert partial == []


def test_no_overlap_returns_partial():
    a = Person("A", available=[(t(9, 9), t(9, 12))])
    b = Person("B", available=[(t(9, 13), t(9, 18))])
    c = Person("C", available=[(t(9, 9), t(9, 12))])
    everyone, partial = find_slots([a, b, c], date(2026, 11, 9), date(2026, 11, 9), 60)
    assert everyone == []
    assert partial and partial[0].who == ["A", "C"] and partial[0].missing == ["B"]


def test_duration_filter():
    a = Person("A", available=[(t(9, 14), t(9, 14, 30))])
    b = Person("B", available=[(t(9, 14), t(9, 15))])
    everyone, _ = find_slots([a, b], date(2026, 11, 9), date(2026, 11, 9), 60)
    assert everyone == []


def test_people_without_info_are_ignored():
    a = Person("A", unavailable=[(t(9, 9), t(9, 12))])
    silent = Person("Z")  # 가능 시간을 말하지 않음
    assert find_slots([a, silent], date(2026, 11, 9), date(2026, 11, 9)) == ([], [])


def test_past_times_excluded():
    a = Person("A", unavailable=[(t(9, 0), t(9, 1))])
    b = Person("B", unavailable=[(t(9, 0), t(9, 1))])
    everyone, _ = find_slots([a, b], date(2026, 11, 9), date(2026, 11, 9), 60, not_before=t(9, 20))
    assert everyone[0].start == t(9, 20)

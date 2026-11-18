from datetime import date, datetime

from analyzer import Analysis
from scheduler import KST, Person, Slot
from validator import finalize, verify_slots

NOW = datetime(2026, 11, 7, 15, 30, tzinfo=KST)


def t(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=KST)


def make(people, decided=(), start=date(2026, 11, 9), end=date(2026, 11, 10)):
    return Analysis(summary=[], decided=list(decided), duration_minutes=60,
                    search_start=start, search_end=end, people=people)


def test_decided_event_conflicting_with_unavailable_is_separated():
    # 지민이 월요일 9~16시는 안 된다고 했는데 14시 회의가 '확정'으로 나온 경우 (피드백 2-3)
    people = [Person("민수", available=[(t(9, 14), t(9, 18))]),
              Person("지민", unavailable=[(t(9, 9), t(9, 16))])]
    r = finalize(make(people, [("팀 회의", t(9, 14), t(9, 15))]), NOW)
    assert r.analysis.decided == []
    assert len(r.conflicts) == 1 and r.conflicts[0].who == ["지민"]


def test_clean_decided_event_stays():
    people = [Person("민수", unavailable=[(t(9, 9), t(9, 12))])]
    r = finalize(make(people, [("회의", t(9, 14), t(9, 15))]), NOW)
    assert len(r.analysis.decided) == 1 and r.conflicts == []


def test_past_and_duplicate_events_removed():
    events = [("지난 회의", t(5, 10), t(5, 11)),
              ("회의", t(9, 14), None), ("회의", t(9, 14), None)]
    r = finalize(make([], events), NOW)
    assert [e[0] for e in r.analysis.decided] == ["회의"]


def test_available_only_checked_inside_search_range():
    # 민수는 11/9~10 중 월요일 오후만 가능. 11/12 확정 일정은 다른 모임일 수 있으니 충돌로 보지 않는다
    people = [Person("민수", available=[(t(9, 14), t(9, 18))])]
    r = finalize(make(people, [("발표 리허설", t(12, 10), t(12, 11))]), NOW)
    assert len(r.analysis.decided) == 1 and r.conflicts == []


def test_inverted_interval_dropped_with_warning():
    people = [Person("A", unavailable=[(t(9, 12), t(9, 10))]),
              Person("B", unavailable=[(t(9, 9), t(9, 10))])]
    r = finalize(make(people), NOW)
    assert any("시작이 끝보다 늦은" in w for w in r.warnings)


def test_available_unavailable_overlap_warns_and_unavailable_wins():
    people = [Person("A", available=[(t(9, 14), t(9, 18))], unavailable=[(t(9, 14), t(9, 16))]),
              Person("B", available=[(t(9, 14), t(9, 18))])]
    r = finalize(make(people), NOW)
    assert any("불가 시간을 우선" in w for w in r.warnings)
    assert [(s.start, s.end) for s in r.everyone] == [(t(9, 16), t(9, 18))]


def test_stale_search_range_reset():
    r = finalize(make([], start=date(2025, 1, 1), end=date(2025, 1, 7)), NOW)
    assert r.analysis.search_start == NOW.date()
    assert any("이미 지나서" in w for w in r.warnings)


def test_verify_slots_drops_inconsistent_result():
    a = Person("A", unavailable=[(t(9, 14), t(9, 16))])
    bad = Slot(t(9, 14), t(9, 15), ["A"], [])
    good = Slot(t(9, 17), t(9, 18), ["A"], [])
    assert verify_slots([bad, good], [a]) == [good]

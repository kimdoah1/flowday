"""AI가 뽑은 정보를 계산 전에 검증하고, 계산 결과를 다시 한 번 확인한다.

- 시간 형식·순서 확인 (시작 < 끝), 중복·겹침 정리
- 이미 지난 확정 일정 제거
- 확정 일정이 누군가의 '불가능한 시간'과 겹치면 확정 목록에서 빼고 '확인 필요'로 분리
- 계산된 '모두 가능한 시간'을 사람별 데이터로 다시 검증 (불일치하면 제외)
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from analyzer import Analysis
from scheduler import KST, Interval, Person, Slot, find_slots, intersect, merge, subtract

DEFAULT_EVENT_LEN = timedelta(hours=1)


@dataclass
class Conflict:
    title: str
    start: datetime
    end: datetime | None
    who: list[str]  # 이 일정에 참석하기 어려운 사람


@dataclass
class Result:
    analysis: Analysis                 # 검증을 거친 분석 결과 (출력도 이 데이터만 쓴다)
    everyone: list[Slot] = field(default_factory=list)
    partial: list[Slot] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _clean(intervals: list[Interval], label: str, warnings: list[str]) -> list[Interval]:
    good = [(s, e) for s, e in intervals if s < e]
    if len(good) != len(intervals):
        warnings.append(f"{label}님의 시간 중 시작이 끝보다 늦은 {len(intervals) - len(good)}개를 무시했어요.")
    return merge(good)  # 중복·겹침은 하나로 합친다


def _unavailable_for(span: Interval, person: Person, in_search_range: bool) -> bool:
    """이 시간(span)에 사람이 참석하기 어려운지. '가능 시간'은 일정을 잡는 기간 안에서만 따진다."""
    if intersect([span], person.unavailable):
        return True
    return in_search_range and bool(person.available) and bool(subtract([span], person.available))


def verify_slots(slots: list[Slot], people: list[Person]) -> list[Slot]:
    """계산된 시간이 사람별 데이터와 실제로 맞는지 다시 확인한다."""
    by_name = {p.name: p for p in people}
    good = []
    for slot in slots:
        span = (slot.start, slot.end)
        if all(
            n in by_name and not _unavailable_for(span, by_name[n], True) for n in slot.who
        ):
            good.append(slot)
    return good


def finalize(analysis: Analysis, now: datetime) -> Result:
    now = now.astimezone(KST)
    warnings: list[str] = []

    # 1) 사람별 시간 정리
    people: list[Person] = []
    for p in analysis.people:
        av = _clean(p.available, p.name, warnings)
        un = _clean(p.unavailable, p.name, warnings)
        if av and un and intersect(av, un):
            warnings.append(f"{p.name}님의 가능·불가 시간이 겹쳐서 불가 시간을 우선했어요.")
        people.append(Person(p.name, av, un))

    # 2) 검색 기간·모임 길이 확인
    start, end = analysis.search_start, analysis.search_end
    today = now.date()
    if end < today:
        warnings.append("분석된 기간이 이미 지나서 오늘부터 7일로 바꿨어요.")
        start, end = today, today + timedelta(days=6)
    if (end - start).days > 30:
        end = start + timedelta(days=30)
        warnings.append("기간이 너무 길어서 30일까지만 계산했어요.")
    duration = min(max(analysis.duration_minutes, 15), 480)

    # 3) 확정 일정 정리 (지난 일정·중복 제거, 끝 시간 확인)
    decided, seen = [], set()
    for title, s, e in analysis.decided:
        if e is not None and e <= s:
            warnings.append(f"'{title}'의 끝 시간이 시작보다 빨라서 끝 시간을 뺐어요.")
            e = None
        if (e or s + DEFAULT_EVENT_LEN) < now or (title.strip(), s) in seen:
            continue
        seen.add((title.strip(), s))
        decided.append((title, s, e))

    # 4) 확정 일정 ↔ 불가능한 시간 충돌 확인
    ok, conflicts = [], []
    for title, s, e in decided:
        span = (s, e or s + DEFAULT_EVENT_LEN)
        in_range = start <= s.date() <= end
        who = [p.name for p in people if p.has_info and _unavailable_for(span, p, in_range)]
        if who:
            conflicts.append(Conflict(title, s, e, who))
        else:
            ok.append((title, s, e))
    for i, (t1, s1, e1) in enumerate(ok):
        for t2, s2, e2 in ok[i + 1:]:
            if intersect([(s1, e1 or s1 + DEFAULT_EVENT_LEN)], [(s2, e2 or s2 + DEFAULT_EVENT_LEN)]):
                warnings.append(f"확정 일정 '{t1}'과 '{t2}'의 시간이 겹쳐요.")

    cleaned = replace(analysis, people=people, decided=ok, search_start=start,
                      search_end=end, duration_minutes=duration)

    # 5) 겹치는 시간 계산 → 결과 재검증
    everyone, partial = find_slots(people, start, end, duration, not_before=now)
    good_everyone, good_partial = verify_slots(everyone, people), verify_slots(partial, people)
    dropped = (len(everyone) - len(good_everyone)) + (len(partial) - len(good_partial))
    if dropped:
        warnings.append(f"계산 결과 {dropped}개가 사람별 분석과 맞지 않아 제외했어요.")

    return Result(cleaned, good_everyone, good_partial, conflicts, warnings)

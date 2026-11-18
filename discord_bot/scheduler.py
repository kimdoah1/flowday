"""사람별 가능/불가 시간 → '모두 가능한 시간'을 계산한다.

AI(LLM)를 쓰지 않는 순수 계산 코드다. 그래서 결과가 항상 같고 테스트하기 쉽다.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DAY_START = time(9, 0)    # 하루 중 일정을 잡아볼 시간대: 09:00 ~ 22:00
DAY_END = time(22, 0)
MAX_SEARCH_DAYS = 31

Interval = tuple[datetime, datetime]


@dataclass
class Person:
    name: str
    available: list[Interval] = field(default_factory=list)    # "이 시간대만 돼요"
    unavailable: list[Interval] = field(default_factory=list)  # "이 시간대는 안 돼요"

    @property
    def has_info(self) -> bool:
        return bool(self.available or self.unavailable)


@dataclass
class Slot:
    start: datetime
    end: datetime
    who: list[str]       # 이 시간에 가능한 사람
    missing: list[str]   # 이 시간에 안 되는 사람


def parse_dt(value: str) -> datetime:
    """ISO 8601 문자열 → 한국 시간 datetime (오프셋이 없으면 한국 시간으로 간주)."""
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=KST) if dt.tzinfo is None else dt.astimezone(KST)


def merge(intervals: list[Interval]) -> list[Interval]:
    """겹치거나 붙어 있는 구간을 하나로 합친다."""
    out: list[Interval] = []
    for s, e in sorted(i for i in intervals if i[0] < i[1]):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def intersect(a: list[Interval], b: list[Interval]) -> list[Interval]:
    """두 구간 목록의 교집합."""
    a, b = merge(a), merge(b)
    res: list[Interval] = []
    i = j = 0
    while i < len(a) and j < len(b):
        s, e = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if s < e:
            res.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return res


def subtract(base: list[Interval], remove: list[Interval]) -> list[Interval]:
    """base에서 remove 구간을 뺀다."""
    result: list[Interval] = []
    remove = merge(remove)
    for s, e in merge(base):
        cur = s
        for rs, re_ in remove:
            if re_ <= cur or rs >= e:
                continue
            if rs > cur:
                result.append((cur, rs))
            cur = max(cur, re_)
            if cur >= e:
                break
        if cur < e:
            result.append((cur, e))
    return result


def day_windows(start_date: date, end_date: date) -> list[Interval]:
    """검색 기간의 날짜별 09:00~22:00 구간."""
    days = min((end_date - start_date).days + 1, MAX_SEARCH_DAYS)
    return [
        (
            datetime.combine(start_date + timedelta(days=d), DAY_START, tzinfo=KST),
            datetime.combine(start_date + timedelta(days=d), DAY_END, tzinfo=KST),
        )
        for d in range(max(days, 0))
    ]


def person_free(person: Person, windows: list[Interval]) -> list[Interval]:
    """한 사람이 가능한 구간. 가능 시간을 말했으면 그 안에서, 아니면 전체에서 불가 시간을 뺀다."""
    free = intersect(person.available, windows) if person.available else list(windows)
    return subtract(free, person.unavailable)


def find_slots(
    people: list[Person],
    search_start: date,
    search_end: date,
    duration_minutes: int = 60,
    not_before: datetime | None = None,
    max_results: int = 5,
) -> tuple[list[Slot], list[Slot]]:
    """(모두 가능한 구간, 모두는 안 될 때의 차선 구간)을 돌려준다.

    가능/불가 정보를 말하지 않은 사람은 계산에서 빼고, 2명 미만이면 계산하지 않는다.
    """
    people = [p for p in people if p.has_info]
    if len(people) < 2:
        return [], []

    windows = day_windows(search_start, search_end)
    if not_before is not None:  # 이미 지난 시간은 제외
        windows = intersect(windows, [(not_before, not_before + timedelta(days=366))])

    free = {p.name: person_free(p, windows) for p in people}
    points = sorted({t for ivs in free.values() for iv in ivs for t in iv})

    # 인접한 두 시각 사이마다 '그 구간에 가능한 사람 집합'을 구하고, 같은 집합이면 이어 붙인다
    segments: list[tuple[datetime, datetime, frozenset[str]]] = []
    for a, b in zip(points, points[1:]):
        who = frozenset(n for n, ivs in free.items() if any(s <= a and b <= e for s, e in ivs))
        if not who:
            continue
        if segments and segments[-1][1] == a and segments[-1][2] == who:
            segments[-1] = (segments[-1][0], b, who)
        else:
            segments.append((a, b, who))

    everyone_set = frozenset(free)
    need = timedelta(minutes=duration_minutes)
    ok = [s for s in segments if s[1] - s[0] >= need]

    def to_slot(seg) -> Slot:
        s, e, who = seg
        return Slot(s, e, sorted(who), sorted(everyone_set - who))

    everyone = [to_slot(s) for s in ok if s[2] == everyone_set][:max_results]
    partial: list[Slot] = []
    if not everyone:
        best = max((len(s[2]) for s in ok), default=0)
        if best >= 2:
            partial = [to_slot(s) for s in ok if len(s[2]) == best][:3]
    return everyone, partial

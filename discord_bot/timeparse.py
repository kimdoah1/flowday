"""시간 표현 정규화 (AI에게 보내기 전에 코드로 통일한다).

  오후 2시 → 14:00      2PM → 14:00       14시 → 14:00      오후 6시 반 → 18:30
  오후 2시~6시 → 14:00~18:00 (뒤쪽 시각은 앞쪽의 오전/오후를 이어받는다)

오전/오후 표시가 없는 경우의 가정: 1~6시는 오후, 7~11시는 오전, 12시는 정오로 본다.
('2시간', '시작'처럼 시각이 아닌 말은 건드리지 않는다)
"""
import re

PERIODS = "오전|오후|아침|새벽|낮|점심|저녁|밤"

_KO = (rf"(?:(?P<p>{PERIODS})\s*)?(?P<h>\d{{1,2}})\s*시(?!간|작)"
       rf"(?:\s*(?:(?P<m>\d{{1,2}})\s*분|(?P<half>반(?!대))))?")
_KOC = rf"(?P<p2>{PERIODS})\s*(?P<h2>\d{{1,2}}):(?P<m2>\d{{2}})"
_EN = r"(?<![\d:A-Za-z])(?P<h3>\d{1,2})(?::(?P<m3>\d{2}))?\s*(?P<ap>[AaPp])\.?[Mm](?![A-Za-z])"

TIME_RE = re.compile(f"{_KOC}|{_KO}|{_EN}")
SEP_RE = re.compile(r"^\s*(?:~|-|–|—|부터|에서|to)\s*$", re.I)


def to_24h(h: int, period: str | None) -> int:
    """시(0~24)와 오전/오후 표시 → 24시간제 시."""
    if period in ("오후", "저녁"):
        return h + 12 if 1 <= h <= 11 else h
    if period == "밤":
        if 6 <= h <= 11:
            return h + 12
        return 24 if h == 12 else h
    if period in ("낮", "점심"):
        return h + 12 if 1 <= h <= 6 else h
    if period in ("오전", "아침", "새벽"):
        return 0 if h == 12 else h
    # 표시가 없을 때
    return h + 12 if 1 <= h <= 6 else h


def normalize_times(text: str) -> str:
    out: list[str] = []
    pos = 0
    prev_end: int | None = None
    prev_period: str | None = None

    for m in TIME_RE.finditer(text):
        g = m.groupdict()
        if g["h2"] is not None:            # 오후 2:30
            h, minute, period = int(g["h2"]), int(g["m2"]), g["p2"]
        elif g["h"] is not None:           # 오후 2시 / 14시 / 6시 반 / 2시 30분
            h, period = int(g["h"]), g["p"]
            minute = 30 if g["half"] else int(g["m"] or 0)
        else:                              # 2PM, 9:30am
            h, minute = int(g["h3"]), int(g["m3"] or 0)
            period = "오후" if g["ap"].lower() == "p" else "오전"

        # '오후 2시~6시'처럼 범위의 뒤쪽에 오전/오후가 없으면 앞쪽 것을 이어받는다
        if (period is None and prev_end is not None and prev_period
                and SEP_RE.match(text[prev_end:m.start()])):
            period = prev_period

        if h > 24 or minute > 59 or (h == 24 and minute > 0):
            continue  # 시각이 아닌 숫자는 그대로 둔다

        out.append(text[pos:m.start()])
        out.append(f"{to_24h(h, period):02d}:{minute:02d}")
        pos = prev_end = m.end()
        prev_period = period

    out.append(text[pos:])
    return "".join(out)

"""디스코드 메시지가 '일정 얘기'인지 가볍게 걸러내는 함수.

AI(LLM)를 부르기 전에 먼저 거르는 용도라서, 정규식만 쓰고 외부 라이브러리는 쓰지 않는다.
(그래서 Actions 테스트에서도 discord.py 없이 돌릴 수 있다.)
"""
import re

# 날짜·요일·시간 표현
DATE_TIME_PATTERNS = [
    r"\d{1,2}\s*월\s*\d{1,2}\s*일",      # 11월 14일
    r"\d{1,2}\s*/\s*\d{1,2}",             # 11/14
    r"\d{1,2}\s*일",                      # 14일
    r"[월화수목금토일]요일",                # 금요일
    r"오늘|내일|모레|글피|이번\s*주|다음\s*주|주말",
    r"이번\s*달|다음\s*달|이번\s*해|올해|내년|월말|연말",
    r"\d{1,2}\s*시",                      # 2시, 14시
    r"\d{1,2}\s*:\s*\d{2}",               # 14:30
    r"오전|오후",
]

# 일정을 암시하는 단어
KEYWORDS = ["회의", "마감", "까지", "모임"]

_DATE_RE = re.compile("|".join(DATE_TIME_PATTERNS))


def is_schedule_message(content: str) -> bool:
    """날짜·시간 표현이나 일정 키워드가 있으면 True."""
    if not content or not content.strip():
        return False
    if _DATE_RE.search(content):
        return True
    return any(word in content for word in KEYWORDS)

import pytest

from filter import is_schedule_message

# 일정 있음 6
SCHEDULE = [
    "금요일 오후 2시에 팀 회의",
    "11/14 모임 있어요",
    "다음 주 수요일 3시에 다시 모이자",
    "발표 자료 마감은 12월 1일입니다",
    "이번 주까지 PPT 제출해 주세요",
    "월요일 2시에 회의하자",
]

# 일정 없음 5
NOT_SCHEDULE = [
    "점심 뭐 먹지?",
    "ㅋㅋㅋㅋ 이거 진짜 웃기다",
    "PR 리뷰 부탁해요",
    "안녕하세요 잘 부탁드립니다",
    "이 에러 나는데 봐줄 수 있어?",
]


@pytest.mark.parametrize("text", SCHEDULE)
def test_schedule_messages(text):
    assert is_schedule_message(text) is True


@pytest.mark.parametrize("text", NOT_SCHEDULE)
def test_non_schedule_messages(text):
    assert is_schedule_message(text) is False


def test_empty_message():
    assert is_schedule_message("") is False


def test_month_and_year_expressions_reach_analysis():
    for text in ['이번달 여행 가자', '이번 달 회의', '다음 달 모이자', '올해 프로젝트', '내년 프로젝트', '월말 정리', '연말 행사']:
        assert is_schedule_message(text)

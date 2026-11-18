from timeparse import normalize_times as n


def test_feedback_examples():
    assert n("오후 2시") == "14:00"
    assert n("2PM") == "14:00"
    assert n("14시") == "14:00"
    assert n("오후 6시 반") == "18:30"


def test_same_time_different_expressions():
    forms = ["오후 2시", "14시", "2PM", "2pm", "오후 2:00", "2시"]
    assert {n(f) for f in forms} == {"14:00"}


def test_minutes_and_periods():
    assert n("저녁 7시 30분") == "19:30"
    assert n("오전 9시") == "09:00"
    assert n("새벽 2시") == "02:00"
    assert n("점심 12시") == "12:00"
    assert n("오후 12시") == "12:00"
    assert n("오전 12시") == "00:00"
    assert n("밤 10시") == "22:00"
    assert n("9:30pm") == "21:30"
    assert n("12am") == "00:00"
    assert n("오후 2:30") == "14:30"


def test_range_inherits_period():
    assert n("오후 2시~6시") == "14:00~18:00"
    assert n("오전 10시~오후 2시") == "10:00~14:00"
    assert n("10시~12시") == "10:00~12:00"
    assert n("오후 2시부터 6시") == "14:00부터 18:00"


def test_inside_sentence():
    assert n("금요일 오후 2시에 팀 회의") == "금요일 14:00에 팀 회의"
    assert n("11월 12일 3시까지") == "11월 12일 15:00까지"


def test_not_time_expressions_untouched():
    assert n("2시간 걸려요") == "2시간 걸려요"
    assert n("프로젝트 시작해요") == "프로젝트 시작해요"
    assert n("14:30에 만나요") == "14:30에 만나요"
    assert n("99시") == "99시"

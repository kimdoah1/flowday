import json
import os
import uuid

from datetime import date, datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


API_URL = os.getenv(
    "CONSOLE_API_URL",
    "http://localhost:8000"
)

KST = timezone(timedelta(hours=9))

WEEKDAY_MAP = {
    "월": "Monday",
    "화": "Tuesday",
    "수": "Wednesday",
    "목": "Thursday",
    "금": "Friday",
    "토": "Saturday",
    "일": "Sunday"
}


def request_api(path, method="GET", data=None):
    url = API_URL + path

    headers = {
        "Content-Type": "application/json"
    }

    body = None

    if data is not None:
        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

    req = Request(
        url,
        data=body,
        headers=headers,
        method=method
    )

    try:
        with urlopen(req, timeout=120) as response:
            if response.status == 204:
                return None

            result = response.read().decode("utf-8")

            if not result:
                return None

            return json.loads(result)

    except HTTPError as e:
        error_body = e.read().decode("utf-8")

        try:
            message = json.loads(error_body).get(
                "detail",
                error_body
            )
        except json.JSONDecodeError:
            message = error_body

        print(f"\n[API 오류] {e.code}: {message}")

    except (URLError, TimeoutError) as e:
        print("\n[연결 오류] API 서버에 연결할 수 없습니다.")
        print("API 서버가 실행 중인지 확인해 주세요.")
        print(e)

    return None


def input_date(message):
    while True:
        value = input(message).strip()

        try:
            return date.fromisoformat(value)

        except ValueError:
            print("YYYY-MM-DD 형식으로 입력해 주세요.")


def input_positive_number(message):
    while True:
        try:
            number = int(input(message).strip())

            if number > 0:
                return number

        except ValueError:
            pass

        print("1 이상의 정수를 입력해 주세요.")


def input_rest_days():
    print("\n휴식 요일을 입력해 주세요.")
    print("예: 일")
    print("예: 토, 일")
    print("휴식일이 없다면 Enter를 누르세요.")

    while True:
        value = input("휴식 요일: ").strip()

        if not value:
            return []

        selected = []

        for day in value.replace(" ", "").split(","):
            if day not in WEEKDAY_MAP:
                print("월, 화, 수, 목, 금, 토, 일 중 입력해 주세요.")
                break

            english_day = WEEKDAY_MAP[day]

            if english_day not in selected:
                selected.append(english_day)

        else:
            return selected


def input_study_information():
    print("\n========== AI 학습 계획 생성 ==========")

    goal = input("학습 목표: ").strip()

    while not goal:
        print("학습 목표를 입력해 주세요.")
        goal = input("학습 목표: ").strip()

    start_date = input_date(
        "학습 시작일 (YYYY-MM-DD): "
    )

    deadline = input_date(
        "목표 마감일 (YYYY-MM-DD): "
    )

    while start_date > deadline:
        print("마감일은 시작일보다 빠를 수 없습니다.")
        deadline = input_date(
            "목표 마감일 (YYYY-MM-DD): "
        )

    book_name = input("교재명: ").strip()

    while not book_name:
        print("교재명을 입력해 주세요.")
        book_name = input("교재명: ").strip()

    total_pages = input_positive_number(
        "교재 전체 페이지 수: "
    )

    available_minutes = input_positive_number(
        "하루 학습 가능 시간 (분): "
    )

    rest_days = input_rest_days()

    return {
        "goal": goal,
        "start_date": start_date.isoformat(),
        "deadline": deadline.isoformat(),
        "book_name": book_name,
        "total_pages": total_pages,
        "available_minutes_per_day": available_minutes,
        "rest_days": rest_days
    }


def print_plan(plan, information):
    print("\n========== 최적화된 학습 계획 ==========")

    print(f"목표: {information['goal']}")
    print(f"교재: {information['book_name']}")
    print(f"전체 분량: {information['total_pages']}페이지")

    print(
        f"하루 학습 가능 시간: "
        f"{information['available_minutes_per_day']}분"
    )

    print(
        f"휴식 요일: "
        f"{', '.join(information['rest_days']) or '없음'}"
    )

    print("\n----------------------------------------")

    daily_totals = {}

    for i, task in enumerate(plan["tasks"], start=1):
        task_date = task["date"]

        print(f"\n[{i}] {task_date}")
        print(f"학습 내용: {task['title']}")

        print(
            f"페이지: {task['pages_start']}~"
            f"{task['pages_end']}페이지"
        )

        print(
            f"예상 학습 시간: "
            f"{task['estimated_minutes']}분"
        )

        daily_totals[task_date] = (
            daily_totals.get(task_date, 0)
            + task["estimated_minutes"]
        )

    print("\n========== 날짜별 학습 시간 ==========")

    for task_date, total in sorted(daily_totals.items()):
        print(f"{task_date}: {total}분")

    print("\n----------------------------------------")
    print(f"총 {len(plan['tasks'])}개의 학습 항목이 생성되었습니다.")


def select_tasks(plan):
    print("\n========== 일정 저장 ==========")
    print("저장할 일정 번호를 입력하세요.")
    print("여러 개는 쉼표로 구분합니다.")
    print("전체 저장: all")
    print("저장 취소: 0")

    while True:
        value = input("\n선택: ").strip().lower()

        if value == "0":
            return []

        if value == "all":
            return plan["tasks"]

        try:
            numbers = [
                int(number.strip())
                for number in value.split(",")
            ]

            if len(numbers) != len(set(numbers)):
                print("같은 번호를 중복 선택할 수 없습니다.")
                continue

            if any(
                number < 1 or number > len(plan["tasks"])
                for number in numbers
            ):
                print("존재하는 일정 번호를 입력해 주세요.")
                continue

            return [
                plan["tasks"][number - 1]
                for number in numbers
            ]

        except ValueError:
            print("번호 또는 all을 입력해 주세요.")


def save_tasks(tasks, information):
    plan_id = str(uuid.uuid4())

    saved_count = 0

    print("\n========== 일정 저장 결과 ==========")

    for task in tasks:
        task_date = date.fromisoformat(task["date"])

        start_datetime = datetime.combine(
            task_date,
            datetime.min.time(),
            tzinfo=KST
        )

        end_datetime = start_datetime + timedelta(days=1)

        memo = (
            f"교재: {information['book_name']}\n"
            f"페이지: {task['pages_start']}~"
            f"{task['pages_end']}페이지\n"
            f"예상 학습 시간: "
            f"{task['estimated_minutes']}분\n"
            f"학습 목표: {information['goal']}"
        )

        event = {
            "title": task["title"],
            "start_at": start_datetime.isoformat(),
            "end_at": end_datetime.isoformat(),
            "all_day": True,
            "source": "ai_plan",
            "source_ref": plan_id,
            "memo": memo
        }

        result = request_api(
            "/api/events",
            method="POST",
            data=event
        )

        if result is not None:
            saved_count += 1
            print(
                f"[저장 완료] {task['date']} - "
                f"{task['title']}"
            )
        else:
            print(
                f"[저장 실패] {task['date']} - "
                f"{task['title']}"
            )

    print("\n----------------------------------------")
    print(f"선택한 일정: {len(tasks)}개")
    print(f"저장 성공: {saved_count}개")
    print(f"저장 실패: {len(tasks) - saved_count}개")


def main():
    information = input_study_information()

    print("\nAI가 학습 항목을 생성하고 있습니다...")
    print("이후 OR-Tools가 날짜별 일정을 최적화합니다.")

    plan = request_api(
        "/api/ai/plan",
        method="POST",
        data=information
    )

    if plan is None:
        print("\n학습 계획 생성에 실패했습니다.")
        return

    if not plan.get("tasks"):
        print("\n생성된 학습 항목이 없습니다.")
        return

    print_plan(plan, information)

    selected_tasks = select_tasks(plan)

    if not selected_tasks:
        print("\n일정 저장을 취소했습니다.")
        return

    save_tasks(selected_tasks, information)


if __name__ == "__main__":
    main()
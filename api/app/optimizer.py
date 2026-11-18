
from datetime import timedelta

from ortools.sat.python import cp_model


MAX_TASKS_PER_DAY = 3


def optimize_plan(draft, request):
    """
    LLM이 생성한 학습 항목을 날짜별로 배치합니다.

    최적화 조건:
    1. 모든 학습 항목을 반드시 한 날짜에 배치
    2. 휴식 요일에는 배치하지 않음
    3. 하루 학습 시간은 제한 시간 이하
    4. 하루 최대 3개 학습 항목
    5. 학습 항목의 순서 유지
    6. 날짜별 학습 시간 균형 유지
    7. 날짜별 학습 항목 개수 균형 유지
    """

    tasks = draft.tasks

    if not tasks:
        raise ValueError("최적화할 학습 항목이 없습니다.")

    # 시작일부터 마감일까지 학습 가능한 날짜 계산
    available_dates = []

    current_date = request.start_date

    while current_date <= request.deadline:
        weekday = current_date.strftime("%A")

        if weekday not in request.rest_days:
            available_dates.append(current_date)

        current_date += timedelta(days=1)

    if not available_dates:
        raise ValueError("학습 가능한 날짜가 없습니다.")

    task_count = len(tasks)
    day_count = len(available_dates)

    # 하루 최대 항목 개수 검사
    if task_count > day_count * MAX_TASKS_PER_DAY:
        raise ValueError(
            "학습 항목이 너무 많아 현재 기간에 배치할 수 없습니다. "
            "학습 기간을 늘려 주세요."
        )

    # 각 학습 항목의 예상 시간 검사
    for task in tasks:
        if task.estimated_minutes > request.available_minutes_per_day:
            raise ValueError(
                f"'{task.title}'의 예상 학습 시간이 "
                "하루 학습 가능 시간을 초과합니다."
            )

    # 전체 학습 시간 검사
    total_minutes = sum(
        task.estimated_minutes
        for task in tasks
    )

    if total_minutes > (
        request.available_minutes_per_day * day_count
    ):
        raise ValueError(
            "전체 학습 시간이 남은 학습 가능 시간보다 많습니다."
        )

    model = cp_model.CpModel()

    # x[i][d]:
    # i번째 학습 항목을 d번째 날짜에 배치하면 1
    x = {}

    for i in range(task_count):
        for d in range(day_count):
            x[i, d] = model.new_bool_var(
                f"task_{i}_day_{d}"
            )

    # 각 학습 항목은 정확히 한 날짜에 배치
    for i in range(task_count):
        model.add(
            sum(x[i, d] for d in range(day_count)) == 1
        )

    daily_load = []
    daily_count = []

    for d in range(day_count):

        # 날짜별 총 학습 시간
        load = sum(
            tasks[i].estimated_minutes * x[i, d]
            for i in range(task_count)
        )

        # 날짜별 학습 항목 개수
        count = sum(
            x[i, d]
            for i in range(task_count)
        )

        # 하루 학습 시간 제한
        model.add(
            load <= request.available_minutes_per_day
        )

        # 하루 최대 학습 항목 개수
        model.add(
            count <= MAX_TASKS_PER_DAY
        )

        # 가능한 경우 날짜별 학습 항목을 고르게 배치
        min_tasks_per_day = task_count // day_count

        model.add(
            count >= min_tasks_per_day
        )

        load_var = model.new_int_var(
            0,
            request.available_minutes_per_day,
            f"daily_load_{d}"
        )

        model.add(load_var == load)

        count_var = model.new_int_var(
            0,
            MAX_TASKS_PER_DAY,
            f"daily_count_{d}"
        )

        model.add(count_var == count)

        daily_load.append(load_var)
        daily_count.append(count_var)

    # 학습 항목 순서 유지
    for i in range(task_count - 1):

        current_day = sum(
            d * x[i, d]
            for d in range(day_count)
        )

        next_day = sum(
            d * x[i + 1, d]
            for d in range(day_count)
        )

        model.add(current_day <= next_day)

    # 날짜별 학습 시간 균형
    target_minutes = total_minutes // day_count

    load_deviations = []

    for d in range(day_count):

        deviation = model.new_int_var(
            0,
            request.available_minutes_per_day,
            f"load_deviation_{d}"
        )

        model.add_abs_equality(
            deviation,
            daily_load[d] - target_minutes
        )

        load_deviations.append(deviation)

    # 날짜별 학습 항목 개수 균형
    target_count = task_count // day_count

    count_deviations = []

    for d in range(day_count):

        deviation = model.new_int_var(
            0,
            MAX_TASKS_PER_DAY,
            f"count_deviation_{d}"
        )

        model.add_abs_equality(
            deviation,
            daily_count[d] - target_count
        )

        count_deviations.append(deviation)

    # 시간과 항목 개수를 함께 고려
    average_task_minutes = max(
        1,
        total_minutes // task_count
    )

    model.minimize(
        sum(load_deviations)
        + average_task_minutes * sum(count_deviations)
    )

    # 최적화 실행
    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 8

    status = solver.solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE
    ):
        raise ValueError(
            "입력한 조건으로 학습 계획을 배치할 수 없습니다. "
            "학습 기간을 늘리거나 하루 학습 시간을 늘려 주세요."
        )

    # 최적화 결과 반환
    optimized_tasks = []

    for i, task in enumerate(tasks):

        assigned_day = None

        for d in range(day_count):

            if solver.value(x[i, d]) == 1:
                assigned_day = available_dates[d]
                break

        if assigned_day is None:
            raise ValueError(
                "학습 일정 배치 결과를 확인할 수 없습니다."
            )

        optimized_tasks.append({
            "title": task.title,
            "date": assigned_day,
            "pages_start": task.pages_start,
            "pages_end": task.pages_end,
            "estimated_minutes": task.estimated_minutes
        })

    # 날짜순 정렬
    optimized_tasks.sort(
        key=lambda task: task["date"]
    )

    return optimized_tasks

import math

MAX_TASKS = 60
MIN_TASK_MINUTES = 5
MAX_TASK_MINUTES = 45


from datetime import date
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm import ask_llm
from app.optimizer import optimize_plan


router = APIRouter()


# 사용자가 AI 계획 생성을 요청할 때 전달하는 입력 데이터
class PlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    start_date: date
    deadline: date
    book_name: str = Field(min_length=1)
    total_pages: int = Field(gt=0)
    available_minutes_per_day: int = Field(gt=0)
    rest_days: List[str] = Field(default_factory=list)


# Claude가 생성하는 학습 항목 하나
class PlanDraftTask(BaseModel):
    title: str
    pages_start: int
    pages_end: int
    estimated_minutes: int


# Claude가 생성하는 학습 항목 목록
class PlanDraft(BaseModel):
    tasks: List[PlanDraftTask]


# 최종적으로 사용자에게 반환하는 학습 항목 하나
class PlanTask(BaseModel):
    title: str
    date: date
    pages_start: int
    pages_end: int
    estimated_minutes: int


# 최종 API 응답
class PlanResponse(BaseModel):
    tasks: List[PlanTask]


def validate_request(request: PlanRequest):
    """사용자가 입력한 학습 계획 조건을 검사합니다."""

    if request.start_date > request.deadline:
        raise ValueError("시작일은 마감일보다 늦을 수 없습니다.")

    valid_weekdays = {
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    }

    for day in request.rest_days:
        if day not in valid_weekdays:
            raise ValueError(f"잘못된 휴식 요일입니다: {day}")


import math


MAX_TASKS = 60
MIN_TASK_MINUTES = 5
MAX_TASK_MINUTES = 45


def validate_draft(draft: PlanDraft, request: PlanRequest):
    tasks = draft.tasks

    if not tasks:
        raise ValueError("생성된 학습 항목이 없습니다.")

    if len(tasks) > MAX_TASKS:
        raise ValueError("학습 항목은 최대 60개까지 생성할 수 있습니다.")

    # 전체 페이지에 따른 학습 항목의 최대 페이지 수
    max_pages_per_task = max(
        10,
        math.ceil(request.total_pages / MAX_TASKS)
    )

    # 필요한 최소 학습 항목 개수
    min_task_count = math.ceil(
        request.total_pages / max_pages_per_task
    )

    if len(tasks) < min_task_count:
        raise ValueError(
            f"학습 항목이 너무 적습니다. "
            f"최소 {min_task_count}개 이상 생성해야 합니다."
        )

    expected_page = 1

    max_minutes = min(
        MAX_TASK_MINUTES,
        request.available_minutes_per_day
    )

    for task in tasks:

        # 제목 검사
        if not task.title.strip():
            raise ValueError("학습 항목의 제목이 비어 있습니다.")

        # 페이지 시작 및 종료 검사
        if task.pages_start != expected_page:
            raise ValueError(
                "학습 페이지 범위가 연속적이지 않습니다."
            )

        if task.pages_end < task.pages_start:
            raise ValueError(
                f"'{task.title}'의 페이지 범위가 잘못되었습니다."
            )

        if task.pages_end > request.total_pages:
            raise ValueError(
                f"'{task.title}'의 페이지 범위가 "
                "전체 페이지를 초과합니다."
            )

        # 한 학습 항목의 페이지가 너무 많지 않은지 검사
        page_count = (
            task.pages_end - task.pages_start + 1
        )

        if page_count > max_pages_per_task:
            raise ValueError(
                f"'{task.title}'의 학습 분량이 너무 많습니다."
            )

        # 예상 학습 시간 검사
        if task.estimated_minutes < MIN_TASK_MINUTES:
            raise ValueError(
                f"'{task.title}'의 예상 학습 시간이 너무 짧습니다."
            )

        if task.estimated_minutes > max_minutes:
            raise ValueError(
                f"'{task.title}'의 예상 학습 시간이 "
                "허용 범위를 초과합니다."
            )

        expected_page = task.pages_end + 1

    # 전체 페이지가 빠짐없이 포함되었는지 검사
    if expected_page != request.total_pages + 1:
        raise ValueError(
            "생성된 학습 항목이 교재 전체 페이지를 포함하지 않습니다."
        )

def make_plan(request: PlanRequest) -> PlanResponse:
    """Claude로 학습 항목을 생성하고 OR-Tools로 날짜를 배치합니다."""

    validate_request(request)

    max_pages_per_task = max(
    10,
    math.ceil(request.total_pages / MAX_TASKS)
    )

    max_task_minutes = min(
    45,
    request.available_minutes_per_day
    )

    prompt = f"""
당신은 전문적인 학습 계획 설계 AI입니다.

사용자의 목표와 교재 정보를 바탕으로
실제로 수행할 수 있는 상세한 학습 항목을 생성하세요.

[학습 정보]

학습 목표: {request.goal}
교재명: {request.book_name}
전체 페이지: {request.total_pages}페이지

시작일: {request.start_date}
마감일: {request.deadline}

하루 학습 가능 시간: {request.available_minutes_per_day}분
휴식 요일: {request.rest_days}

[학습 항목 생성 규칙]

1. 교재 전체 페이지를 작은 학습 단위로 나누세요.

2. 한 학습 항목은 가급적 5~10페이지로 구성하세요.
   한 항목의 페이지 범위는 최대 {max_pages_per_task}페이지입니다.

3. 전체 학습 항목은 최소
   {math.ceil(request.total_pages / max_pages_per_task)}개 이상,
   최대 {MAX_TASKS}개 이하로 생성하세요.

4. 학습 항목의 제목은 구체적으로 작성하세요.

   좋지 않은 예시:
   - Listening 공부
   - Reading 학습
   - Part 1~4 학습

   좋은 예시:
   - 사진 속 인물의 동작을 나타내는 표현 학습
   - Part 1 사진 묘사 문제의 주요 오답 유형 정리
   - 의문사 의문문에 대한 응답 유형 학습
   - Part 3 대화의 목적과 세부 정보 파악 연습
   - 지문에서 핵심 정보와 정답 근거 찾기

5. 각 학습 항목은 구체적인 학습 활동을 포함해야 합니다.

   예를 들어:
   - 개념 이해
   - 핵심 표현 암기
   - 유형별 문제 풀이
   - 오답 분석
   - 복습 및 정리

6. 각 학습 항목의 예상 학습 시간은
   5분 이상 {max_task_minutes}분 이하의 정수로 작성하세요.

7. 페이지 범위는 반드시 1페이지부터
   {request.total_pages}페이지까지 빠짐없이 포함해야 합니다.

8. 페이지 범위는 겹치거나 누락되면 안 됩니다.

9. 학습 항목은 교재의 페이지 순서대로 작성하세요.

10. 교재의 실제 목차나 페이지별 내용을 제공받지 않았다면
    확인되지 않은 단원명이나 세부 내용을 사실처럼 만들어내지 마세요.
    이 경우 학습 목표에 맞는 일반적인 학습 활동 중심으로
    구체적인 제목을 작성하세요.

[중요한 제한 사항]

- 학습 날짜는 생성하지 마세요.
- 날짜 배정은 별도의 최적화 프로그램이 담당합니다.
- 모든 학습 항목을 빠짐없이 생성하세요.
- 지나치게 큰 학습 범위로 항목을 묶지 마세요.
- 같은 내용의 학습 항목을 반복 생성하지 마세요.

반드시 지정된 Pydantic 출력 형식에 맞춰 응답하세요.
"""

    # 1. Claude가 학습 항목 생성
    draft = ask_llm(prompt, PlanDraft)

    # 2. Claude가 생성한 결과 검증
    validate_draft(draft, request)

    # 3. OR-Tools가 학습 항목을 날짜별로 배치
    optimized_tasks = optimize_plan(draft, request)

    # 4. 최종 응답 생성
    return PlanResponse(tasks=optimized_tasks)


@router.post("/ai/plan", response_model=PlanResponse)
def create_plan(request: PlanRequest):
    """AI 학습 계획 생성 API"""

    try:
        return make_plan(request)

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except Exception as e:
        print(f"AI 계획 생성 오류: {e}")

        raise HTTPException(
            status_code=502,
            detail="AI 학습 계획 생성 중 오류가 발생했습니다."
        )

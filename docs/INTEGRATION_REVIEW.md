# Flowday 통합 검토 기록

검증일: 2026-11-20 (KST). 대상: `feature/service-integration` → `develop`, PR #7.
기준 develop: `14de2d4` (PR #6 병합 완료). develop/master에는 직접 push하지 않는다.

## 변경과 보존한 코드

- 기존 캘린더에 연간 12개월 보기, 연도/월 선택, 전체 일정 목록을 추가했다. 일정 CRUD와 기존 디자인을 유지한다.
- 검토함과 메뉴 배지는 실제 pending 후보를 공유하며 5초마다 갱신한다. 후보가 없으면 배지를 숨기고 API 실패는 화면에 표시한다.
- PostgreSQL events/proposals API를 추가했다. 승인 전에는 일정이 없고 external_id 중복, 반복 승인, 거절 후 승인 요청을 검증한다.
- 기존 책 학습 계획 및 OR-Tools 경로를 보존하며 일반 목표 요청을 지원한다. `mode=rule`과 `mode=llm`을 구분한다. API 실패를 Mock 성공으로 대체하지 않는다.
- 기존 회의 요약/추출 라우터와 faster-whisper worker를 연결한다. 텍스트 분석은 스레드에서 수행해 API 이벤트 루프를 막지 않는다. Worker의 결과 전달은 요약·추출 두 호출을 기다리도록 120초 제한을 둔다.
- 기존 Discord 멘션 분석, 초기화, 반응 기능을 유지한다. 지정 채널의 메시지만 실제 추출 API와 후보 API로 보낸다.
- 이번 달·다음 달·올해·내년·월말·연말을 감지한다. 명확한 날짜는 그대로 추출한다. Discord에서만 선택적으로 날짜가 모호한 기간 요청에 빈 시간 후보를 추천한다.
- 추천은 규칙 기반이다. 해당 기간의 현재 이후 평일 09~18시 중 첫 빈 1시간을 30분 간격으로 찾고, 확정 일정과 pending 후보 모두를 피한다. `[시간 추천]`으로 표시하며 승인 전에는 저장된 캘린더 일정이 아니다. 명시 날짜/시간, 마감, 주말 조건 등을 이 기본 추천으로 덮어쓰지 않는다.
- Gemini 호출은 45초 제한, 자동 재시도 0회다. 추출/요약은 기존 규칙 대체 동작을 유지하고, 계획 실패는 오류를 반환한다.
- Compose 서비스 5종을 유지한다. develop 병합 충돌은 frontend의 고정 container_name 한 곳이었다. 여러 테스트 프로젝트가 충돌하지 않도록 Compose 자동 이름을 사용한다.

주요 담당 코드: 김도아의 계획/LLM/optimizer, 정혁의 meeting_ai/meetings/Whisper,
정세린의 Discord 분석/필터/API 클라이언트, 박수현의 공통 React/API 계약,
남영준의 캘린더/대시보드/Docker를 유지하며 필요한 연결부를 수정했다.

## 실행 검증

테스트 프로젝트 `flowday-final-check`는 사용자 데이터와 분리된 PostgreSQL 볼륨을 사용했다.

| 검증 | 결과 |
|---|---|
| Python 문법 검사 | 통과 |
| 백엔드 전체 pytest (실제 PostgreSQL, LLM_MODE=rule) | 37 passed |
| Discord pytest (외부 응답 대체) | 49 passed |
| 프론트 npm test | 7 passed |
| npm ci / npm run build | 통과 |
| JS 문법 / Compose 설정 검사 | 통과 |
| frontend/api/meeting-worker 이미지 빌드 | 통과; 봇 이미지도 로컬 PR7에서 빌드·실행됨 |
| Nginx → API → PostgreSQL CRUD/후보 승인 | integration_smoke.py 통과 |
| DB 영속성 | 테스트용 컨테이너 재생성 후 marker 일정 재조회·삭제 통과 |
| 한국어 음성 전사 | Windows Heami 합성 음성 → 실제 faster-whisper small → 규칙 분석 성공 |
| 음성 내용/결과 | “11월 25일 오후 3시부터 4시까지 팀 회의” → 2026-11-25 15:00~16:00 |
| 실제 Discord | 로그인/모델 확인, 메시지 추출 200, 후보 생성 201, 사용자 승인 후 DB 일정 저장 확인 |
| 브라우저 | 연간/월간/전체 보기, 윤일 이동, 일정 편집·완료·새로고침 유지, 모바일 너비 확인 |
| 검토함 브라우저 테스트 | 응답 대체로 0개 배지 숨김, 폴링, 승인 후 갱신, 오류 표시 확인 |
| 실제 Gemini | 계획 생성 성공 이력이 있지만 이번 HTTP 재검증은 502. 같은 모델의 구조화된 작업 3개 생성 직접 호출은 성공. 안정성 미확보 |

합성 음성 테스트는 사람의 실제 녹음 품질 검증과 다르다. 외부 AI 테스트와 규칙/대체 응답 테스트를 구분한다.
최신 GitHub Actions 결과는 PR #7의 Checks에서 확인한다. 과거 커밋의 성공을 최신 결과로 사용하지 않는다.

## 실행 방법

루트 `.env.example`을 `.env`로 복사하고 실제 키는 로컬에만 입력한다.

```bash
# Compose v2
docker compose --env-file .env up -d --build db api frontend meeting-worker discord-bot
# 이 PC의 Compose v1 환경
docker-compose --env-file .env -p flowday-pr7-test up -d --build db api frontend meeting-worker discord-bot
```

| 환경 변수 | 용도 |
|---|---|
| POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB | DB 접속 정보 |
| FRONTEND_PORT / API_PORT | 기본 8080 / 8000. 현재 사용자 테스트는 18087 / 18007 |
| GEMINI_API_KEY / LLM_MODEL | 실제 Gemini. 모델은 계정에서 사용 가능한 이름으로 설정 |
| LLM_MODE | auto: 실제 AI 사용. rule: 명시적 규칙 테스트 |
| DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID | 봇 로그인과 후보 자동 전송 대상 채널 |
| WHISPER_MODEL | 기본 small |
| VITE_USE_MOCK | 프론트 빌드 인자 true인 경우에만 Mock; 기본 false |

Discord Developer Portal에서 Message Content Intent를 켜고, 채널 보기/메시지 보내기/기록 보기/반응 추가 권한으로 초대한다.
채널 ID가 비어 있으면 검토함 자동 전송을 하지 않는다. 자세한 절차는 `discord_bot/README.md`.
중지할 때 `docker-compose --env-file .env -p flowday-pr7-test down`을 사용한다. DB 유지가 필요하면 `-v`를 붙이지 않는다.

## 평가와 발표

- Git: 기존 feature 브랜치, PR #6 → develop, 통합 PR #7의 기능별 커밋과 리뷰 기록을 보여준다.
- Docker: frontend/api/db/meeting-worker/discord-bot 5종, Nginx→API→DB 및 Worker 공유 음성 볼륨, DB 볼륨을 보여준다.
- 오픈소스: faster-whisper와 OR-Tools 등 실제 사용 코드를 설명한다. 수업에서 다룬 오픈소스인지 여부는 수업 목록과 대조해야 한다.
- Actions: frontend-test, backend-test, bot-test, lint, docker-build, integration-test 6개 workflow의 최신 실행 결과를 보여준다.
- 시연: 일정 CRUD/새로고침 → 연간 보기 → Discord 메시지/검토함 승인 → 캘린더 → 한국어 음성 전사 순서. 실제 AI 계획은 외부 모델 상태 확인 후 시연한다.

## 남은 제한

- Gemini가 간헐적으로 시간 초과/오류를 반환한다. 계획 기능이 항상 성공한다고 보장할 수 없다.
- 회의 메타데이터/결과는 기존 메모리 저장 방식이라 API 재시작 시 사라진다. 일정/후보 DB는 유지된다.
- 봇 후보 전달 실패의 영속 재시도 큐가 없다. 📅 반응은 후보 저장 완료의 증거가 아니다.
- 빈 시간 추천은 기본 정책이며 자연어 제약을 모두 처리하는 최적화기가 아니다. 승인 직전 다른 일정이 생기면 충돌할 수 있다.
- npm audit의 기존 경고 2개(moderate 1/high 1)가 남아 있다.
- 최종 머지는 담당자 검토 후 수행한다. 이번 작업에서 원격 develop/master 변경이나 PR 머지는 하지 않는다.

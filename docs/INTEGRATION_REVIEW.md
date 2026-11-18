# Flowday 통합 검토 및 실행 기록

검토일: 2026-11-19. 기준: origin/develop `8190765`, 로컬 `feature/service-integration`.
공식 규격 참고: `../test/Flowday_Integrated_Working_Copy/docs/Flowday_Team_Development_Guide.md`.

## Git 상태와 권장 PR 순서

- 원래 `../flowday`는 `feature/calendar-ui`, HEAD `2906cf0`. 이미 develop을 병합한 상태였다.
- 원격보다 13개 앞섰지만 대부분 팀원 커밋/병합 이력이다. 독자적인 기능 13개를 뜻하지 않는다.
- 미커밋 변경 59개 중 줄바꿈을 제외한 기존 파일의 실질 변경은 CalendarPage, DashboardPage, CSS 3개였다. EventModal과 calendar 유틸은 미추적 상태였다.
- 원래 작업 폴더와 미커밋 파일을 수정하지 않았다. 새 worktree `../flowday-integration`에서 작업했다.
- PR #1~#5의 병합은 develop 이력에 존재한다. 원격 브랜치 병합/삭제, push, 강제 push는 수행하지 않았다.
- **권장: 담당 UI PR → 팀원 리뷰·develop 병합 → 통합 PR.** 자신의 feature에 develop을 받아 테스트하는 것은 정상적인 작업이다. 다른 담당자의 기능 수정까지 한 PR에 섞는 것은 피한다.
- `feature/calendar-ui-review`는 최신 develop에서 캘린더 담당 변경만 분리한 새 로컬 브랜치다. 기존 `feature/calendar-ui`를 덮어쓰지 않는다.
- 캘린더 커밋 `cc1632a`: UI/모달/달력 유틸/CSS/프론트 Docker/초기 테스트. 이 커밋은 통합 브랜치의 첫 커밋이기도 하다.
- API 커밋 `c1b879c`: 일정·후보 PostgreSQL 저장, 기존 책 계획 호환, 일반 목표 계획, API 테스트.
- 연결 커밋 `f0bfa5e`: 회의 입력·업로드, 선택 계획 저장, Discord 후보 전달, Worker 오류 확인.
- 나머지 CI/Compose/검증 문서는 별도 커밋으로 묶는다.

게시할 때의 명령(이번 작업에서는 실행하지 않음):

```bash
git push -u origin feature/calendar-ui-review
# GitHub: base develop <- compare feature/calendar-ui-review
# 팀 리뷰 후 병합. 통합 브랜치에도 같은 커밋이 있으므로 일반 merge 방식이면 이력 연결이 쉽다.
git push -u origin feature/service-integration
# GitHub: base develop <- compare feature/service-integration
```

캘린더 PR을 squash 병합한다면 통합 PR의 중복 변경 여부를 다시 비교한 후 develop을 동기화한다. 원래 작업 폴더에서 `git add .`로 59개 파일을 무작정 올리지 않는다.

## 첨부 통합본과 현재 코드의 차이

첨부 통합본의 main.py는 일정 라우터만 등록한 MVP이고, 기존 팀의 책 계획/회의/봇 전체 구현을 대체할 수 없다. 따라서 전체 덮어쓰기는 하지 않았다. 첨부본의 일정 CRUD, DB 연결, Nginx/Docker 구성 및 달력 테스트만 읽고 필요한 부분을 선별했다. PATCH 검증 예외의 500 응답 문제, 날짜 검증, 시간대와 행 잠금은 보완했다.

유지한 코드: 김도아의 `llm.py`, `optimizer.py`, 책 계획 검증/생성; 정혁의 `meeting_ai.py`, 추출·회의 라우터와 Whisper 전사 흐름; 정세린의 필터/요약/스케줄러/멘션 처리 및 기존 `flowday_later/api_client.py`; 박수현의 App/검토함/공통 클라이언트 함수 계약; 남영준의 로컬 캘린더·모달·대시보드·CSS.

## 기능 상태

| 기능 | 상태 및 증거 |
|---|---|
| 일정 CRUD | 실제 PostgreSQL 생성·조회·수정·삭제, 잘못된 PATCH 422, 별도 API 클라이언트 재조회 통과 |
| 후보 검토 | external_id 중복 409, 승인 전 미등록, 승인 트랜잭션/행 잠금, 반복 승인 동일 일정, 거절 후 승인 금지 테스트 통과 |
| 계획 | 기존 책 요청과 OR-Tools 유지, 일반 목표 요청 지원. 규칙 모드는 명시적으로 표시. Gemini 호출 경로는 가짜 모델로 검증, 실제 호출 미검증 |
| 회의 텍스트 | 입력 텍스트를 .txt 업로드로 전달하고 기존 요약/추출 사용. 실제 API 테스트 통과 |
| 녹음 | 업로드/폴링 UI와 기존 Whisper Worker 연결, 이미지 빌드 통과. 실제 녹음 전사는 이번에 미검증 |
| Discord | 기존 봇의 지정 채널 메시지를 기존 추출/후보 클라이언트에 연결. 기존 테스트 48개 통과. 실제 서버/토큰 수신 미검증 |
| 프론트 | 실 API 기본, VITE_USE_MOCK=true만 Mock. 캘린더·대시보드·모달 렌더링 테스트와 빌드 통과. 브라우저 클릭 시나리오는 미검증 |
| Docker | 5개 서비스 정의 유지, 자체 이미지 4개 빌드 성공. frontend/api/db 3종 실행·healthy, HTTP 통신과 볼륨 유지 확인 |
| Actions | 실행 가능한 6개 workflow 구성. 기존 원격 3개 성공 확인, 이번 변경의 원격 실행은 게시 전이라 미검증 |

## 실제 실행 결과

- `python -m compileall -q api discord_bot meeting_worker scripts`: 통과.
- `find frontend/src -name '*.js' -print0 | xargs -0 -n 1 node --check`: 통과.
- 로컬 `LLM_MODE=rule /tmp/flowday-venv/bin/python -m pytest -q` (api): **29 passed, 4 skipped**. DATABASE_URL이 없어서 DB 테스트 제외.
- `docker-compose -p flowday-integration-check exec -T -e LLM_MODE=rule api python -m pytest -q`: **33 passed**, 실제 PostgreSQL 포함, skip 없음.
- 봇 폴더 `/tmp/flowday-venv/bin/python -m pytest -q`: **48 passed**. LLM/HTTP 응답을 대체한 테스트이며 Discord 실서버 검증은 아님.
- 프론트 `npm ci`: 성공. 기존 의존성 audit 경고 2개(moderate 1, high 1)는 남아 있음. 강제 메이저 업그레이드는 하지 않음.
- 프론트 `npm test`: **5 passed** (날짜 4개, React 렌더링 1개).
- 프론트 `npm run build`: 성공, 40 modules.
- `docker-compose -p flowday-integration-check config --quiet`: 성공.
- `docker-compose -p flowday-integration-check build api frontend` 및 `build meeting-worker discord-bot`: 성공.
- `BASE_URL=http://localhost:18080 python3 scripts/integration_smoke.py`: Nginx→API→PostgreSQL CRUD/후보 승인 통과.
- `scripts/verify_volume.py create` → 테스트 프로젝트 `down`(볼륨 유지) → `up` → `verify`: 컨테이너 재생성 뒤 일정 유지 통과.
- `git diff --check`: 통과.

초기 제한 환경에서 DNS/로컬 소켓 권한 오류가 있었고, 승인된 실행 환경에서 재검증했다. 8080은 다른 컨테이너가 사용 중이어서 테스트 서버는 18080/API 18000으로 분리했다. 기존 컨테이너는 종료하지 않았다.

기존 GitHub 실행 기록(이번 변경과는 별개):
- [backend-test 성공](https://github.com/kimdoah1/flowday/actions/runs/44325342342)
- [bot-test 성공](https://github.com/kimdoah1/flowday/actions/runs/44325342211)
- [frontend-test 성공](https://github.com/kimdoah1/flowday/actions/runs/44325342143)

## 실행 방법과 환경 변수

현재 테스트 웹: http://localhost:18080 / API 문서: http://localhost:18000/docs

```bash
cd flowday-integration
# 별도 .env가 없어도 DB/API/frontend는 실행 가능
FRONTEND_PORT=18080 API_PORT=18000 LLM_MODE=rule \
  docker-compose -p flowday-integration-check up -d --build db api frontend
BASE_URL=http://localhost:18080 python3 scripts/integration_smoke.py
# 종료 시 데이터 보존
docker-compose -p flowday-integration-check down
```

일반적인 Docker Compose v2 환경에서는 `docker-compose` 대신 `docker compose`를 사용한다. 현재 Linux에는 v2 플러그인의 링크가 끊겨 있어 설치된 v1으로 검증했다. CI는 v2의 `--wait`를 사용한다.

`.env.example`을 복사하여 `.env`를 만들고 실제 키는 로컬에서만 입력한다.
- DB: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB. 로컬 Python 실행은 DATABASE_URL 별도 설정.
- 실제 AI: GEMINI_API_KEY, 계정에서 사용할 수 있는 LLM_MODEL, LLM_MODE=auto.
- 키 없는 일반 계획 초안 시연: LLM_MODE=rule. 화면에도 규칙 초안으로 표시. 실제 AI 시연으로 설명하지 않는다.
- 녹음: WHISPER_MODEL=small, AUDIO_DIR=/data/audio, API_URL=http://api:8000 (Compose가 주입).
- Discord: DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, GEMINI_API_KEY, LLM_MODEL. 지정 채널이 설정되어야 Flowday 후보 전달이 켜진다. Message Content Intent와 채널 권한 필요.
- 프론트 개발 시 `npm run dev`, Vite가 localhost:8000 API로 프록시한다. `frontend/.env.local`의 VITE_USE_MOCK=true는 UI 독립 개발용이다. Docker 기본은 false.

키/채널 설정 후 `docker compose up -d --build`로 5개 서비스를 실행한다. 현재 테스트에서는 실제 Discord 봇을 가동하지 않았다.

## 남은 작업과 발표 범위

1. **실제 Gemini 응답, 실제 한국어 녹음, Discord 실서버 메시지**는 키/테스트 음성/서버 설정으로 별도 리허설이 필요하다.
2. 회의 메타데이터는 기존 팀 코드의 메모리 저장소를 유지한다. 서버 재시작 시 회의 처리 상태/결과가 사라진다. 음성 파일 볼륨과 승인된 일정 DB는 유지된다. 처리 중 API를 재시작하지 않는 시연은 가능하지만 영속 회의 큐를 완성한 것은 아니다.
3. 실시간 메시지 자동 재시도/실패 큐는 아직 없다. 후보 전송 실패는 로그에 남는다.
4. 새 6개 Actions의 GitHub 성공 기록은 PR 게시 후 확보해야 한다. 로컬 테스트를 원격 Actions 성공으로 대체하지 않는다.
5. 수업에서 사용하지 않은 오픈소스라는 조건은 수업 목록 확인이 필요하다. 현재 구현에 쓰인 **OR-Tools(책 일정 최적화)**와 **faster-whisper(전사)**가 후보이며, 언어·DB 자체는 해당 증거로 세지 않는다.
6. 달력 CRUD/완료/수정/삭제, 텍스트 회의 분석, 후보 생성→검토→승인, DB 볼륨 유지가 현재 검증된 시연 범위다. 일반 목표의 rule 초안은 AI 실호출과 구분한다.
7. 브라우저에서 페이지 이동·일정 편집·새로고침 리허설, 팀원 리뷰, 6개 Actions 로그 캡처를 마친 뒤 발표 버전 PR을 만든다.

## PR 설명 초안

캘린더: 월 이동·날짜 선택·일정 CRUD/완료 UI, 대시보드·일정 모달 및 Nginx 프론트 이미지를 추가한다. 기존 공통 API 함수 계약을 따른다. API가 준비되기 전에는 VITE_USE_MOCK 설정이 필요하다.

통합: React 요청과 기존 백엔드가 연결되지 않아 실제 일정을 저장할 수 없던 문제를 해결한다. PostgreSQL 일정/후보 API를 추가하고 기존 계획·회의·Discord 코드를 연결한다. API 33개/봇 48개/프론트 5개 테스트, 4개 이미지 빌드와 3종 컨테이너 HTTP·볼륨 테스트를 검증했다. 실제 외부 AI/Discord/음성 시연 및 회의 상태 영속화는 남아 있다.

## 전체 수정·추가·삭제 파일

A=추가, M=수정, D=삭제. 삭제한 test.yaml은 내용이 없던 파일이다.

```text
M	.env.example
M	.github/workflows/backend-test.yml
A	.github/workflows/docker-build.yml
M	.github/workflows/frontend-test.yml
A	.github/workflows/integration-test.yml
A	.github/workflows/lint.yml
D	.github/workflows/test.yaml
A	api/app/db.py
M	api/app/main.py
A	api/app/routers/events.py
M	api/app/routers/plan.py
A	api/app/routers/proposals.py
M	api/requirements.txt
A	api/tests/test_integration.py
A	api/tests/test_plan_contract.py
M	discord_bot/main.py
M	docker-compose.yaml
A	docs/INTEGRATION_REVIEW.md
A	frontend/.dockerignore
M	frontend/Dockerfile
A	frontend/nginx.conf
M	frontend/package.json
M	frontend/src/api/client.js
A	frontend/src/components/EventModal.jsx
M	frontend/src/pages/CalendarPage.jsx
M	frontend/src/pages/DashboardPage.jsx
M	frontend/src/pages/MeetingPage.jsx
M	frontend/src/pages/PlanPage.jsx
M	frontend/src/styles/flowday.css
A	frontend/src/utils/calendar.js
A	frontend/tests/calendar.test.js
A	frontend/tests/render.test.js
M	frontend/vite.config.js
M	meeting_worker/main.py
A	scripts/integration_smoke.py
A	scripts/verify_volume.py
```

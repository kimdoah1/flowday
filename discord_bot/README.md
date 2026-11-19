# 일정 인식 디스코드 봇

디스코드 대화를 읽고 **요약 / 확정된 일정 / 참여자 모두 가능한 시간**을 알려주는 봇입니다.
AI는 Google Gemini(무료 등급 사용 가능)를 쓰고, 겹치는 시간 계산은 코드가 합니다. (Flowday 검토함 연동 포함)

## Flowday 통합 실행
프로젝트 루트 `.env`에 `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `GEMINI_API_KEY`를 설정하고 기존 `LLM_MODEL`을 유지합니다.
`DISCORD_CHANNEL_ID`를 설정한 채널의 새 일정 메시지만 Flowday API로 전달됩니다. 비우면 반응·멘션 분석은 가능하지만 검토함 자동 전송은 하지 않습니다.

```bash
docker-compose --env-file .env -p flowday-pr7-test up -d --build --no-deps discord-bot
```

- 메시지 → `/api/ai/extract` → `/api/proposals` → 검토함 승인 → 캘린더 순서입니다.
- 이번 달·다음 달·올해·내년·월말·연말도 감지합니다. 날짜 계산 기준은 메시지를 보낸 한국 날짜입니다.
- 날짜가 없는 기간 요청(예: “이번 달에 회의하자”)은 추출 결과가 없을 때 빈 시간을 추천합니다.
- 추천은 **규칙 기반**으로 해당 기간의 평일 09~18시 중 현재 이후 첫 빈 1시간을 찾습니다. 확정 일정과 검토 대기 후보를 모두 피합니다. 제목에 `[시간 추천]`을 표시하며 승인 전에는 실제 일정이 아닙니다.
- 명시된 날짜·시간, 주말 조건, 마감·취소 등은 이 기본 추천으로 덮어쓰지 않습니다. 지원하지 않는 조건은 추천이 없을 수 있습니다.
- 프론트 검토함과 메뉴 숫자는 5초마다 서버의 대기 후보를 확인합니다. 대기 후보가 없으면 숫자가 표시되지 않습니다.

## 사용법
| 하는 일 | 방법 |
|---|---|
| 일정 분석 | 채널에서 봇을 `@멘션` (최근 7일, 최대 200개 메시지를 읽음) |
| 새 일정 논의 시작 | `!초기화` 또는 `@봇 초기화` → 이 시점 이전 대화는 분석에서 제외 |
| 일정 인식 표시 | 일정처럼 보이는 메시지에 봇이 📅 반응을 붙임 |

예) "다음 주 월요일 오후 2시~6시 가능해요" / "저는 월요일 16시 전엔 안 돼요" → `@봇`

시간 표현(오후 2시, 14시, 2PM, 오후 6시 반 …)은 AI에 보내기 전에 코드가 `14:00` 형식으로 통일합니다.
오전/오후를 안 쓰면 1~6시는 오후, 7~11시는 오전으로 봅니다.

## 처음 설치
1. **Discord Developer Portal** → 앱 생성 → Bot → **Message Content Intent 켜기**, 토큰 복사
2. OAuth2 → URL Generator: `bot` 선택, 권한 `View Channels`, `Send Messages`, `Read Message History`, `Add Reactions` → 생성된 URL로 서버에 초대
3. https://aistudio.google.com/apikey 에서 Gemini API 키 발급
4. 설정 파일 만들기: `.env.example`을 복사해 `.env`로 이름을 바꾸고 값 입력
5. 실행
   ```
   cd discord_bot
   pip install -r requirements.txt
   python main.py
   ```
   로그에 `로그인 완료`, `AI 모델 준비됨`이 뜨면 성공

## 환경 변수 (.env)
| 이름 | 필수 | 설명 |
|---|---|---|
| `DISCORD_BOT_TOKEN` | ✅ | 디스코드 봇 토큰 |
| `GEMINI_API_KEY` | ✅ | Gemini API 키 |
| `DISCORD_CHANNEL_ID` | | 반응할 채널 ID (비우면 모든 채널) |
| `LLM_MODEL` | | 비우면 `gemini-2.5-flash` |
| `RESET_STATE_PATH` | | 초기화 기록 파일 위치 (기본 `reset_state.json`) |

`.env`는 절대 GitHub에 올리지 마세요. (`.gitignore`에 등록되어 있음)

## 업데이트 적용 방법
1. 실행 중인 봇을 끈다 (터미널에서 `Ctrl+C`)
2. 새 파일로 교체한다. **`.env`와 `reset_state.json`은 덮어쓰지 말고 그대로 둔다**
3. `pip install -r requirements.txt` 실행 (새 라이브러리가 있을 수 있음)
4. `.env.example`에 새 항목이 생겼다면 `.env`에도 추가한다
5. `python main.py`로 다시 실행하고, 로그에 `로그인 완료` / `AI 모델 준비됨`이 뜨는지 확인한다

디스코드 쪽 설정(토큰, 서버 초대)은 다시 할 필요가 없습니다. 봇은 코드를 다시 실행해야만 새 버전이 적용됩니다.
(단, 권한을 새로 요구하는 업데이트라면 초대 URL을 다시 만들어 재초대해야 합니다.)

Git 팀 저장소를 쓴다면: `git switch develop && git pull` → `feature/` 브랜치에서 파일 교체 → 커밋 → PR → 병합 후 위 3~5단계.
Docker로 돌린다면: `docker build -t schedule-bot discord_bot` → 기존 컨테이너 중지·삭제 → `docker run -d --env-file discord_bot/.env schedule-bot`.
(Docker에서는 `reset_state.json`이 컨테이너를 새로 만들면 사라지니 볼륨으로 연결하세요.)

## 테스트
```
cd discord_bot
pytest -v
```
AI·디스코드 없이 가짜 응답으로 시간 정규화, 겹치는 시간 계산, 결과 검증, 초기화 저장, Gemini 응답 파싱을 검사합니다.

## 문제 해결
| 증상 | 확인할 것 |
|---|---|
| 봇이 오프라인 | `python main.py`가 켜져 있는지, 토큰이 맞는지 |
| 멘션해도 반응 없음 | Message Content Intent, `Read Message History` 권한, `DISCORD_CHANNEL_ID` |
| "AI 모델을 쓸 수 없어요" | `GEMINI_API_KEY`, 모델 이름, 무료 한도 (로그 확인) |
| 시간이 틀리게 나옴 | 날짜+시간을 또렷하게 쓰기, `!초기화`로 이전 대화 분리 |

## 개인정보 안내
멘션할 때마다 최근 대화가 Google Gemini API로 전송됩니다. 무료 등급에서는 입력 내용이 Google 제품 개선에 사용될 수 있으니 서버 참여자에게 미리 알려주세요.

## 구조
```
discord_bot/
├─ main.py        봇 본체 (멘션·초기화·📅 반응)
├─ analyzer.py    대화 → AI가 사람별 가능/불가 시간 추출
├─ timeparse.py   시간 표현 정규화
├─ validator.py   추출 결과 검증 + 충돌 확인
├─ scheduler.py   겹치는 시간 계산
├─ report.py      답장 문구 생성
├─ llm.py         Gemini 호출
├─ state.py       채널별 초기화 시점 저장
├─ filter.py      일정 같은 메시지 판별
├─ tests/         테스트
└─ flowday_later/ Flowday API 클라이언트와 독립 테스트
```

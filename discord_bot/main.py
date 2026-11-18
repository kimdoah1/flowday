"""일정 인식 디스코드 봇 (Flowday 연동 전, 디스코드 안에서만 동작).

- 일정처럼 보이는 메시지에는 📅 반응을 달아 '인식했다'고 알린다.
- 봇을 @멘션하면 최근 대화를 읽고 요약 / 확정 일정 / 모두 가능한 시간을 답장한다.
- `!초기화` (또는 @봇 초기화): 이 시점 이전 대화는 무시하고 새 일정 논의를 시작한다.
"""
import logging
import os
import re
from datetime import datetime, timedelta

import discord
from dotenv import load_dotenv

from analyzer import ChatLine, analyze, build_transcript
from filter import is_schedule_message
from llm import DEFAULT_MODEL, GeminiClient, LLMError
from report import build_reply, split_message
from scheduler import KST
from state import ResetStore
from validator import finalize

load_dotenv()  # 같은 폴더(또는 상위 폴더)의 .env 파일을 읽는다. Docker에서는 compose가 주입하므로 없어도 된다.

# ---- 환경 변수 (.env) ----
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID") or 0)  # 비우면 봇이 볼 수 있는 모든 채널
LLM_MODEL = os.environ.get("LLM_MODEL") or DEFAULT_MODEL  # Gemini 모델 이름

# ---- 설정 ----
HISTORY_LIMIT = 200               # 멘션 시 읽을 최대 메시지 수
HISTORY_DAYS = 7                  # 최근 며칠 치 대화를 읽을지
REACT_TO_SCHEDULE_MESSAGES = True # 일정 같은 메시지에 📅 반응 달기
RESET_COMMANDS = {"!초기화", "!reset"}
RESET_WORDS = {"초기화", "리셋", "reset"}  # @봇 초기화

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("schedule_bot")

intents = discord.Intents.default()
intents.message_content = True  # Developer Portal에서도 켜 둬야 한다
NO_PING = discord.AllowedMentions.none()


class ScheduleBot(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = GeminiClient()  # GEMINI_API_KEY 환경 변수를 읽는다
        self.resets = ResetStore()  # 채널별 초기화 시점
        self.busy: set[int] = set() # 분석 중인 채널 (같은 채널 동시 요청 방지)

    async def on_ready(self):
        log.info("로그인 완료: %s", self.user)
        problem = await self.llm.check(LLM_MODEL)  # API 키·모델 준비 여부 확인
        if problem:
            log.warning("AI 모델 문제: %s", problem)
        else:
            log.info("AI 모델 준비됨: %s", LLM_MODEL)

    async def close(self):
        await self.llm.aclose()
        await super().close()

    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if DISCORD_CHANNEL_ID and message.channel.id != DISCORD_CHANNEL_ID:
            return

        mentioned = self.user in message.mentions
        request = re.sub(r"<@!?\d+>", "", message.content).strip()

        # 초기화: 이후 분석에서는 이 메시지 이전의 대화를 읽지 않는다
        if message.content.strip().lower() in RESET_COMMANDS or (
            mentioned and request.lower() in RESET_WORDS
        ):
            self.resets.set(message.channel.id, message.created_at)
            await message.reply("🔄 초기화했어요. 지금부터 나오는 대화만 새 일정으로 분석할게요.",
                                allowed_mentions=NO_PING)
            return

        if mentioned:
            await self.handle_mention(message, request)
        elif REACT_TO_SCHEDULE_MESSAGES and is_schedule_message(message.content):
            try:
                await message.add_reaction("📅")
            except discord.HTTPException:
                pass  # 반응 권한이 없어도 봇은 계속 동작

    async def handle_mention(self, message: discord.Message, request: str):
        channel = message.channel
        if channel.id in self.busy:
            await message.reply("아직 이전 요청을 분석 중이에요. 잠시만 기다려 주세요!",
                                allowed_mentions=NO_PING)
            return
        self.busy.add(channel.id)
        try:
            async with channel.typing():
                now = datetime.now(KST)

                # 읽을 대화의 시작점: 최근 N일, 초기화가 있었다면 그 이후만
                default_after = discord.utils.utcnow() - timedelta(days=HISTORY_DAYS)
                reset_at = self.resets.get(channel.id)
                after = max(default_after, reset_at) if reset_at else default_after
                since = reset_at if reset_at and reset_at > default_after else None

                lines: list[ChatLine] = []
                async for m in channel.history(limit=HISTORY_LIMIT, after=after, oldest_first=True):
                    if m.author.bot or m.id == message.id or not m.content.strip():
                        continue
                    lines.append(ChatLine(m.created_at.astimezone(KST),
                                          m.author.display_name, m.clean_content))
                if not lines:
                    await message.reply(
                        "분석할 대화가 없어요." + (" (초기화 이후 새 대화가 아직 없어요)" if since else ""),
                        allowed_mentions=NO_PING)
                    return

                transcript, authors = build_transcript(lines)
                analysis = await analyze(self.llm, LLM_MODEL, transcript, request, now)
                result = finalize(analysis, now)  # 검증 + 겹치는 시간 계산 + 재검증
                text = build_reply(result, authors, since=since)

            for i, chunk in enumerate(split_message(text)):
                if i == 0:
                    await message.reply(chunk, allowed_mentions=NO_PING)
                else:
                    await channel.send(chunk, allowed_mentions=NO_PING)
        except LLMError as e:
            log.error("AI 모델 오류: %s", e)
            await message.reply(f"AI 모델을 쓸 수 없어요: {e}",
                                allowed_mentions=NO_PING)
        except Exception:
            log.exception("일정 분석 실패")
            await message.reply("일정을 분석하는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
                                allowed_mentions=NO_PING)
        finally:
            self.busy.discard(channel.id)


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN을 .env에 설정하세요.")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("GEMINI_API_KEY를 .env에 설정하세요. (https://aistudio.google.com/apikey 에서 무료 발급)")
    ScheduleBot(intents=intents).run(DISCORD_BOT_TOKEN)

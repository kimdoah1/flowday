"""채널별 '초기화 시점'을 저장한다. 이 시점 이전의 대화는 분석에서 제외된다."""
import json
import os
from datetime import datetime
from pathlib import Path

from scheduler import KST


class ResetStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.environ.get("RESET_STATE_PATH", "reset_state.json"))
        self.data: dict[str, str] = {}
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}  # 파일이 없거나 깨졌으면 빈 상태로 시작

    def get(self, channel_id: int) -> datetime | None:
        value = self.data.get(str(channel_id))
        try:
            return datetime.fromisoformat(value).astimezone(KST) if value else None
        except ValueError:
            return None

    def set(self, channel_id: int, when: datetime) -> None:
        self.data[str(channel_id)] = when.astimezone(KST).isoformat()
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # 저장에 실패해도 메모리에서는 계속 동작한다

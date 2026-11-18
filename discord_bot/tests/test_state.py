import tempfile
from datetime import datetime
from pathlib import Path

from scheduler import KST
from state import ResetStore


def test_reset_persists_across_restart():
    with tempfile.TemporaryDirectory() as d:
        path = str(Path(d) / "s.json")
        when = datetime(2026, 11, 7, 15, 30, tzinfo=KST)
        store = ResetStore(path)
        assert store.get(1) is None
        store.set(1, when)
        assert ResetStore(path).get(1) == when   # 다시 켜도 유지
        assert ResetStore(path).get(2) is None   # 다른 채널은 영향 없음


def test_corrupted_file_is_ignored():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "s.json"
        path.write_text("{깨진 파일", encoding="utf-8")
        assert ResetStore(str(path)).get(1) is None

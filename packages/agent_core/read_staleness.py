from __future__ import annotations

from pathlib import Path


class CampaignReadStalenessTracker:
    """Drop campaign context file reads when workspace mtime advances."""

    def __init__(self) -> None:
        self._snapshots: dict[str, float] = {}

    def note_read(self, path: Path) -> None:
        key = str(path.resolve())
        try:
            self._snapshots[key] = path.stat().st_mtime
        except OSError:
            return

    def is_stale(self, path: Path) -> bool:
        key = str(path.resolve())
        prior = self._snapshots.get(key)
        if prior is None:
            return False
        try:
            return path.stat().st_mtime > prior
        except OSError:
            return True

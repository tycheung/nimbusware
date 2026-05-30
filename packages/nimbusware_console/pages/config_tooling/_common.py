from __future__ import annotations

import os
from pathlib import Path

from nimbusware_console.pages import _state as rl
from nimbusware_console.settings import API_BASE


def _resolve_prune_status_path() -> Path | None:
    raw = os.environ.get("HERMES_PRUNE_STATUS_PATH", "").strip()
    return Path(raw).expanduser() if raw else None

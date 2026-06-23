from __future__ import annotations

import base64
import os
import time
from datetime import datetime
from pathlib import Path


def urlsafe_b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def restore_b64_padding(value: str) -> str:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return value + pad


def set_mtime_days_ago(path: Path, *, days_ago: float) -> None:
    ts = time.time() - days_ago * 86400
    os.utime(path, (ts, ts))


def set_mtime_to(path: Path, when: datetime) -> None:
    ts = when.timestamp()
    os.utime(path, (ts, ts))

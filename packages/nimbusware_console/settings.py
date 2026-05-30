"""Shared console settings (API base URL, repo root)."""

from __future__ import annotations

import os
from pathlib import Path


def default_api_base() -> str:
    return os.environ.get("NIMBUSWARE_API_BASE", "http://127.0.0.1:8000/v1")


API_BASE = default_api_base()


def repo_root() -> Path:
    return Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()

from __future__ import annotations

import os
from typing import Any

from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

DEFAULT_E2E_ENV: dict[str, str] = {
    "NIMBUSWARE_SKIP_PREFLIGHT": "1",
    "NIMBUSWARE_USE_LLM": "0",
    "NIMBUSWARE_SLICE_IMPLEMENT": "stub",
    "NIMBUSWARE_SLICE_AUTO_ADVANCE": "0",
    "NIMBUSWARE_SLICE_P3_EVIDENCE": "0",
    "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
    "NIMBUSWARE_ADMIN_TOKEN": DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
}


def apply_e2e_unit_profile(
    monkeypatch: Any,
    *,
    repo_root: str | None = None,
    extra: dict[str, str] | None = None,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_SLICE_E2E_COMMAND", raising=False)
    for key, value in DEFAULT_E2E_ENV.items():
        monkeypatch.setenv(key, value)
    if repo_root is not None:
        monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", repo_root)
    if extra:
        for key, value in extra.items():
            monkeypatch.setenv(key, value)


def journey_env_summary() -> str:
    keys = (
        "NIMBUSWARE_REPO_ROOT",
        "NIMBUSWARE_SLICE_IMPLEMENT",
        "NIMBUSWARE_DATABASE_URL",
    )
    parts = [f"{k}={os.environ.get(k, '')!r}" for k in keys]
    return "env_profile=local " + " ".join(parts)

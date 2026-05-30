"""First-run onboarding state (fo308)."""

from __future__ import annotations

import os
from pathlib import Path

SESSION_ONBOARDED = "maker_onboarded"
SESSION_WIZARD_STEP = "maker_wizard_step"


def is_onboarded(session_state: object) -> bool:
    get = getattr(session_state, "get", None)
    if callable(get) and get(SESSION_ONBOARDED):
        return True
    flag_file = onboarding_flag_path()
    return flag_file.is_file()


def mark_onboarded(session_state: object) -> None:
    setattr(session_state, SESSION_ONBOARDED, True)
    flag = onboarding_flag_path()
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("1\n", encoding="utf-8")


def onboarding_flag_path() -> Path:
    base = os.environ.get("NIMBUSWARE_MAKER_STATE_DIR", "").strip()
    root = Path(base) if base else Path(".cache/nimbusware_maker")
    return root.resolve() / "onboarded"

from __future__ import annotations

from pathlib import Path

from nimbusware_console.operator_chat_core import ChatState, process_user_message

__all__ = ["ChatState", "process_user_message", "render_operator_chat"]


def render_operator_chat(*, repo_root: Path | None = None) -> None:
    raise RuntimeError("Operator chat UI moved to /v1/admin/app/ (Preact).")

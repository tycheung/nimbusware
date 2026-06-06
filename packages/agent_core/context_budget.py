"""Shared truncation policy for LLM prompts and summarized projections.

Call sites that feed secondary LLM stages or tool history should use
``truncate_for_llm_history``. Active read tool results use
``truncate_for_active_read``. Shell output uses ``truncate_shell_output``.
"""

from __future__ import annotations

import re

_ELLIPSIS = "..."
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    suffix_len = len(_ELLIPSIS)
    return text[: max(0, limit - suffix_len)] + _ELLIPSIS


def truncate_for_llm_history(text: str, *, max_chars: int | None = None) -> str:
    """Bound text entering secondary LLM stages or message history (default 2k)."""
    cap = max_chars if max_chars is not None else _default_llm_history_max_chars()
    return _truncate(text, cap)


def truncate_for_active_read(text: str, *, max_chars: int | None = None) -> str:
    """Bound active read-tool content shown to the model (default 16k)."""
    cap = max_chars if max_chars is not None else _default_read_max_chars()
    return _truncate(text, cap)


def strip_ansi(text: str) -> str:
    """Remove terminal ANSI escape sequences for LLM-facing shell output."""
    return _ANSI_ESCAPE.sub("", text)


def truncate_shell_output(text: str, *, max_chars: int | None = None) -> str:
    """Bound shell command output in agent tool results (default 4k)."""
    cap = max_chars if max_chars is not None else _default_shell_output_max_chars()
    return _truncate(text, cap)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4 heuristic)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _default_llm_history_max_chars() -> int:
    from nimbusware_env.env_flags import nimbusware_llm_history_max_chars

    return nimbusware_llm_history_max_chars()


def _default_read_max_chars() -> int:
    from nimbusware_env.env_flags import nimbusware_read_max_chars

    return nimbusware_read_max_chars()


def _default_shell_output_max_chars() -> int:
    from nimbusware_env.env_flags import nimbusware_shell_output_max_chars

    return nimbusware_shell_output_max_chars()

from __future__ import annotations

from agent_core.context_budget import (
    estimate_tokens,
    truncate_for_active_read,
    truncate_for_llm_history,
    truncate_shell_output,
)


def test_truncate_for_llm_history_at_boundary() -> None:
    text = "x" * 2000
    assert truncate_for_llm_history(text, max_chars=2000) == text
    assert truncate_for_llm_history(text + "extra", max_chars=2000).endswith("...")
    assert len(truncate_for_llm_history(text + "extra", max_chars=2000)) == 2000


def test_truncate_for_active_read_at_boundary() -> None:
    text = "y" * 16000
    assert truncate_for_active_read(text, max_chars=16000) == text
    result = truncate_for_active_read(text + "more", max_chars=16000)
    assert result.endswith("...")
    assert len(result) == 16000


def test_truncate_shell_output_at_boundary() -> None:
    text = "z" * 4000
    assert truncate_shell_output(text, max_chars=4000) == text
    result = truncate_shell_output(text + "tail", max_chars=4000)
    assert result.endswith("...")
    assert len(result) == 4000


def test_truncate_empty_input() -> None:
    assert truncate_for_llm_history("") == ""
    assert truncate_for_active_read("") == ""
    assert truncate_shell_output("") == ""


def test_truncate_zero_limit() -> None:
    assert truncate_for_llm_history("hello", max_chars=0) == "hello"


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 8) == 2

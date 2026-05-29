"""Operator chat helpers (fo150)."""

from __future__ import annotations

from nimbusware_console.operator_chat import process_user_message


def test_help_command() -> None:
    reply = process_user_message("/help")
    assert reply is not None
    assert "/run" in reply


def test_natural_language_fallback() -> None:
    reply = process_user_message("hello there")
    assert "micro_slice" in reply or "/run" in reply

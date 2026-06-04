"""Operator chat helpers."""

from __future__ import annotations

from nimbusware_console.operator_chat_core import ChatState, process_user_message


def test_help_command() -> None:
    reply = process_user_message("/help", ChatState())
    assert "/run" in reply


def test_natural_language_fallback() -> None:
    reply = process_user_message("hello there", ChatState())
    assert "micro_slice" in reply or "/run" in reply

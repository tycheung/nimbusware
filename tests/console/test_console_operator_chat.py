from __future__ import annotations

from unittest.mock import MagicMock

from nimbusware_console.operator_chat_core import ChatState, process_user_message


def test_help_command() -> None:
    reply = process_user_message("/help", ChatState())
    assert "/run" in reply


def test_natural_language_classify_suggestion(monkeypatch) -> None:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "classification": {
            "work_type": "patch",
            "confidence": 0.91,
            "rationale": "Small bug-fix scope",
        },
    }
    monkeypatch.setattr(
        "nimbusware_console.operator_chat_core.chat_svc.classify_intent",
        lambda _msg: resp,
    )
    state = ChatState()
    reply = process_user_message("fix the failing login test", state)
    assert "patch" in reply
    assert state.suggested_profile == "patch"
    assert "/run auto" in reply


def test_run_auto_uses_suggested_profile(monkeypatch) -> None:
    run_resp = MagicMock()
    run_resp.status_code = 200
    run_resp.json.return_value = {"run_id": "00000000-0000-4000-8000-000000000099"}
    monkeypatch.setattr(
        "nimbusware_console.operator_chat_core.chat_svc.create_run",
        lambda payload: run_resp,
    )
    state = ChatState(suggested_profile="patch")
    reply = process_user_message("/run auto", state)
    assert "Started run" in reply

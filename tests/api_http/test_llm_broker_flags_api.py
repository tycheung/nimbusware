from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes import chat as chat_routes
from api.routes.chat_common import ClassifyIntentBody


def _broker_miss_exc() -> RuntimeError:
    return RuntimeError(
        "broker_miss: intent_classifier: LLM classification unavailable under "
        "NIMBUSWARE_BROKER_LLM=1|2"
    )


def test_classify_under_llm_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-b: classify returns broker_miss body under LLM=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    body = ClassifyIntentBody(message="fix bug in login")
    with patch("api.routes.chat.classify_intent", side_effect=_broker_miss_exc()):
        out = chat_routes.classify_chat_intent(
            body,
            project_store=MagicMock(),
            _user=MagicMock(),
        )
    payload = out.model_dump()
    assert payload.get("via") == "broker_miss"
    assert payload.get("feature") == "intent_classifier"
    assert payload.get("status") == "degraded"
    assert payload.get("classification") == {}


def test_classify_under_llm_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-b: classify maps broker failure to 503 under LLM=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    body = ClassifyIntentBody(message="fix bug in login")
    with (
        patch("api.routes.chat.classify_intent", side_effect=_broker_miss_exc()),
        pytest.raises(HTTPException) as ei,
    ):
        chat_routes.classify_chat_intent(
            body,
            project_store=MagicMock(),
            _user=MagicMock(),
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_llm_unavailable"

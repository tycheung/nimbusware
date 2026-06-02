from __future__ import annotations

import logging
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.llm.test_writer_role_critique import (
    emit_stub_test_writer_critique_panel,
    execute_test_writer_critique_llm,
)
from hermes_orchestrator.registry import RoleRegistry
from hermes_store.memory import InMemoryEventStore
from nimbusware_api.app import app

_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def _router() -> UniversalCritiqueRouter:
    return UniversalCritiqueRouter.from_yaml(_ROOT / "configs" / "personas" / "critique_pairings.yaml")


def test_request_log_includes_request_id(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="nimbusware_api.request")
    client = TestClient(app)
    client.get("/v1/platform/edition", headers={"X-Request-Id": "log-req-99"})
    assert any("request_id=log-req-99" in rec.message for rec in caplog.records)


def test_emit_stub_test_writer_role_critique_panel_appends_events() -> None:
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = _router()
    run_id = uuid4()
    emit_stub_test_writer_critique_panel(store, registry, router, run_id=run_id)
    rows = store.list_run_events(str(run_id))
    assert len(rows) >= 2


def test_execute_test_writer_role_critique_llm_success() -> None:
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()

    def good(**_: object) -> dict[str, object]:
        return {
            "critics": [
                {
                    "tax_key": "product_reference_critic",
                    "verdict": "PASS",
                    "severity": "LOW",
                    "is_in_domain": True,
                    "evidence_refs": ["t"],
                },
                {
                    "tax_key": "domain_critic",
                    "verdict": "PASS",
                    "severity": "LOW",
                    "is_in_domain": True,
                },
            ],
            "gate": {"verdict": "PASS"},
        }

    with patch("hermes_orchestrator.llm_plan.ollama_chat_json", side_effect=good):
        ok = execute_test_writer_critique_llm(
            store,
            registry,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=0,
            log_snippet="ok",
            timeout_seconds=1.0,
        )
    assert ok is True
    assert len(store.list_run_events(str(run_id))) >= 2


def test_lane_v2_config_notify_smoke() -> None:
    from nimbusware_config.notify import (
        ConfigDocumentUpdated,
        encode_notify_payload,
        parse_notify_payload,
    )

    payload = encode_notify_payload(namespace="workflows", document_key="default", version=1)
    parsed = parse_notify_payload(payload)
    assert parsed == ConfigDocumentUpdated(namespace="workflows", document_key="default", version=1)
    assert parse_notify_payload("") is None
    assert parse_notify_payload("{not json") is None

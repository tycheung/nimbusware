from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx

from env import find_repo_root
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.llm import (
    execute_implementation_critique_llm,
    execute_plan_stage_llm,
    execute_planner_critique_llm,
    execute_test_writer_critique_llm,
)
from orchestrator.registry import RoleRegistry
from store.memory import InMemoryEventStore

_MOCK_RESOLVER_CHAT = "orchestrator.routing.resolver.ModelBindingResolver.chat_json"
ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])
CRITIQUE_PAIRINGS_YAML = ROOT / "configs" / "personas" / "critique_pairings.yaml"


def _router() -> UniversalCritiqueRouter:
    return UniversalCritiqueRouter.from_yaml(CRITIQUE_PAIRINGS_YAML)


def test_llm_invalid_shape_emits_stub_plan() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    run_id = uuid4()

    def bad_json(**_: object) -> dict[str, object]:
        return {"critics": [], "gate": {"verdict": "PASS"}}

    with patch(_MOCK_RESOLVER_CHAT, side_effect=bad_json):
        execute_plan_stage_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            timeout_seconds=1.0,
        )
    types = [r["event_type"] for r in store.list_run_events(str(run_id))]
    assert types.count("critic.verdict.emitted") == 2
    assert "gate.decision.emitted" in types


def test_llm_http_error_emits_stub_plan() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    run_id = uuid4()

    def boom(**_: object) -> dict[str, object]:
        raise httpx.ConnectError("no server")

    with patch(_MOCK_RESOLVER_CHAT, side_effect=boom):
        execute_plan_stage_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            timeout_seconds=1.0,
        )
    rows = store.list_run_events(str(run_id))
    assert any(r["event_type"] == "gate.decision.emitted" for r in rows)


def test_llm_valid_json_records_critics() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
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

    with patch(_MOCK_RESOLVER_CHAT, side_effect=good):
        execute_plan_stage_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            timeout_seconds=1.0,
        )
    critics = [
        r for r in store.list_run_events(str(run_id)) if r["event_type"] == "critic.verdict.emitted"
    ]
    assert len(critics) == 2
    assert all((r.get("payload") or {}).get("evidence_refs") for r in critics)


def test_implementation_critique_llm_invalid_shape_returns_false() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    run_id = uuid4()

    def bad_json(**_: object) -> dict[str, object]:
        return {"critics": [], "gate": {"verdict": "PASS"}}

    with patch(_MOCK_RESOLVER_CHAT, side_effect=bad_json):
        ok = execute_implementation_critique_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=1,
            log_snippet="error line",
            timeout_seconds=1.0,
        )
    assert ok is False
    assert not store.list_run_events(str(run_id))


def test_implementation_critique_llm_records_events() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
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

    with patch(
        "orchestrator.llm.common.ollama_chat_json_via_plan_patch",
        side_effect=good,
    ):
        ok = execute_implementation_critique_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=0,
            log_snippet="pytest ok",
            timeout_seconds=1.0,
        )
    assert ok is True
    rows = store.list_run_events(str(run_id))
    assert any(
        (r.get("payload") or {}).get("stage_name") == "implementation.critique"
        for r in rows
        if r.get("event_type") == "stage.started"
    )
    gates = [
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "implementation.critique"
    ]
    assert len(gates) == 1


def test_test_writer_critique_llm_invalid_shape_returns_false() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    run_id = uuid4()

    def bad_json(**_: object) -> dict[str, object]:
        return {"critics": [], "gate": {"verdict": "PASS"}}

    with patch(_MOCK_RESOLVER_CHAT, side_effect=bad_json):
        ok = execute_test_writer_critique_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=1,
            log_snippet="error line",
            timeout_seconds=1.0,
        )
    assert ok is False
    assert not store.list_run_events(str(run_id))


def test_test_writer_critique_llm_records_events() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
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

    with patch(
        "orchestrator.llm.common.ollama_chat_json_via_plan_patch",
        side_effect=good,
    ):
        ok = execute_test_writer_critique_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=0,
            log_snippet="pytest ok",
            timeout_seconds=1.0,
        )
    assert ok is True
    rows = store.list_run_events(str(run_id))
    assert any(
        (r.get("payload") or {}).get("stage_name") == "test_writer.critique"
        for r in rows
        if r.get("event_type") == "stage.started"
    )
    gates = [
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "test_writer.critique"
    ]
    assert len(gates) == 1


def test_planner_critique_llm_invalid_shape_returns_false() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    run_id = uuid4()

    def bad_json(**_: object) -> dict[str, object]:
        return {"critics": [], "gate": {"verdict": "PASS"}}

    with patch(_MOCK_RESOLVER_CHAT, side_effect=bad_json):
        ok = execute_planner_critique_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=1,
            log_snippet="error line",
            timeout_seconds=1.0,
        )
    assert ok is False
    assert not store.list_run_events(str(run_id))


def test_planner_critique_llm_records_events() -> None:
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
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

    with patch(
        "orchestrator.llm.common.ollama_chat_json_via_plan_patch",
        side_effect=good,
    ):
        ok = execute_planner_critique_llm(
            store,
            reg,
            _router(),
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=0,
            log_snippet="pytest ok",
            timeout_seconds=1.0,
        )
    assert ok is True
    rows = store.list_run_events(str(run_id))
    assert any(
        (r.get("payload") or {}).get("stage_name") == "planner.critique"
        for r in rows
        if r.get("event_type") == "stage.started"
    )
    gates = [
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "planner.critique"
    ]
    assert len(gates) == 1

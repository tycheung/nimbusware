from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from orchestrator.llm.slice_facade import (
    _require_broker_chat,
    execute_slice_plan_llm,
    execute_slice_replan_llm,
)
from orchestrator.slice.micro_slice import parse_slice_plan

_ROOT = Path(__file__).resolve().parents[2]


def test_sak497_a_slice_facade_peel_strict_wiring() -> None:
    """sak497-a: plan/replan use _require_broker_chat + peel_strict."""
    src = (_ROOT / "packages" / "orchestrator" / "llm" / "slice_facade.py").read_text(
        encoding="utf-8",
    )
    assert "sak497-a" in src
    assert "def execute_slice_plan_llm" in src
    assert "def execute_slice_replan_llm" in src
    assert "_require_broker_chat" in src
    assert "peel_strict=True" in src
    assert (
        "raise RuntimeError"
        not in src.split("execute_slice_plan_llm")[1].split("execute_slice_implement_llm")[0]
    )


def test_execute_slice_plan_llm_parses_broker_response() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "custom_agent": {
                    "system_prompt_preview": "You are a test planner.",
                },
            },
        },
    ]
    fake = {
        "slice_id": "slice-llm-1",
        "rationale": "touch api",
        "target_paths": ["packages/api/app.py"],
        "acceptance_criteria": "tests pass",
    }
    with patch(
        "orchestrator.llm.slice_facade._require_broker_chat",
        return_value=fake,
    ):
        plan = execute_slice_plan_llm(
            rows=rows,
            base_url="http://localhost:11434",
            model_id="test-model",
            slice_index=1,
        )
    assert plan is not None
    assert plan.slice_id == "slice-llm-1"
    assert plan.target_paths[0].endswith("app.py")


def test_execute_slice_plan_llm_returns_none_on_failure_when_llm_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    with patch(
        "orchestrator.llm.slice_facade._require_broker_chat",
        side_effect=RuntimeError("down"),
    ):
        plan = execute_slice_plan_llm(
            rows=[],
            base_url="http://localhost:11434",
            model_id="test-model",
        )
    assert plan is None


def test_execute_slice_plan_llm_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    with patch(
        "orchestrator.llm.slice_facade._require_broker_chat",
        side_effect=RuntimeError("broker_miss: chat_facade"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_slice_plan_llm(
                rows=[],
                base_url="http://localhost:11434",
                model_id="test-model",
            )


def test_execute_slice_replan_llm_parses_broker_response() -> None:
    prior = parse_slice_plan(
        {
            "slice_id": "slice-1",
            "target_paths": ["a.py", "b.py", "c.py", "d.py"],
        },
    )
    fake = {
        "slice_id": "slice-1-r1",
        "rationale": "narrower",
        "target_paths": ["a.py", "b.py"],
        "acceptance_criteria": "tests pass",
    }
    with patch(
        "orchestrator.llm.slice_facade._require_broker_chat",
        return_value=fake,
    ):
        sub = execute_slice_replan_llm(
            rows=[],
            base_url="http://localhost:11434",
            model_id="test-model",
            prior_plan=prior,
            budget_message="too many files",
            replan_attempt=1,
        )
    assert sub is not None
    assert sub.slice_id == "slice-1-r1"
    assert len(sub.target_paths) == 2


def test_require_broker_chat_forwards_peel_strict() -> None:
    with patch(
        "orchestrator.llm.slice_facade.ollama_chat_json_via_plan_patch",
        return_value={"ok": True},
    ) as chat:
        out = _require_broker_chat(
            [{"role": "user", "content": "x"}],
            base_url="http://ollama",
            model="m",
        )
    assert out == {"ok": True}
    assert chat.call_args.kwargs.get("peel_strict") is True


# --- sak497-b: lifecycle plan stage chat_facade peel_strict ---


def test_sak497_b_source_markers() -> None:
    """sak497-b: plan stage uses chat_facade peel_strict; lifecycle keeps peel guards."""
    plan_stage = (_ROOT / "packages" / "orchestrator" / "llm" / "gate_helpers.py").read_text(
        encoding="utf-8",
    )
    lifecycle_plan = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "lifecycle_plan.py"
    ).read_text(encoding="utf-8")
    llm_init = (_ROOT / "packages" / "orchestrator" / "llm" / "__init__.py").read_text(
        encoding="utf-8",
    )
    assert "sak497-b" in plan_stage
    assert "peel_strict=True" in plan_stage
    assert "execute_plan_stage_llm" in plan_stage
    assert "ollama_chat_json_via_plan_patch" in plan_stage
    assert "sak497-b" in lifecycle_plan
    assert "broker_llm_enabled()" in lifecycle_plan
    assert "from orchestrator.llm.gate_helpers import" in llm_init
    assert "execute_plan_stage_llm" in llm_init


def test_sak497_b_peel_broker_miss_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-b: LLM=1 — broker miss from plan LLM propagates (no stub fallback)."""
    from collections.abc import Iterator
    from contextlib import contextmanager
    from typing import Any
    from unittest.mock import MagicMock
    from uuid import uuid4

    from orchestrator.pipeline import make_dev_orchestrator

    @contextmanager
    def _patched_plan_stage(
        orch: Any,
        *,
        llm_raises: BaseException,
    ) -> Iterator[tuple[MagicMock, MagicMock]]:
        with (
            patch.object(orch, "_maybe_emit_research_stages"),
            patch.object(orch, "_maybe_emit_stitch_stages"),
            patch.object(orch, "_run_created_metadata", return_value={}),
            patch(
                "research.reresearch.maybe_reresearch_after_plan_fail",
                return_value=False,
            ),
            patch.object(orch, "_selected_model_for_run", return_value="dev:primary"),
            patch(
                "orchestrator._pipeline.lifecycle_plan.execute_plan_stage_llm",
                side_effect=llm_raises,
            ) as mock_llm,
            patch(
                "orchestrator._pipeline.lifecycle_plan.emit_stub_plan_stage",
            ) as mock_stub,
        ):
            yield mock_llm, mock_stub

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=RuntimeError("broker_miss: chat_facade: down"),
    ) as (_mock_llm, mock_stub):
        with pytest.raises(RuntimeError, match="broker_miss"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


def test_sak497_b_peel_invalid_llm_no_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-b: LLM=2 — invalid LLM payload propagates (no stub fallback)."""
    from collections.abc import Iterator
    from contextlib import contextmanager
    from typing import Any
    from unittest.mock import MagicMock
    from uuid import uuid4

    from orchestrator.pipeline import make_dev_orchestrator

    @contextmanager
    def _patched_plan_stage(
        orch: Any,
        *,
        llm_raises: BaseException,
    ) -> Iterator[tuple[MagicMock, MagicMock]]:
        with (
            patch.object(orch, "_maybe_emit_research_stages"),
            patch.object(orch, "_maybe_emit_stitch_stages"),
            patch.object(orch, "_run_created_metadata", return_value={}),
            patch(
                "research.reresearch.maybe_reresearch_after_plan_fail",
                return_value=False,
            ),
            patch.object(orch, "_selected_model_for_run", return_value="dev:primary"),
            patch(
                "orchestrator._pipeline.lifecycle_plan.execute_plan_stage_llm",
                side_effect=llm_raises,
            ) as mock_llm,
            patch(
                "orchestrator._pipeline.lifecycle_plan.emit_stub_plan_stage",
            ) as mock_stub,
        ):
            yield mock_llm, mock_stub

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=ValueError("bad plan payload"),
    ) as (_mock_llm, mock_stub):
        with pytest.raises(ValueError, match="bad plan payload"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


def test_sak497_b_peel_off_broker_miss_stub_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-b / sak498-i: LLM=0 — broker_miss still soft-falls back to stub."""
    from collections.abc import Iterator
    from contextlib import contextmanager
    from typing import Any
    from unittest.mock import MagicMock
    from uuid import uuid4

    from orchestrator.pipeline import make_dev_orchestrator

    @contextmanager
    def _patched_plan_stage(
        orch: Any,
        *,
        llm_raises: BaseException,
    ) -> Iterator[tuple[MagicMock, MagicMock]]:
        with (
            patch.object(orch, "_maybe_emit_research_stages"),
            patch.object(orch, "_maybe_emit_stitch_stages"),
            patch.object(orch, "_run_created_metadata", return_value={}),
            patch(
                "research.reresearch.maybe_reresearch_after_plan_fail",
                return_value=False,
            ),
            patch.object(orch, "_selected_model_for_run", return_value="dev:primary"),
            patch(
                "orchestrator._pipeline.lifecycle_plan.execute_plan_stage_llm",
                side_effect=llm_raises,
            ) as mock_llm,
            patch(
                "orchestrator._pipeline.lifecycle_plan.emit_stub_plan_stage",
            ) as mock_stub,
        ):
            yield mock_llm, mock_stub

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=RuntimeError("broker_miss: chat_facade: down"),
    ) as (_mock_llm, mock_stub):
        orch.execute_plan_stage(run_id)
    mock_stub.assert_called_once()


def test_sak497_b_peel_strict_passed_to_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-b: execute_plan_stage_llm calls chat_facade with peel_strict=True."""
    from typing import Any
    from uuid import uuid4

    from env import find_repo_root
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm.gate_helpers import execute_plan_stage_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        raise RuntimeError("broker_miss: chat_facade: probe")

    root = find_repo_root()
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        root / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()

    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=_capture,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_plan_stage_llm(
                store,
                reg,
                router,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                timeout_seconds=1.0,
            )
    assert captured.get("peel_strict") is True
    assert captured.get("stage_name") == "plan"


# --- sak497-h: post-verify role critique broker chat + peel miss ---


def test_sak497_h_source_markers() -> None:
    """sak497-h: gate_helpers wires peel_strict for post-verify role critiques."""
    gate_helpers = (_ROOT / "packages" / "orchestrator" / "llm" / "gate_helpers.py").read_text(
        encoding="utf-8"
    )
    role_emit = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "role_critique_emit.py"
    ).read_text(encoding="utf-8")
    bindings = (
        _ROOT / "packages" / "orchestrator" / "llm" / "post_verify_role_bindings.py"
    ).read_text(encoding="utf-8")

    assert "sak497-h" in gate_helpers
    assert "peel_strict=True" in gate_helpers
    assert "bind_post_verify_role_critique" in gate_helpers
    assert "broker_miss: post_verify_role_critique" in gate_helpers
    assert "sak497-h" in role_emit
    assert "broker_miss: role_critique_emit" in role_emit
    assert "sak497-h" in bindings


def test_sak497_h_peel_broker_miss_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-h: LLM=1 — broker miss propagates for planner critique."""
    from uuid import uuid4

    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm.post_verify_role_bindings import execute_planner_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("broker_miss: chat_facade: down"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_planner_critique_llm(
                store,
                reg,
                router,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                verifier_exit_code=0,
                log_snippet="ok",
                timeout_seconds=1.0,
            )
    assert not store.list_run_events(str(run_id))


def test_sak497_h_peel_invalid_llm_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-h: LLM=1 — invalid LLM payload raises (no silent False)."""
    from uuid import uuid4

    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm.post_verify_role_bindings import execute_test_writer_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        return_value={"critics": [], "gate": {"verdict": "PASS"}},
    ):
        with pytest.raises(RuntimeError, match="broker_miss: post_verify_role_critique"):
            execute_test_writer_critique_llm(
                store,
                reg,
                router,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                verifier_exit_code=1,
                log_snippet="error",
                timeout_seconds=1.0,
            )


def test_sak497_h_non_peel_invalid_llm_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-h: LLM off peel — invalid payload returns False (stub path allowed)."""
    from uuid import uuid4

    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm.post_verify_role_bindings import execute_test_writer_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        return_value={"critics": [], "gate": {"verdict": "PASS"}},
    ):
        ok = execute_test_writer_critique_llm(
            store,
            reg,
            router,
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=1,
            log_snippet="error",
            timeout_seconds=1.0,
        )
    assert ok is False
    assert not store.list_run_events(str(run_id))


def test_sak497_h_peel_strict_passed_to_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-h: post-verify critique calls chat_facade with peel_strict=True."""
    from typing import Any
    from uuid import uuid4

    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm.post_verify_role_bindings import execute_planner_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> dict[str, object]:
        captured.update(kwargs)
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
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=_capture,
    ):
        ok = execute_planner_critique_llm(
            store,
            reg,
            router,
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            verifier_exit_code=0,
            log_snippet="pytest ok",
            timeout_seconds=1.0,
        )
    assert ok is True
    assert captured.get("peel_strict") is True
    assert captured.get("stage_name") == "planner.critique"


# --- sak497-c: campaign backlog generator broker chat + peel miss ---


_INVALID_LLM_BACKLOG_PAYLOAD = {"backlog": {"epics": [{"epic_id": "", "title": "bad"}]}}


def test_sak497_c_source_markers() -> None:
    """sak497-c: generator uses chat_facade peel_strict; raises broker_miss under peel."""
    generator = (_ROOT / "packages" / "orchestrator" / "campaign" / "generator.py").read_text(
        encoding="utf-8",
    )
    assert "sak497-c" in generator
    assert "ollama_chat_json_via_plan_patch" in generator
    assert "peel_strict=True" in generator
    assert "broker_miss: backlog_generator" in generator
    assert "backlog_generator import" not in generator


def test_sak497_c_peel_broker_miss_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-c: LLM=1 — broker miss propagates (no heuristic fallback)."""
    from uuid import uuid4

    from orchestrator.campaign.generator import _generate_backlog_for_run

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", "llama3.2")
    with (
        patch(
            "orchestrator.campaign.generator.ollama_chat_json_via_plan_patch",
            side_effect=RuntimeError("broker_miss: chat_facade: down"),
        ),
        patch(
            "orchestrator.campaign.generator.generate_heuristic_backlog",
        ) as mock_heuristic,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            _generate_backlog_for_run(
                uuid4(),
                [],
                generator_mode="llm",
                max_slices=10,
                repo_root=_ROOT,
            )
    mock_heuristic.assert_not_called()


def test_sak497_c_peel_invalid_llm_no_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-c: LLM=1 — invalid LLM payload raises broker_miss (no heuristic)."""
    from uuid import uuid4

    from orchestrator.campaign.generator import _generate_backlog_for_run

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", "llama3.2")
    with (
        patch(
            "orchestrator.campaign.generator.ollama_chat_json_via_plan_patch",
            return_value=_INVALID_LLM_BACKLOG_PAYLOAD,
        ),
        patch(
            "orchestrator.campaign.generator.generate_heuristic_backlog",
        ) as mock_heuristic,
    ):
        with pytest.raises(RuntimeError, match="broker_miss: backlog_generator"):
            _generate_backlog_for_run(
                uuid4(),
                [],
                generator_mode="llm",
                max_slices=10,
            )
    mock_heuristic.assert_not_called()


def test_sak497_c_non_peel_invalid_llm_falls_back_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-c: LLM off peel — invalid LLM payload may fall back to heuristic."""
    from uuid import uuid4

    from orchestrator.campaign.generator import _generate_backlog_for_run

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", "llama3.2")
    sentinel = object()
    with (
        patch(
            "orchestrator.campaign.generator.ollama_chat_json_via_plan_patch",
            return_value=_INVALID_LLM_BACKLOG_PAYLOAD,
        ),
        patch(
            "orchestrator.campaign.generator.generate_heuristic_backlog",
            return_value=sentinel,
        ) as mock_heuristic,
    ):
        out = _generate_backlog_for_run(
            uuid4(),
            [],
            generator_mode="llm",
            max_slices=10,
        )
    assert out is sentinel
    mock_heuristic.assert_called_once()


def test_sak497_c_peel_strict_passed_to_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-c: backlog LLM path calls chat_facade with peel_strict=True."""
    from typing import Any
    from uuid import uuid4

    from orchestrator.campaign.generator import _generate_backlog_for_run

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", "llama3.2")
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        raise RuntimeError("broker_miss: chat_facade: probe")

    with patch(
        "orchestrator.campaign.generator.ollama_chat_json_via_plan_patch",
        side_effect=_capture,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            _generate_backlog_for_run(
                uuid4(),
                [],
                generator_mode="llm",
                max_slices=10,
            )
    assert captured.get("peel_strict") is True
    assert captured.get("agent_role") == "planner"


# --- sak497-d: campaign OpenAPI 503 (404 only where peel applies) ---


import json

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import campaign_json_openapi_responses

SAK497_D_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/campaigns", "post"),
    ("/v1/campaigns/{campaign_id}/backlog", "get"),
    ("/v1/campaigns/{campaign_id}/pause", "post"),
    ("/v1/campaigns/{campaign_id}/resume", "post"),
    ("/v1/campaigns/{campaign_id}/cancel", "post"),
    ("/v1/campaigns/{campaign_id}/progress", "get"),
)


def _sak497_d_openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


@pytest.mark.sak497_d
def test_sak497_d_openapi_artifact_documents_peel_503() -> None:
    """sak497-d: openapi.json lists 503 problem+json on /v1/campaigns* peel paths."""
    spec = json.loads(_sak497_d_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK497_D_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


@pytest.mark.sak497_d
def test_sak497_d_peel_routes_source_wire_openapi_helpers() -> None:
    """sak497-d: campaign routes wire campaign_json_openapi_responses (404 where applicable)."""
    root = _ROOT / "packages" / "api"
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    create = (root / "routes" / "campaigns" / "create.py").read_text(encoding="utf-8")
    backlog = (root / "routes" / "campaigns" / "backlog.py").read_text(encoding="utf-8")
    lifecycle = (root / "routes" / "campaigns" / "lifecycle.py").read_text(encoding="utf-8")
    progress = (root / "routes" / "campaigns" / "progress.py").read_text(encoding="utf-8")

    assert "sak497-d" in peel
    assert campaign_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert campaign_json_openapi_responses(not_found={"x": 1})[404] == {"x": 1}

    assert "campaign_json_openapi_responses()" in create
    assert "sak497-d" in create
    assert "campaign_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)" in backlog
    assert "sak497-d" in backlog
    assert lifecycle.count("campaign_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)") >= 3
    assert "sak497-d" in lifecycle
    assert "campaign_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)" in progress
    assert "sak497-d" in progress


# --- sak497-e: chat sessions/turns/scope/collab LLM OpenAPI 503 ---

from api.schemas.peel_responses import llm_json_openapi_responses

SAK497_E_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}", "get"),
    ("/v1/chat/sessions/{session_id}/graph", "get"),
    ("/v1/chat/sessions/{session_id}/fork", "post"),
    ("/v1/chat/sessions/{session_id}/active-leaf", "put"),
    ("/v1/chat/sessions/{session_id}/turns", "post"),
    ("/v1/chat/sessions/{session_id}/messages", "post"),
    ("/v1/chat/sessions/{session_id}/turns/{turn_id}/switch-mode", "post"),
    ("/v1/chat/scope/discover", "post"),
    ("/v1/chat/scope/gather", "post"),
    ("/v1/chat/scope/recommend", "post"),
    ("/v1/chat/scope/confirm", "post"),
    ("/v1/chat/sessions/{session_id}/model-bindings/swap", "post"),
)


def _sak497_e_openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


@pytest.mark.sak497_e
def test_sak497_e_openapi_artifact_documents_peel_503() -> None:
    """sak497-e: openapi.json lists 503 problem+json on chat LLM peel paths."""
    spec = json.loads(_sak497_e_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK497_E_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


@pytest.mark.sak497_e
def test_sak497_e_peel_routes_source_wire_openapi_helpers() -> None:
    """sak497-e: chat session/turn/scope/collab routes wire llm_json_openapi_responses."""
    root = _ROOT / "packages" / "api"
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    chat = (root / "routes" / "chat.py").read_text(encoding="utf-8")
    chat_session = (root / "routes" / "chat_session.py").read_text(encoding="utf-8")
    chat_collab = (root / "routes" / "chat_collab.py").read_text(encoding="utf-8")

    assert "sak497-e" in peel
    assert llm_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert llm_json_openapi_responses(not_found={"x": 1})[404] == {"x": 1}

    assert chat.count("llm_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)") >= 7
    assert "sak497-e" in chat
    for needle in ("/turns", "/messages", "/fork", "/active-leaf", "/switch-mode"):
        assert needle in chat
        assert "llm_json_openapi_responses" in chat

    for needle in ("/scope/discover", "/scope/gather", "/scope/recommend", "/scope/confirm"):
        assert needle in chat_session
    assert chat_session.count("responses=llm_json_openapi_responses()") >= 4
    assert "sak497-e" in chat_session

    assert "/model-bindings/swap" in chat_collab
    assert "llm_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)" in chat_collab
    assert "sak497-e" in chat_collab


# --- sak497-i: SANDBOX/RESEARCH/EGRESS/TOOLS HTTP flag-matrix ---


def test_sak497_i_domain_broker_flags_api_modules() -> None:
    """sak497-i: domain flag-matrix modules cover =1 miss and =2 503 paths."""
    root = Path(__file__).resolve().parents[2] / "tests" / "api_http"
    sandbox = (root / "test_sandbox_broker_flags_api.py").read_text(encoding="utf-8")
    research = (root / "test_research_broker_flags_api.py").read_text(encoding="utf-8")
    egress = (root / "test_egress_broker_flags_api.py").read_text(encoding="utf-8")
    tools = (root / "test_tools_broker_flags_api.py").read_text(encoding="utf-8")
    for src in (sandbox, research, egress, tools):
        assert "sak497-i" in src
        assert "_under_" in src and "_1_" in src
        assert "_2_returns_503" in src
    yml = (
        Path(__file__).resolve().parents[3] / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "test_sandbox_broker_flags_api.py" in yml
    assert "test_research_broker_flags_api.py" in yml
    assert "test_egress_broker_flags_api.py" in yml
    assert "test_tools_broker_flags_api.py" in yml


# --- sak497-g: Maker bootstrap-load peel 503 + toast ---


def test_sak497_g_maker_bootstrap_peel_http() -> None:
    """sak497-g: bootstrap-load + api-client map 503 peel; toast on peel miss."""
    bootstrap = (
        _ROOT / "packages" / "maker_web" / "static" / "js" / "bootstrap-load.js"
    ).read_text(encoding="utf-8")
    api_client = (_ROOT / "packages" / "maker_web" / "static" / "js" / "api-client.js").read_text(
        encoding="utf-8"
    )
    peel_http = (_ROOT / "packages" / "ui_shared" / "js" / "peel-http.js").read_text(
        encoding="utf-8",
    )
    assert "sak497-g" in bootstrap
    assert "mapHttp503PeelMiss" in bootstrap
    assert "toastIfMiss" in bootstrap
    assert "app_bootstrap" in bootstrap
    assert "sak497-g" in api_client
    assert "isBootstrapPeelMiss" in api_client
    assert "mapHttp503PeelMiss" in api_client
    assert "feature" in peel_http.split("mapHttp503PeelMiss")[1][:120]


# --- sak497-f: admin isDomainPeelMiss / writeMissMessage domain ---


def test_sak497_f_admin_domain_peel_assert_markers() -> None:
    """sak497-f: peel_assert.ts domain miss detectors + write/read formatters."""
    peel = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8"
    )
    assert "sak497-f" in peel
    assert "isDomainPeelMiss" in peel
    assert "writeMissMessage" in peel
    assert "parseSsePeelMiss" in peel
    assert "formatReadCatchMessage" in peel


def test_sak497_f_admin_domain_peel_assert_detectors() -> None:
    """sak497-f: isDomainPeelMiss classifies structured domain broker bodies."""
    from broker_client.peel_assert import (
        format_domain_miss_message,
        is_domain_peel_miss,
        is_llm_miss,
        is_sandbox_miss,
    )

    assert is_sandbox_miss({"code": "broker_sandbox_only", "error": "sandbox down"})
    assert is_llm_miss({"code": "broker_llm_unavailable", "error": "llm down"})
    assert is_domain_peel_miss({"code": "broker_research_only", "error": "research down"})
    assert format_domain_miss_message({"error": "llm down"}) == "llm down"


# --- sak497-j: llm __init__ consolidation / Maker SSE domain / formatDomainMissMessage ---


def test_sak497_j_llm_init_consolidation_markers() -> None:
    """sak497-j: implementation critique re-exported; removed paths documented."""
    init = (_ROOT / "packages" / "orchestrator" / "llm" / "__init__.py").read_text(
        encoding="utf-8",
    )
    bindings = (
        _ROOT / "packages" / "orchestrator" / "llm" / "post_verify_role_bindings.py"
    ).read_text(encoding="utf-8")
    assert "sak497-j" in init
    assert "execute_implementation_critique_llm" in init
    assert "execute_implementation_critique_llm = _removed" not in init
    assert "execute_self_refinement_critique_llm = _removed" not in init
    assert "execute_agent_evaluator_policy_llm = _removed" not in init
    assert "sak498-d" in init
    assert "execute_implementation_critique_llm" in bindings


def test_sak497_j_maker_sse_domain_peel_miss() -> None:
    """sak497-j: Maker sse-client parseSsePeelMiss parity with admin domain misses."""
    sse = (_ROOT / "packages" / "maker_web" / "static" / "js" / "sse-client.js").read_text(
        encoding="utf-8",
    )
    broker_miss = (_ROOT / "packages" / "maker_web" / "static" / "js" / "broker_miss.js").read_text(
        encoding="utf-8"
    )
    assert "sak497-j" in sse
    assert "isDomainPeelMiss" in sse
    assert "isDomainPeelMiss" in broker_miss
    assert "formatDomainMissMessage" in broker_miss


def test_sak497_j_format_domain_miss_message_ts() -> None:
    """sak497-j: admin formatDomainMissMessage exported."""
    peel = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8"
    )
    assert "sak497-j" in peel
    assert "formatDomainMissMessage" in peel

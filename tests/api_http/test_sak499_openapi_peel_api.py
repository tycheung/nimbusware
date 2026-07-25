from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.routes import project_context_artifacts as pca
from api.routes.runs import maker_approval as ma
from orchestrator.context_artifacts import ContextArtifactRecord


def _launch_eval_broker_miss() -> RuntimeError:
    return RuntimeError(
        "broker_miss: launch_evaluator: LLM panel unavailable under "
        "NIMBUSWARE_BROKER_LLM=1|2"
    )


def _bridge_memory_refuse() -> RuntimeError:
    return RuntimeError(
        "context-artifact FAISS rebuild unavailable under NIMBUSWARE_BROKER_MEMORY=1|2; "
        "use SwissArmyNoife memory_index"
    )


def test_bridge_memory_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak499-c: bridge-memory returns broker_miss body under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    project_id = uuid4()
    artifact = ContextArtifactRecord(
        artifact_id="art-1",
        project_id=str(project_id),
        title="Note",
        content="body",
        kind="note",
        created_at="2026-01-01T00:00:00Z",
    )
    store = MagicMock()
    store.get.return_value = MagicMock(tenant_id=None)
    with (
        patch("api.routes.project_context_artifacts.assert_project_accessible"),
        patch("api.routes.project_context_artifacts.get_context_artifact", return_value=artifact),
        patch(
            "api.routes.project_context_artifacts.bridge_artifact_to_memory_index",
            side_effect=_bridge_memory_refuse(),
        ),
    ):
        out = pca.bridge_context_artifact_to_memory(
            project_id=project_id,
            artifact_id="art-1",
            store=store,
            _user=MagicMock(),
        )
    assert out.via == "broker_miss"
    assert out.feature == "context_artifact_bridge"
    assert out.status == "degraded"
    assert out.indexed is False


def test_bridge_memory_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak499-c: bridge-memory maps peel refuse to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    project_id = uuid4()
    artifact = ContextArtifactRecord(
        artifact_id="art-1",
        project_id=str(project_id),
        title="Note",
        content="body",
        kind="note",
        created_at="2026-01-01T00:00:00Z",
    )
    store = MagicMock()
    store.get.return_value = MagicMock(tenant_id=None)
    with (
        patch("api.routes.project_context_artifacts.assert_project_accessible"),
        patch("api.routes.project_context_artifacts.get_context_artifact", return_value=artifact),
        patch(
            "api.routes.project_context_artifacts.bridge_artifact_to_memory_index",
            side_effect=_bridge_memory_refuse(),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        pca.bridge_context_artifact_to_memory(
            project_id=project_id,
            artifact_id="art-1",
            store=store,
            _user=MagicMock(),
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_launch_eval_under_llm_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak499-c: launch-eval returns broker_miss body under LLM=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    run_id = uuid4()
    store = MagicMock()
    store.list_run_events.return_value = [{"event_type": "run.created", "payload": {}}]
    with (
        patch("maker.workspace.workspace.resolve_run_workspace", return_value=MagicMock(is_dir=lambda: True)),
        patch(
            "orchestrator.launch.launch_eval_catalog.attach_context_from_run",
            return_value={},
        ),
        patch(
            "orchestrator.launch.launch_evaluator.evaluate_workspace_rubric",
            side_effect=_launch_eval_broker_miss(),
        ),
    ):
        out = ma.post_maker_launch_eval(run_id=run_id, store=store)
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "launch_eval"
    assert out.get("status") == "degraded"


def test_launch_eval_under_llm_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak499-c: launch-eval maps broker failure to 503 under LLM=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    run_id = uuid4()
    store = MagicMock()
    store.list_run_events.return_value = [{"event_type": "run.created", "payload": {}}]
    with (
        patch("maker.workspace.workspace.resolve_run_workspace", return_value=MagicMock(is_dir=lambda: True)),
        patch(
            "orchestrator.launch.launch_eval_catalog.attach_context_from_run",
            return_value={},
        ),
        patch(
            "orchestrator.launch.launch_evaluator.evaluate_workspace_rubric",
            side_effect=_launch_eval_broker_miss(),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        ma.post_maker_launch_eval(run_id=run_id, store=store)
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_llm_unavailable"

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest

from agent_core.models import EventType
from extensions import SelfRefinementPolicy
from orchestrator.pipeline import make_dev_orchestrator


def _sr_policy_markers(mem: object, rid: UUID) -> list[dict]:
    return [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    ]


def test_env_kill_switch_suppresses_marker_when_policy_would_emit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER", "0")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch(
        "orchestrator.workflow.self_refinement_policy.load_self_refinement_policy",
        return_value=SelfRefinementPolicy(version=2, enabled=True, description="x"),
    ):
        orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    assert _sr_policy_markers(mem, rid) == []


def test_env_unset_still_emits_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch(
        "orchestrator.workflow.self_refinement_policy.load_self_refinement_policy",
        return_value=SelfRefinementPolicy(version=3, enabled=True, description="y"),
    ):
        orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    assert len(_sr_policy_markers(mem, rid)) == 1

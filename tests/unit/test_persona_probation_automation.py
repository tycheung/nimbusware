from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from agent_core.models import EventType, StageStartedEvent, StageStartedPayload
from nimbusware_extensions.personas import PersonaShelf
from nimbusware_extensions.extension_runtime import AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD
from nimbusware_orchestrator.persona_probation_automation import (
    emit_probation_promotion_notice,
    run_probation_automation,
)
from nimbusware_orchestrator.persona_probation_reliability import (
    ProbationReliabilityMetrics,
    collect_persona_eval_metrics,
    reliability_decision,
)
from nimbusware_orchestrator.persona_shelf_promotion import (
    auto_shelve_probation_correlation_id,
    try_auto_shelve_probation_persona,
)
from nimbusware_orchestrator.workflow_probation_automation import (
    ProbationAutomationWorkflowBlock,
    parse_probation_automation_workflow_block,
)
from nimbusware_store.memory import InMemoryEventStore


def _minimal_shelves(tmp: Path, *, commerce_on_probation: bool) -> None:
    cfg = tmp / "configs" / "personas"
    cfg.mkdir(parents=True, exist_ok=True)
    commerce: dict = {
        "id": "commerce",
        "display_name": "Commerce",
        "version": 3,
    }
    if commerce_on_probation:
        commerce["probation_status"] = "probation"
    payload = {
        "version": 1,
        "business_area": [commerce],
        "development_role": [{"id": "backend", "display_name": "Backend", "version": 1}],
    }
    (cfg / "shelves.yaml").write_text(
        yaml.dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _append_eval_stage(
    store: InMemoryEventStore,
    run_id: UUID,
    persona_id: str,
    score: float,
) -> None:
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "evaluation": {
                        "persona_id": persona_id,
                        "status": "ok",
                        "score": score,
                        "promotion_ready": score >= AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD,
                    },
                },
            },
            payload=StageStartedPayload(stage_name=f"agent_eval:{persona_id}", attempt=1),
        ),
    )


def test_parse_probation_automation_block(tmp_path: Path) -> None:
    wf = tmp_path / "configs" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / "prob.yaml").write_text(
        "version: 1\nprobation_automation:\n  enabled: true\n",
        encoding="utf-8",
    )
    block = parse_probation_automation_workflow_block(tmp_path, "prob")
    assert block.enabled is True


def test_try_auto_shelve_applies(tmp_path: Path) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=True)
    mem = InMemoryEventStore()
    meta = try_auto_shelve_probation_persona(
        tmp_path,
        mem,
        persona_id="commerce",
        run_id=uuid4(),
    )
    assert meta["auto_shelve_probation_applied"] is True
    shelf = PersonaShelf(tmp_path / "configs" / "personas" / "shelves.yaml")
    row = shelf.find_entry("business_area", "commerce")
    assert row is not None
    assert row.get("probation_status") == "shelved"


def test_reliability_decision_shelve_on_invalid() -> None:
    metrics = ProbationReliabilityMetrics(
        persona_id="commerce",
        runs_evaluated=3,
        avg_score=0.9,
        below_threshold_count=0,
        invalid_status_count=1,
    )
    assert (
        reliability_decision(
            metrics,
            min_runs=2,
            min_score=0.75,
            max_below_ratio=0.5,
        )
        == "shelve"
    )


def test_run_probation_automation_shelve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _minimal_shelves(tmp_path, commerce_on_probation=True)
    mem = InMemoryEventStore()
    for _ in range(3):
        _append_eval_stage(mem, uuid4(), "commerce", 0.2)
    monkeypatch.delenv("NIMBUSWARE_PROBATION_AUTO_SHELVE", raising=False)
    block = ProbationAutomationWorkflowBlock(
        enabled=True,
        auto_shelve=True,
        min_eval_runs=2,
    )
    out = run_probation_automation(
        tmp_path,
        mem,
        persona_id="commerce",
        run_id=uuid4(),
        evaluation={
            "persona_id": "commerce",
            "status": "ok",
            "score": 0.2,
            "promotion_ready": False,
        },
        block=block,
        owner_role=str(uuid4()),
    )
    assert out["auto_shelve_probation"]["auto_shelve_probation_applied"] is True


def test_promotion_notice_emitted_once() -> None:
    mem = InMemoryEventStore()
    run_id = uuid4()
    owner = str(uuid4())
    evaluation = {
        "persona_id": "commerce",
        "promotion_ready": True,
        "score": 0.9,
        "status": "ok",
    }
    m1 = emit_probation_promotion_notice(
        mem,
        run_id,
        "commerce",
        evaluation,
        owner,
    )
    m2 = emit_probation_promotion_notice(
        mem,
        run_id,
        "commerce",
        evaluation,
        owner,
    )
    assert m1["probation_promotion_notice_emitted"] is True
    assert m2["probation_promotion_notice_emitted"] is False


def test_auto_shelve_correlation_stable() -> None:
    rid = uuid4()
    a = auto_shelve_probation_correlation_id(rid, "commerce")
    b = auto_shelve_probation_correlation_id(rid, "commerce")
    assert a == b
    assert a != auto_shelve_probation_correlation_id(rid, "other")


def test_collect_metrics_from_store() -> None:
    mem = InMemoryEventStore()
    _append_eval_stage(mem, uuid4(), "commerce", 0.5)
    _append_eval_stage(mem, uuid4(), "commerce", 0.4)
    metrics = collect_persona_eval_metrics(mem, "commerce", run_limit=10)
    assert metrics.runs_evaluated >= 2

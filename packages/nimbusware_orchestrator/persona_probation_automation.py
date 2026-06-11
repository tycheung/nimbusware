from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, FindingCreatedEvent, FindingCreatedPayload, Severity
from nimbusware_env.env_flags import env_falsy
from nimbusware_orchestrator.persona_probation_reliability import (
    collect_persona_eval_metrics,
    reliability_decision,
)
from nimbusware_orchestrator.persona_shelf_promotion import try_auto_shelve_probation_persona
from nimbusware_orchestrator.workflow_probation_automation import ProbationAutomationWorkflowBlock
from nimbusware_store.protocol import EventStore


def _probation_auto_shelve_env_disabled() -> bool:
    return env_falsy("NIMBUSWARE_PROBATION_AUTO_SHELVE")


def _probation_notify_env_disabled() -> bool:
    return env_falsy("NIMBUSWARE_PROBATION_NOTIFY_BEFORE_PROMOTE")


def _probation_promotion_notice_already_emitted(
    store: EventStore,
    run_id: UUID,
    persona_id: str,
) -> bool:
    for row in store.list_run_events(str(run_id)):
        if row.get("event_type") != EventType.FINDING_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if meta.get("reason_code") != "persona_probation_promotion_notice":
            continue
        if str(meta.get("persona_id") or "") == persona_id:
            return True
    return False


def emit_probation_promotion_notice(
    store: EventStore,
    run_id: UUID,
    persona_id: str,
    evaluation: dict[str, Any],
    owner_role: str,
    *,
    strictness_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if _probation_promotion_notice_already_emitted(store, run_id, persona_id):
        return {
            "probation_promotion_notice_emitted": False,
            "reason": "already_recorded",
        }

    score = evaluation.get("score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        score_txt = str(score)
    else:
        score_txt = "n/a"

    repro = [
        f"Persona {persona_id} is on probation and evaluator reports promotion_ready.",
        f"policy_score={score_txt}; review catalog before auto-promote.",
    ]
    ctx = strictness_context if isinstance(strictness_context, dict) else {}
    payload = FindingCreatedPayload.model_validate(
        {
            "finding_id": str(uuid4()),
            "category": "persona_probation",
            "owner_role": owner_role,
            "severity": Severity.LOW.value,
            "source_artifact": "probation_automation",
            "repro_steps": repro,
            "required_fixes": [],
        },
        context=ctx,
    )
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "reason_code": "persona_probation_promotion_notice",
                "persona_id": persona_id,
                "promotion_ready": bool(evaluation.get("promotion_ready")),
            },
            payload=payload,
        ),
    )
    return {"probation_promotion_notice_emitted": True}


def run_probation_automation(
    repo_root: Path,
    store: EventStore,
    persona_id: str,
    run_id: UUID,
    evaluation: dict[str, Any],
    block: ProbationAutomationWorkflowBlock,
    *,
    config_materializer: Any | None = None,
    actor: str = "system:agent_evaluator",
    owner_role: str | None = None,
    strictness_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return metadata for agent_evaluator / self_refinement stage envelopes."""
    out: dict[str, Any] = {}
    if not block.enabled or not persona_id.strip() or persona_id.strip() == "default":
        return out

    metrics = collect_persona_eval_metrics(
        store,
        persona_id.strip(),
        run_limit=block.history_run_limit,
    )
    decision = reliability_decision(
        metrics,
        min_runs=block.min_eval_runs,
        min_score=block.min_score,
        max_below_ratio=block.max_below_ratio,
        current_promotion_ready=bool(evaluation.get("promotion_ready")),
    )
    out["probation_reliability"] = {**metrics.to_dict(), "decision": decision}

    if block.auto_shelve and decision == "shelve":
        if _probation_auto_shelve_env_disabled():
            out["auto_shelve_probation"] = {
                "auto_shelve_probation_requested": True,
                "auto_shelve_probation_applied": False,
                "reason": "env_kill_switch",
            }
        else:
            out["auto_shelve_probation"] = try_auto_shelve_probation_persona(
                repo_root,
                store,
                persona_id=persona_id.strip(),
                run_id=run_id,
                config_materializer=config_materializer,
                actor=actor,
            )
            if out["auto_shelve_probation"].get("auto_shelve_probation_applied"):
                return out

    promotion_ready = bool(evaluation.get("promotion_ready"))
    if block.notify_before_promote and promotion_ready and decision in ("notify_promote", "ok"):
        if _probation_notify_env_disabled():
            out["probation_promotion_notice"] = {
                "probation_promotion_notice_requested": True,
                "probation_promotion_notice_emitted": False,
                "reason": "env_kill_switch",
            }
        elif owner_role:
            out["probation_promotion_notice"] = emit_probation_promotion_notice(
                store,
                run_id,
                persona_id.strip(),
                evaluation,
                owner_role,
                strictness_context=strictness_context,
            )

    return out

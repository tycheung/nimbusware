from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    RequiredFixArtifact,
    Severity,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import append_gate_decision_event
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_orchestrator.workflow_refactor import RefactorWorkflowBlock
from nimbusware_store.protocol import EventStore

REFACTOR_STAGE = "refactor"
REFACTOR_CRITIQUE_STAGE = "refactor.critique"
REFACTOR_POST_STITCH_STAGE = "refactor.post_stitch"
REFACTOR_POST_STITCH_CRITIQUE_STAGE = "refactor.post_stitch.critique"
_REFACTOR_CRITIC = "refactor_critic"
_CODE_QUALITY_CRITIC = "code_quality_critic"

_REFACTOR_FAIL_FIX = RequiredFixArtifact.model_validate(
    {
        "artifact_schema_version": 1,
        "format": "json_patch",
        "target_files": ["packages/"],
        "patch_artifact": "[]",
        "validation_steps": ["address refactor critique findings"],
        "acceptance_criteria": "refactor.critique gate passes",
    },
)


def refactor_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    last_gate: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != "gate.decision.emitted":
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") == REFACTOR_CRITIQUE_STAGE:
            last_gate = payload
    if last_gate is None:
        return None
    return {
        "stage_name": REFACTOR_CRITIQUE_STAGE,
        "verdict": last_gate.get("verdict"),
        "failing_critics": last_gate.get("failing_critics") or [],
    }


def emit_refactor_stage_and_critique(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    block: RefactorWorkflowBlock,
    unanimous_gate_enforce: bool = False,
    force_fail: bool = False,
    workspace: Path | None = None,
) -> bool:
    tax_keys = critique_router.pairing_for("refactorer")
    if len(tax_keys) < 2:
        return False
    owner = registry.resolve("refactorer")
    now = datetime.now(timezone.utc)
    refactor_mode = "stub_proposal"
    llm_summary: str | None = None
    if not block.stub_only and workspace is not None and workspace.is_dir():
        refactor_mode = "workspace_scan"
        if block.llm_enabled:
            refactor_mode = "llm_proposal"
            try:
                from nimbusware_env.env_flags import env_str, nimbusware_use_llm_enabled
                from nimbusware_orchestrator.ollama_chat import ollama_chat_json

                if nimbusware_use_llm_enabled():
                    model = env_str("NIMBUSWARE_DEFAULT_MODEL") or "llama3.2"
                    base = env_str("NIMBUSWARE_OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
                    payload = ollama_chat_json(
                        base_url=base,
                        model=model,
                        timeout_seconds=60.0,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    "Summarize one low-risk refactor for this workspace "
                                    "(JSON: summary, target_paths)."
                                ),
                            },
                        ],
                    )
                    if payload.get("summary"):
                        llm_summary = str(payload.get("summary"))[:500]
                    else:
                        refactor_mode = "workspace_scan"
            except Exception:
                refactor_mode = "workspace_scan"
    refactor_meta: dict[str, Any] = {
        "stub_only": block.stub_only,
        "llm_enabled": block.llm_enabled,
        "max_iterations": block.max_iterations,
        "mode": refactor_mode,
    }
    if llm_summary:
        refactor_meta["llm_summary"] = llm_summary
    if workspace is not None and workspace.is_dir():
        from nimbusware_orchestrator.loc_accord_stage import emit_refactor_loc_accord_stage
        from nimbusware_orchestrator.simplification_metrics import ComplexityIndex

        cx = ComplexityIndex.from_workspace(workspace)
        loc_delta = max(0, cx.loc - block.max_iterations * 40)
        loc_accord_ok = emit_refactor_loc_accord_stage(store, run_id, loc_delta=loc_delta)
        refactor_meta.update(
            {
                "loc_total": cx.loc,
                "file_count": cx.file_count,
                "loc_delta_estimate": loc_delta,
                "loc_accord": loc_accord_ok,
            },
        )

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata={"refactor": refactor_meta},
            payload=StageStartedPayload(stage_name=REFACTOR_STAGE, attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"refactor": {"mode": refactor_mode}},
            payload=StagePassedPayload(stage_name=REFACTOR_STAGE, duration_ms=0),
        ),
    )

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=REFACTOR_CRITIQUE_STAGE, attempt=1),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        fail = force_fail and tax_key in (_REFACTOR_CRITIC, _CODE_QUALITY_CRITIC)
        verdict = Verdict.FAIL if fail else Verdict.PASS
        fixes = [_REFACTOR_FAIL_FIX] if verdict == Verdict.FAIL else []
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.LOW if verdict == Verdict.PASS else Severity.MEDIUM,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=[f"refactor://{tax_key}"],
            required_fixes=fixes,
        )
        critic_payloads.append(payload)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=payload,
            ),
        )

    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=REFACTOR_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or force_fail,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return str(gate.verdict).upper() == "FAIL"


def refactor_post_stitch_gate_failed(events: list[dict[str, Any]]) -> bool:
    for row in events:
        if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") != REFACTOR_POST_STITCH_CRITIQUE_STAGE:
            continue
        if str(payload.get("verdict") or "").upper() == "FAIL":
            return True
    return False


def emit_refactor_post_stitch_stage_and_critique(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    unanimous_gate_enforce: bool = False,
    force_fail: bool = False,
) -> bool:
    """Mandatory normalization after stitch.applied. Returns True if gate FAIL."""
    tax_keys = critique_router.pairing_for("refactorer")
    if len(tax_keys) < 2:
        return False
    owner = registry.resolve("refactorer")
    now = datetime.now(timezone.utc)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata={"refactor": {"post_stitch": True, "mode": "stub_proposal"}},
            payload=StageStartedPayload(stage_name=REFACTOR_POST_STITCH_STAGE, attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"refactor": {"post_stitch": True}},
            payload=StagePassedPayload(
                stage_name=REFACTOR_POST_STITCH_STAGE,
                duration_ms=0,
            ),
        ),
    )
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(
                stage_name=REFACTOR_POST_STITCH_CRITIQUE_STAGE,
                attempt=1,
            ),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        fail = force_fail and tax_key in (_REFACTOR_CRITIC, _CODE_QUALITY_CRITIC)
        verdict = Verdict.FAIL if fail else Verdict.PASS
        fixes = [_REFACTOR_FAIL_FIX] if verdict == Verdict.FAIL else []
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.LOW if verdict == Verdict.PASS else Severity.MEDIUM,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=[f"refactor://post_stitch/{tax_key}"],
            required_fixes=fixes,
        )
        critic_payloads.append(payload)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=payload,
            ),
        )

    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=REFACTOR_POST_STITCH_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or force_fail,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return str(gate.verdict).upper() == "FAIL"

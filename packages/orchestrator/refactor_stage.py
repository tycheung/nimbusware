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
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.llm.common import append_gate_decision_event
from orchestrator.refactor_proposal import (
    build_refactor_proposal,
    estimate_loc_delta_from_patch,
    orphan_gate_exceeded,
)
from orchestrator.registry import RoleRegistry
from orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from orchestrator.workflow_refactor import RefactorWorkflowBlock
from store.protocol import EventStore

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
    orphan_gate_fail = False
    proposal_meta: dict[str, Any] = {}
    if not block.stub_only and workspace is not None and workspace.is_dir():
        proposal = build_refactor_proposal(workspace, workspace, block)
        proposal_meta = dict(proposal)
        orphan_gate_fail = orphan_gate_exceeded(
            proposal,
            orphan_gate_max=block.orphan_gate_max,
        )
        refactor_mode = "code_intel_proposal"
        if block.llm_enabled:
            refactor_mode = "llm_proposal"
            try:
                from env.env_flags import (
                    env_str,
                    nimbusware_ollama_base_url,
                    nimbusware_use_llm_enabled,
                )
                from orchestrator.llm.common import ollama_chat_json_via_plan_patch
                from orchestrator.refactor_proposal import build_refactor_patch_artifact

                if nimbusware_use_llm_enabled():
                    model = env_str("NIMBUSWARE_DEFAULT_MODEL") or "llama3.2"
                    base = nimbusware_ollama_base_url()
                    intel_hint = (
                        f"proposal_kind={proposal.get('proposal_kind')}; "
                        f"orphans={proposal.get('orphan_count')}; "
                        f"unreachable={proposal.get('unreachable_module_count')}"
                    )
                    payload = ollama_chat_json_via_plan_patch(
                        base_url=base,
                        model=model,
                        timeout_seconds=60.0,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    "Propose one low-risk refactor as JSON with keys: "
                                    "summary (str), target_paths (list[str]), "
                                    "patch_artifact (list of RFC6902 ops with op, path, value). "
                                    f"Context: {intel_hint}"
                                ),
                            },
                        ],
                        agent_role="refactorer",
                    )
                    if payload.get("summary"):
                        llm_summary = str(payload.get("summary"))[:500]
                    patch_raw = payload.get("patch_artifact")
                    if isinstance(patch_raw, list) and patch_raw:
                        import json

                        proposal_meta["patch_artifact"] = json.dumps(patch_raw)
                        proposal_meta["summary"] = str(
                            payload.get("summary") or proposal_meta.get("summary", ""),
                        )[:500]
                        targets = payload.get("target_paths")
                        if isinstance(targets, list) and targets:
                            proposal_meta["target_paths"] = [
                                str(x) for x in targets if isinstance(x, str) and str(x).strip()
                            ]
                        refactor_mode = "llm_patch"
                    elif payload.get("summary"):
                        refactor_mode = "llm_proposal"
                    else:
                        refactor_mode = "code_intel_proposal"
                    if refactor_mode != "llm_patch" and not proposal_meta.get("patch_artifact"):
                        proposal_meta["patch_artifact"] = build_refactor_patch_artifact(
                            proposal_meta,
                            workspace,
                        )
            except Exception:
                refactor_mode = "code_intel_proposal"
    refactor_meta: dict[str, Any] = {
        "stub_only": block.stub_only,
        "llm_enabled": block.llm_enabled,
        "max_iterations": block.max_iterations,
        "mode": refactor_mode,
        "orphan_gate_fail": orphan_gate_fail,
    }
    if proposal_meta:
        refactor_meta.update(proposal_meta)
    if llm_summary:
        refactor_meta["llm_summary"] = llm_summary
    if workspace is not None and workspace.is_dir():
        from orchestrator.loc_accord_stage import emit_refactor_loc_accord_stage
        from orchestrator.simplification_metrics import ComplexityIndex

        cx = ComplexityIndex.from_workspace(workspace)
        patch_raw = str(proposal_meta.get("patch_artifact") or "[]")
        patch_loc = estimate_loc_delta_from_patch(patch_raw)
        loc_delta = (
            patch_loc if patch_loc is not None else max(0, cx.loc - block.max_iterations * 40)
        )
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
    patch_artifact = str(proposal_meta.get("patch_artifact") or "[]")
    proposal_kind = proposal_meta.get("proposal_kind")
    empty_patch_fail = (
        not block.stub_only and proposal_kind not in (None, "noop") and patch_artifact in ("[]", "")
    )
    fail_targets = proposal_meta.get("target_paths")
    target_files = (
        [str(x) for x in fail_targets if isinstance(x, str) and str(x).strip()]
        if isinstance(fail_targets, list)
        else ["packages/"]
    )
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        fail = force_fail and tax_key in (_REFACTOR_CRITIC, _CODE_QUALITY_CRITIC)
        if orphan_gate_fail and tax_key == _REFACTOR_CRITIC:
            fail = True
        if empty_patch_fail and tax_key == _REFACTOR_CRITIC:
            fail = True
        verdict = Verdict.FAIL if fail else Verdict.PASS
        fixes = []
        if verdict == Verdict.FAIL:
            fixes = [
                RequiredFixArtifact.model_validate(
                    {
                        "artifact_schema_version": 1,
                        "format": "json_patch",
                        "target_files": target_files or ["packages/"],
                        "patch_artifact": patch_artifact,
                        "validation_steps": ["address refactor critique findings"],
                        "acceptance_criteria": "refactor.critique gate passes",
                    },
                ),
            ]
        verdict_payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.LOW if verdict == Verdict.PASS else Severity.MEDIUM,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=[f"refactor://{tax_key}"],
            required_fixes=fixes,
        )
        critic_payloads.append(verdict_payload)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=verdict_payload,
            ),
        )

    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=REFACTOR_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or force_fail or orphan_gate_fail,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return gate.verdict == Verdict.FAIL


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
        verdict_payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.LOW if verdict == Verdict.PASS else Severity.MEDIUM,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=[f"refactor://post_stitch/{tax_key}"],
            required_fixes=fixes,
        )
        critic_payloads.append(verdict_payload)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=verdict_payload,
            ),
        )

    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=REFACTOR_POST_STITCH_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or force_fail,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return gate.verdict == Verdict.FAIL

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from orchestrator.profiles.enforcement_profiles import (
    EnforcementProfile,
    enforcement_profile_from_rows,
    latest_enforcement_block_from_rows,
    nimbusware_enforcement_depth_enabled,
)


def enforcement_wired_for_run(rows: list[dict[str, Any]]) -> bool:
    if nimbusware_enforcement_depth_enabled():
        return True
    return latest_enforcement_block_from_rows(rows) is not None


def active_enforcement_profile(rows: list[dict[str, Any]]) -> EnforcementProfile | None:
    if not enforcement_wired_for_run(rows):
        return None
    return enforcement_profile_from_rows(rows)


def e2e_required_for_profile(profile: EnforcementProfile) -> bool:
    return profile.e2e_mode == "required"


def normalize_e2e_for_enforcement(
    e2e_passed: bool | None,
    e2e_detail: str,
    profile: EnforcementProfile,
    *,
    e2e_enabled: bool,
) -> tuple[bool | None, str]:
    if not e2e_required_for_profile(profile):
        return e2e_passed, e2e_detail
    if not e2e_enabled:
        return False, e2e_detail or "e2e required by enforcement depth but disabled in workflow"
    if e2e_passed is None:
        detail = e2e_detail or "e2e required but skipped"
        return False, detail
    return e2e_passed, e2e_detail


def security_scan_required(profile: EnforcementProfile) -> bool:
    return profile.security_mode in ("bandit", "full_scan")


def run_milestone_enforcement(
    workspace: Path,
    profile: EnforcementProfile,
    *,
    scope_paths: list[str] | None,
    timeout_seconds: float = 300.0,
) -> dict[str, Any] | None:
    if not (profile.milestone_full_ci or profile.terminal_parity_ci):
        return None
    from orchestrator.workspace_ci_runner import run_enforcement_bundle

    result = run_enforcement_bundle(
        workspace,
        profile,
        scope_paths=scope_paths,
        milestone=True,
        timeout_seconds=timeout_seconds,
    )
    return result.to_metadata()


def terminal_enforcement_emitted(rows: list[dict[str, Any]]) -> bool:
    for row in reversed(rows):
        payload = row.get("payload") or {}
        if isinstance(payload, dict) and payload.get("stage_name") == "enforcement.gate":
            return True
        meta = row.get("metadata") or {}
        if meta.get("enforcement_gate") is True:
            return True
    return False


def emit_terminal_enforcement_gate(
    store: Any,
    run_id: UUID,
    workspace: Path,
    rows: list[dict[str, Any]],
    *,
    timeline_base_url: str | None = None,
    timeout_seconds: float = 600.0,
) -> dict[str, Any] | None:
    profile = active_enforcement_profile(rows)
    if profile is None or not profile.terminal_parity_ci:
        return None
    if terminal_enforcement_emitted(rows):
        return None
    from orchestrator.ci_bridge import attach_external_ci_metadata
    from orchestrator.workspace_ci_runner import run_workspace_ci_parity

    now = datetime.now(timezone.utc)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata={"enforcement_gate": True, "enforcement_level": profile.level},
            payload=StageStartedPayload(stage_name="enforcement.gate", attempt=1),
        ),
    )
    result = run_workspace_ci_parity(workspace, timeout_seconds=timeout_seconds)
    meta = {
        "enforcement_gate": True,
        "enforcement_level": profile.level,
        **result.to_metadata(),
    }
    verdict = "PASS" if result.passed else "FAIL"
    attach_external_ci_metadata(
        meta,
        run_id=run_id,
        verdict=verdict,
        stage_name="enforcement.gate",
        timeline_base_url=timeline_base_url,
    )
    if result.passed:
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=meta,
                payload=StagePassedPayload(stage_name="enforcement.gate", duration_ms=0),
            ),
        )
    else:
        store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=meta,
                payload=StageFailedPayload(
                    stage_name="enforcement.gate",
                    reason_code="enforcement_parity_failed",
                    message="terminal workspace CI parity did not pass",
                ),
            ),
        )
    return meta

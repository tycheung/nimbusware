from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.enforcement_profiles import (
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
    from nimbusware_orchestrator.workspace_ci_runner import run_enforcement_bundle

    result = run_enforcement_bundle(
        workspace,
        profile,
        scope_paths=scope_paths,
        milestone=True,
        timeout_seconds=timeout_seconds,
    )
    return result.to_metadata()

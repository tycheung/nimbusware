from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException

from api.deps import OrchDep
from api.errors import problem
from orchestrator.profiles.user_autopilot_profiles import apply_user_autopilot_at_run_start
from orchestrator.profiles.user_enforcement_profiles import apply_user_enforcement_at_run_start
from standards.persist import apply_standards_after_run_profiles
from standards.user_profiles import resolve_user_standards_profile


def apply_operator_profiles_at_run_start(
    store: Any,
    run_id: UUID,
    *,
    orch: OrchDep,
    workspace_path: str | None,
    autopilot_profile_id: str | None = None,
    enforcement_profile_id: str | None = None,
    standards_profile_id: str | None = None,
) -> None:
    if autopilot_profile_id and str(autopilot_profile_id).strip():
        applied = apply_user_autopilot_at_run_start(
            store,
            run_id,
            str(autopilot_profile_id),
            repo_root=orch.repo_root,
        )
        if applied is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "autopilot_profile_not_found",
                    "Unknown autopilot profile id",
                    details={"profile_id": autopilot_profile_id},
                ),
            )
    if enforcement_profile_id and str(enforcement_profile_id).strip():
        applied_enf = apply_user_enforcement_at_run_start(
            store,
            run_id,
            str(enforcement_profile_id),
            repo_root=orch.repo_root,
        )
        if applied_enf is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "enforcement_profile_not_found",
                    "Unknown enforcement profile id",
                    details={"profile_id": enforcement_profile_id},
                ),
            )
    if standards_profile_id and str(standards_profile_id).strip():
        if (
            resolve_user_standards_profile(
                str(standards_profile_id).strip(),
                repo_root=orch.repo_root,
            )
            is None
        ):
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "standards_profile_not_found",
                    "Unknown standards profile id",
                    details={"profile_id": standards_profile_id},
                ),
            )
    if workspace_path and str(workspace_path).strip():
        applied_std = apply_standards_after_run_profiles(
            store,
            run_id,
            workspace_path=workspace_path,
            repo_root=orch.repo_root,
            standards_profile_id=standards_profile_id,
        )
        if standards_profile_id and str(standards_profile_id).strip() and applied_std is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "standards_profile_not_found",
                    "Unknown standards profile id",
                    details={"profile_id": standards_profile_id},
                ),
            )

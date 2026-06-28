from __future__ import annotations

from typing import Any

from nimbusware_auth.models import ROLE_RANK
from nimbusware_iam.scopes import has_maker_admin


def _approver_ids_from_rows(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for row in rows:
        if row.get("event_type") != "stage.passed":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "deploy.approved":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        uid = str(meta.get("approver_user_id") or "").strip()
        kind = str(meta.get("approval_kind") or "maker").strip()
        if uid:
            out.append((uid, kind))
    return out


def deploy_dual_control_satisfied(rows: list[dict[str, Any]]) -> bool:
    kinds = {kind for _, kind in _approver_ids_from_rows(rows)}
    return "maker" in kinds and "fleet_admin" in kinds


def user_may_record_deploy_approval(
    *,
    user_id: str | None,
    is_fleet_admin: bool,
    session_role: str | None,
    chain: str,
    rows: list[dict[str, Any]],
) -> tuple[bool, str | None, str]:
    chain_s = (chain or "maker_only").strip()
    if chain_s == "maker_only":
        return True, None, "maker"

    if chain_s == "session_admin":
        if is_fleet_admin:
            return True, None, "fleet_admin"
        rank = ROLE_RANK.get(session_role or "", -1)
        if rank >= ROLE_RANK.get("session_admin", 2):
            return True, None, "maker"
        return False, "Deploy approval requires session admin or fleet admin", "maker"

    if chain_s == "dual_control":
        prior = _approver_ids_from_rows(rows)
        prior_kinds = {kind for _, kind in prior}
        if is_fleet_admin:
            if "fleet_admin" in prior_kinds:
                return False, "Fleet admin approval already recorded", "fleet_admin"
            if "maker" not in prior_kinds:
                return False, "Maker approval required before fleet admin sign-off", "fleet_admin"
            return True, None, "fleet_admin"
        if "maker" in prior_kinds:
            return False, "Waiting for fleet admin dual-control approval", "maker"
        return True, None, "maker"

    return True, None, "maker"


def resolve_deploy_approver_context(
    user: Any | None,
    *,
    api_scopes: tuple[str, ...] | list[str] | None = None,
    session_role: str | None = None,
) -> tuple[str | None, bool, str | None]:
    uid = str(getattr(user, "user_id", "") or "").strip() or None
    scopes = tuple(api_scopes or ())
    is_admin = has_maker_admin(scopes) or bool(getattr(user, "is_owner", False))
    return uid, is_admin, session_role

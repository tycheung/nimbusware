from __future__ import annotations

from typing import Any
from uuid import UUID

from config.collab_policy_store import load_collab_policy
from config.tenant_policy_store import load_tenant_collab_policy
from env import find_repo_root
from maker.collab.disciplines import normalize_discipline


def _policy_doc(tenant_slug: str | None) -> dict[str, Any]:
    slug = str(tenant_slug or "").strip()
    if slug:
        return load_tenant_collab_policy(slug)
    return load_collab_policy(find_repo_root())


def tenant_default_join_discipline(tenant_slug: str | None) -> str | None:
    raw = _policy_doc(tenant_slug).get("default_join_discipline")
    if raw is None:
        return None
    return normalize_discipline(str(raw))


def tenant_default_agent_overlay(
    tenant_slug: str | None,
    discipline: str | None,
) -> str | None:
    if not discipline:
        return None
    overlays = _policy_doc(tenant_slug).get("default_agent_overlays")
    if not isinstance(overlays, dict):
        return None
    ext = overlays.get(discipline) or overlays.get(str(discipline).lower())
    if ext is None:
        return None
    text = str(ext).strip()
    return text or None


def seed_tenant_agent_overlay_on_join(
    user_id: UUID | str,
    discipline: str | None,
    *,
    tenant_slug: str | None = None,
    repo_root: Any | None = None,
) -> bool:
    ext = tenant_default_agent_overlay(tenant_slug, discipline)
    if not ext or not discipline:
        return False
    from maker.user_agent_overlay import (
        load_user_agent_overlays,
        save_user_agent_overlay,
    )

    uid = str(user_id)
    existing = load_user_agent_overlays(uid, repo_root=repo_root)
    overlays = existing.get("overlays") if isinstance(existing, dict) else {}
    if isinstance(overlays, dict) and discipline in overlays:
        return False
    save_user_agent_overlay(
        uid,
        discipline,
        prompt_extension=ext,
        repo_root=repo_root,
    )
    return True

from __future__ import annotations

from typing import Any
from uuid import UUID

from nimbusware_maker.collab_disciplines import normalize_discipline
from nimbusware_maker.user_discipline_profile import load_user_discipline_profile


def normalize_discipline_or_none(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    return normalize_discipline(str(raw))


def resolve_join_discipline(
    *,
    body_discipline: str | None,
    invite_discipline: str | None,
    user_id: UUID,
    tenant_slug: str | None = None,
) -> str | None:
    for candidate in (body_discipline, invite_discipline):
        normalized = normalize_discipline_or_none(candidate)
        if normalized:
            return normalized
    from nimbusware_maker.tenant_collab_defaults import tenant_default_join_discipline

    tenant_hat = tenant_default_join_discipline(tenant_slug)
    if tenant_hat:
        return tenant_hat
    profile = load_user_discipline_profile(str(user_id))
    return profile.get("default_discipline")


def tenant_slug_for_session(session: Any) -> str | None:
    tenant_id = getattr(session, "tenant_id", None)
    if tenant_id is None:
        return None
    try:
        from nimbusware_env.env_flags import nimbusware_database_url
        from nimbusware_iam.store import build_iam_store

        iam = build_iam_store(nimbusware_database_url())
        tenant = iam.get_tenant(UUID(str(tenant_id)))
        if tenant is not None:
            return str(getattr(tenant, "slug", "") or "").strip() or None
    except Exception:
        return None
    return None

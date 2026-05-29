"""Fleet / org memory scope."""

from __future__ import annotations

import hashlib
from uuid import UUID

from nimbusware_env.edition import is_enterprise, require_enterprise_feature
from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_iam.context import resolve_store_tenant_id

_FLEET_SCOPE_PREFIX = "fleet"


def fleet_scope_hash(
    tenant_id: UUID,
    *,
    org_slug: str = "default",
) -> str:
    """Stable org/fleet scope id for cross-repo retrieval within a tenant."""
    slug = org_slug.strip().lower() or "default"
    raw = f"{_FLEET_SCOPE_PREFIX}:{tenant_id}:{slug}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def resolve_fleet_scope(
    *,
    tenant_id: UUID | None = None,
    org_slug: str = "default",
) -> tuple[UUID, str]:
    """Return ``(tenant_id, org_scope_hash)`` for fleet memory operations."""
    require_fleet_memory_feature()
    tid = tenant_id or resolve_store_tenant_id()
    return tid, fleet_scope_hash(tid, org_slug=org_slug)


def repo_scope_as_org_scope(repo_scope: str) -> str:
    """Individual edition: repo scope is the memory namespace."""
    return repo_scope


def memory_namespace_for_repo(repo_scope: str) -> str:
    """Scope key used by ``MemoryChunkStore`` for repo-local indexes."""
    return repo_scope_as_org_scope(repo_scope)


def require_fleet_memory_feature() -> None:
    require_enterprise_feature("fleet_memory")


def fleet_memory_enabled() -> bool:
    return is_enterprise()

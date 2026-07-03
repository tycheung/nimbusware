from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

from iam.constants import DEFAULT_TENANT_ID
from iam.models import AuthContext

_auth_ctx: ContextVar[AuthContext | None] = ContextVar("auth_ctx", default=None)


def set_auth_context(ctx: AuthContext | None) -> None:
    _auth_ctx.set(ctx)


def get_auth_context() -> AuthContext | None:
    return _auth_ctx.get()


def reset_auth_context() -> None:
    _auth_ctx.set(None)


def resolve_store_tenant_id() -> UUID:
    """Tenant id used for event-store reads/writes."""
    from env.edition import is_individual

    if is_individual():
        return DEFAULT_TENANT_ID
    ctx = get_auth_context()
    if ctx is not None:
        return ctx.tenant_id
    return DEFAULT_TENANT_ID

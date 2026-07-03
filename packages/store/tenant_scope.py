from __future__ import annotations

from uuid import UUID

from iam.context import resolve_store_tenant_id


def store_tenant_id() -> UUID:
    return resolve_store_tenant_id()

"""IAM data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    tenant_id: UUID
    tenant_slug: str
    key_id: UUID
    role_taxonomy_keys: tuple[str, ...]
    api_scopes: tuple[str, ...] = ("maker_user",)


@dataclass(frozen=True)
class TenantRecord:
    tenant_id: UUID
    slug: str
    display_name: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class ApiKeyCreateResult:
    key_id: UUID
    api_key: str
    key_prefix: str
    tenant_id: UUID
    label: str

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from nimbusware_iam.constants import DEFAULT_TENANT_ID, DEFAULT_TENANT_SLUG
from nimbusware_iam.crypto import api_key_prefix, generate_api_key, hash_api_key
from nimbusware_iam.models import ApiKeyCreateResult, AuthContext, TenantRecord
from nimbusware_iam.scopes import DEFAULT_USER_SCOPES, normalize_scopes


class InMemoryIamStore:
    """IAM store for unit tests without Postgres."""

    def __init__(self) -> None:
        self.tenants: dict[UUID, TenantRecord] = {}
        self.keys: dict[UUID, dict[str, Any]] = {}
        self._keys_by_hash: dict[str, UUID] = {}
        self.ensure_default_tenant()

    def ensure_default_tenant(self) -> TenantRecord:
        if DEFAULT_TENANT_ID in self.tenants:
            return self.tenants[DEFAULT_TENANT_ID]
        row = TenantRecord(
            tenant_id=DEFAULT_TENANT_ID,
            slug=DEFAULT_TENANT_SLUG,
            display_name="Default (Individual)",
            created_at=datetime.now(timezone.utc),
        )
        self.tenants[DEFAULT_TENANT_ID] = row
        return row

    def create_tenant(self, *, slug: str, display_name: str) -> TenantRecord:
        slug_n = slug.strip().lower()
        if any(t.slug == slug_n for t in self.tenants.values()):
            msg = f"tenant slug already exists: {slug_n}"
            raise ValueError(msg)
        tid = uuid4()
        row = TenantRecord(
            tenant_id=tid,
            slug=slug_n,
            display_name=display_name.strip() or slug_n,
            created_at=datetime.now(timezone.utc),
        )
        self.tenants[tid] = row
        return row

    def list_tenants(self) -> list[TenantRecord]:
        return sorted(self.tenants.values(), key=lambda t: t.slug)

    def get_tenant(self, tenant_id: UUID) -> TenantRecord | None:
        return self.tenants.get(tenant_id)

    def create_api_key(
        self,
        *,
        tenant_id: UUID,
        label: str = "",
        role_taxonomy_keys: list[str] | None = None,
        api_scopes: list[str] | None = None,
    ) -> ApiKeyCreateResult:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            msg = f"unknown tenant_id: {tenant_id}"
            raise ValueError(msg)
        plain = generate_api_key()
        key_id = uuid4()
        digest = hash_api_key(plain)
        prefix = api_key_prefix(plain)
        roles = tuple(sorted({k.strip().lower() for k in (role_taxonomy_keys or []) if k.strip()}))
        scopes = normalize_scopes(
            api_scopes if api_scopes is not None else list(DEFAULT_USER_SCOPES)
        )
        self.keys[key_id] = {
            "key_id": key_id,
            "tenant_id": tenant_id,
            "key_prefix": prefix,
            "key_hash": digest,
            "label": label.strip(),
            "role_taxonomy_keys": list(roles),
            "api_scopes": list(scopes),
            "revoked_at": None,
        }
        self._keys_by_hash[digest] = key_id
        return ApiKeyCreateResult(
            key_id=key_id,
            api_key=plain,
            key_prefix=prefix,
            tenant_id=tenant_id,
            label=label.strip(),
        )

    def verify_api_key(self, api_key: str) -> AuthContext | None:
        digest = hash_api_key(api_key.strip())
        key_id = self._keys_by_hash.get(digest)
        if key_id is None:
            return None
        rec = self.keys.get(key_id)
        if rec is None or rec.get("revoked_at") is not None:
            return None
        tenant = self.tenants.get(rec["tenant_id"])
        if tenant is None:
            return None
        roles = rec.get("role_taxonomy_keys") or []
        scopes = normalize_scopes(rec.get("api_scopes"))
        return AuthContext(
            tenant_id=tenant.tenant_id,
            tenant_slug=tenant.slug,
            key_id=key_id,
            role_taxonomy_keys=tuple(str(x) for x in roles),
            api_scopes=scopes,
        )


class PostgresIamStore:
    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def ensure_default_tenant(self) -> TenantRecord:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO hermes_tenant (tenant_id, slug, display_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (tenant_id) DO NOTHING
                    """,
                    (DEFAULT_TENANT_ID, DEFAULT_TENANT_SLUG, "Default (Individual)"),
                )
                cur.execute(
                    """
                    SELECT tenant_id, slug, display_name, created_at
                    FROM hermes_tenant WHERE tenant_id = %s
                    """,
                    (DEFAULT_TENANT_ID,),
                )
                row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _tenant_from_row(row)

    def create_tenant(self, *, slug: str, display_name: str) -> TenantRecord:
        tid = uuid4()
        slug_n = slug.strip().lower()
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO hermes_tenant (tenant_id, slug, display_name)
                    VALUES (%s, %s, %s)
                    RETURNING tenant_id, slug, display_name, created_at
                    """,
                    (tid, slug_n, display_name.strip() or slug_n),
                )
                row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _tenant_from_row(row)

    def list_tenants(self) -> list[TenantRecord]:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT tenant_id, slug, display_name, created_at
                    FROM hermes_tenant
                    ORDER BY slug ASC
                    """,
                )
                rows = cur.fetchall()
        return [_tenant_from_row(r) for r in rows]

    def get_tenant(self, tenant_id: UUID) -> TenantRecord | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT tenant_id, slug, display_name, created_at
                    FROM hermes_tenant WHERE tenant_id = %s
                    """,
                    (tenant_id,),
                )
                row = cur.fetchone()
        return _tenant_from_row(row) if row else None

    def create_api_key(
        self,
        *,
        tenant_id: UUID,
        label: str = "",
        role_taxonomy_keys: list[str] | None = None,
        api_scopes: list[str] | None = None,
    ) -> ApiKeyCreateResult:
        plain = generate_api_key()
        key_id = uuid4()
        digest = hash_api_key(plain)
        prefix = api_key_prefix(plain)
        roles = sorted({k.strip().lower() for k in (role_taxonomy_keys or []) if k.strip()})
        scopes = list(
            normalize_scopes(api_scopes if api_scopes is not None else list(DEFAULT_USER_SCOPES)),
        )
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO hermes_api_key (
                      key_id, tenant_id, key_prefix, key_hash, label,
                      role_taxonomy_keys, api_scopes
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    """,
                    (key_id, tenant_id, prefix, digest, label.strip(), roles, scopes),
                )
            conn.commit()
        return ApiKeyCreateResult(
            key_id=key_id,
            api_key=plain,
            key_prefix=prefix,
            tenant_id=tenant_id,
            label=label.strip(),
        )

    def verify_api_key(self, api_key: str) -> AuthContext | None:
        digest = hash_api_key(api_key.strip())
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT k.key_id, k.tenant_id, k.role_taxonomy_keys, k.api_scopes,
                           k.revoked_at, t.slug
                    FROM hermes_api_key k
                    JOIN hermes_tenant t ON t.tenant_id = k.tenant_id
                    WHERE k.key_hash = %s
                    LIMIT 1
                    """,
                    (digest,),
                )
                row = cur.fetchone()
        if row is None or row.get("revoked_at") is not None:
            return None
        roles_raw = row.get("role_taxonomy_keys") or []
        roles = tuple(str(x) for x in roles_raw) if isinstance(roles_raw, list) else ()
        scopes = normalize_scopes(row.get("api_scopes"))
        return AuthContext(
            tenant_id=UUID(str(row["tenant_id"])),
            tenant_slug=str(row["slug"]),
            key_id=UUID(str(row["key_id"])),
            role_taxonomy_keys=roles,
            api_scopes=scopes,
        )


def _tenant_from_row(row: dict[str, Any]) -> TenantRecord:
    created = row.get("created_at")
    if isinstance(created, datetime):
        created_at = created.astimezone(timezone.utc)
    else:
        created_at = None
    return TenantRecord(
        tenant_id=UUID(str(row["tenant_id"])),
        slug=str(row["slug"]),
        display_name=str(row["display_name"]),
        created_at=created_at,
    )


def build_iam_store(conninfo: str | None) -> InMemoryIamStore | PostgresIamStore:
    if conninfo:
        return PostgresIamStore(conninfo)
    return InMemoryIamStore()

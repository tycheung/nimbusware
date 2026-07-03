from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from config.provider_vault import decrypt_secret, encrypt_secret


@dataclass(frozen=True)
class ProviderConnectionRow:
    connection_id: UUID
    tenant_id: str | None
    user_id: str
    provider_id: str
    label: str
    connection_kind: str
    base_url: str | None
    default_model_id: str | None
    secret_set: bool
    last_probe_at: datetime | None
    last_probe_ok: bool | None
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class ProviderConnectionSecret:
    connection_id: UUID
    api_key: str | None
    subscription_connected: bool
    oauth_refresh_token: str | None = None


def _row_from_record(rec: dict[str, Any]) -> ProviderConnectionRow:
    last_probe = rec.get("last_probe_at")
    created = rec.get("created_at")
    updated = rec.get("updated_at")
    return ProviderConnectionRow(
        connection_id=rec["connection_id"],
        tenant_id=rec.get("tenant_id"),
        user_id=str(rec.get("user_id") or ""),
        provider_id=str(rec["provider_id"]),
        label=str(rec.get("label") or ""),
        connection_kind=str(rec.get("connection_kind") or "api_key"),
        base_url=rec.get("base_url"),
        default_model_id=rec.get("default_model_id"),
        secret_set=bool(rec.get("secret_blob")),
        last_probe_at=last_probe.astimezone(timezone.utc)
        if isinstance(last_probe, datetime)
        else None,
        last_probe_ok=rec.get("last_probe_ok"),
        created_at=created.astimezone(timezone.utc) if isinstance(created, datetime) else None,
        updated_at=updated.astimezone(timezone.utc) if isinstance(updated, datetime) else None,
    )


def _row_to_public(row: ProviderConnectionRow) -> dict[str, Any]:
    return {
        "connection_id": str(row.connection_id),
        "tenant_id": row.tenant_id,
        "user_id": row.user_id,
        "provider_id": row.provider_id,
        "label": row.label,
        "connection_kind": row.connection_kind,
        "base_url": row.base_url,
        "default_model_id": row.default_model_id,
        "secret_set": row.secret_set,
        "last_probe_at": row.last_probe_at.isoformat() if row.last_probe_at else None,
        "last_probe_ok": row.last_probe_ok,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def encode_secret_payload(
    *,
    connection_kind: str,
    api_key: str | None = None,
    subscription_connected: bool = False,
    oauth_refresh_token: str | None = None,
) -> bytes:
    if connection_kind == "subscription":
        if oauth_refresh_token and oauth_refresh_token.strip():
            return encrypt_secret(f"sub_oauth:{oauth_refresh_token.strip()}")
        flag = "1" if subscription_connected else "0"
        return encrypt_secret(f"subscription:{flag}")
    if not api_key or not api_key.strip():
        msg = "api_key required for api_key connection_kind"
        raise ValueError(msg)
    return encrypt_secret(api_key.strip())


def decode_secret_payload(
    blob: bytes | None, *, connection_kind: str
) -> ProviderConnectionSecret | None:
    plain = decrypt_secret(blob)
    if plain is None:
        return None
    if connection_kind == "subscription":
        if plain.startswith("sub_oauth:"):
            return ProviderConnectionSecret(
                connection_id=UUID(int=0),
                api_key=None,
                subscription_connected=True,
                oauth_refresh_token=plain[len("sub_oauth:") :],
            )
        connected = plain == "subscription:1"
        return ProviderConnectionSecret(
            connection_id=UUID(int=0),
            api_key=None,
            subscription_connected=connected,
            oauth_refresh_token=None,
        )
    return ProviderConnectionSecret(
        connection_id=UUID(int=0),
        api_key=plain,
        subscription_connected=False,
        oauth_refresh_token=None,
    )


class ProviderConnectionStore:
    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def list_for_user(
        self, *, user_id: str, tenant_id: str | None = None
    ) -> list[ProviderConnectionRow]:
        clauses = ["user_id = %s"]
        params: list[Any] = [user_id]
        if tenant_id is not None:
            clauses.append("(tenant_id IS NULL OR tenant_id = %s)")
            params.append(tenant_id)
        where = " AND ".join(clauses)
        sql = f"""
            SELECT connection_id, tenant_id, user_id, provider_id, label,
                   connection_kind, base_url, default_model_id, secret_blob,
                   last_probe_at, last_probe_ok, created_at, updated_at
            FROM nimbusware_provider_connection
            WHERE {where}
            ORDER BY provider_id, label
        """
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [_row_from_record(r) for r in rows]

    def get(self, connection_id: UUID, *, user_id: str) -> ProviderConnectionRow | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT connection_id, tenant_id, user_id, provider_id, label,
                           connection_kind, base_url, default_model_id, secret_blob,
                           last_probe_at, last_probe_ok, created_at, updated_at
                    FROM nimbusware_provider_connection
                    WHERE connection_id = %s AND user_id = %s
                    """,
                    (connection_id, user_id),
                )
                rec = cur.fetchone()
        if rec is None:
            return None
        return _row_from_record(rec)

    def get_secret(
        self,
        connection_id: UUID,
        *,
        user_id: str,
    ) -> ProviderConnectionSecret | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT connection_id, connection_kind, secret_blob
                    FROM nimbusware_provider_connection
                    WHERE connection_id = %s AND user_id = %s
                    """,
                    (connection_id, user_id),
                )
                rec = cur.fetchone()
        if rec is None:
            return None
        decoded = decode_secret_payload(
            rec.get("secret_blob"),
            connection_kind=str(rec.get("connection_kind") or "api_key"),
        )
        if decoded is None:
            return None
        return ProviderConnectionSecret(
            connection_id=rec["connection_id"],
            api_key=decoded.api_key,
            subscription_connected=decoded.subscription_connected,
        )

    def upsert(
        self,
        *,
        user_id: str,
        tenant_id: str | None,
        provider_id: str,
        label: str,
        connection_kind: str,
        base_url: str | None,
        default_model_id: str | None,
        secret_blob: bytes | None = None,
        connection_id: UUID | None = None,
    ) -> ProviderConnectionRow:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if connection_id is not None:
                    cur.execute(
                        """
                        UPDATE nimbusware_provider_connection
                        SET provider_id = %s,
                            label = %s,
                            connection_kind = %s,
                            base_url = %s,
                            default_model_id = %s,
                            secret_blob = COALESCE(%s, secret_blob),
                            tenant_id = %s,
                            updated_at = NOW()
                        WHERE connection_id = %s AND user_id = %s
                        RETURNING connection_id, tenant_id, user_id, provider_id, label,
                                  connection_kind, base_url, default_model_id, secret_blob,
                                  last_probe_at, last_probe_ok, created_at, updated_at
                        """,
                        (
                            provider_id,
                            label,
                            connection_kind,
                            base_url,
                            default_model_id,
                            secret_blob,
                            tenant_id,
                            connection_id,
                            user_id,
                        ),
                    )
                    rec = cur.fetchone()
                    if rec is None:
                        msg = "connection not found"
                        raise KeyError(msg)
                else:
                    cur.execute(
                        """
                        INSERT INTO nimbusware_provider_connection (
                          tenant_id, user_id, provider_id, label, connection_kind,
                          base_url, default_model_id, secret_blob
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING connection_id, tenant_id, user_id, provider_id, label,
                                  connection_kind, base_url, default_model_id, secret_blob,
                                  last_probe_at, last_probe_ok, created_at, updated_at
                        """,
                        (
                            tenant_id,
                            user_id,
                            provider_id,
                            label,
                            connection_kind,
                            base_url,
                            default_model_id,
                            secret_blob,
                        ),
                    )
                    rec = cur.fetchone()
            conn.commit()
        if rec is None:
            msg = "provider connection upsert returned no row"
            raise RuntimeError(msg)
        return _row_from_record(rec)

    def delete(self, connection_id: UUID, *, user_id: str) -> bool:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM nimbusware_provider_connection
                    WHERE connection_id = %s AND user_id = %s
                    """,
                    (connection_id, user_id),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def record_probe(
        self,
        connection_id: UUID,
        *,
        user_id: str,
        ok: bool,
    ) -> ProviderConnectionRow | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE nimbusware_provider_connection
                    SET last_probe_at = NOW(),
                        last_probe_ok = %s,
                        updated_at = NOW()
                    WHERE connection_id = %s AND user_id = %s
                    RETURNING connection_id, tenant_id, user_id, provider_id, label,
                              connection_kind, base_url, default_model_id, secret_blob,
                              last_probe_at, last_probe_ok, created_at, updated_at
                    """,
                    (ok, connection_id, user_id),
                )
                rec = cur.fetchone()
            conn.commit()
        if rec is None:
            return None
        return _row_from_record(rec)

    def export_metadata_for_user(self, *, user_id: str) -> list[dict[str, Any]]:
        return [_row_to_public(r) for r in self.list_for_user(user_id=user_id)]

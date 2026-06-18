from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from nimbusware_iam.constants import DEFAULT_TENANT_ID

SHARE_POLICIES = frozenset({"off", "claim_only", "managed_by_host", "full_auto"})
NODE_STATUSES = frozenset({"unknown", "online", "degraded", "offline"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ComputeNodeRow:
    node_id: UUID
    tenant_id: UUID
    session_id: UUID | None
    user_id: str
    display_name: str
    host_label: str
    base_url: str
    capabilities: dict[str, Any]
    share_policy: str
    allow_host_resource_management: bool
    last_heartbeat_at: datetime
    status: str
    created_at: datetime | None = None


def _row_from_record(rec: dict[str, Any]) -> ComputeNodeRow:
    caps = rec.get("capabilities")
    return ComputeNodeRow(
        node_id=rec["node_id"],
        tenant_id=rec["tenant_id"],
        session_id=rec.get("session_id"),
        user_id=str(rec.get("user_id") or ""),
        display_name=str(rec.get("display_name") or ""),
        host_label=str(rec.get("host_label") or ""),
        base_url=str(rec.get("base_url") or ""),
        capabilities=caps if isinstance(caps, dict) else {},
        share_policy=str(rec.get("share_policy") or "off"),
        allow_host_resource_management=bool(rec.get("allow_host_resource_management")),
        last_heartbeat_at=rec["last_heartbeat_at"],
        status=str(rec.get("status") or "unknown"),
        created_at=rec.get("created_at"),
    )


def row_to_public(row: ComputeNodeRow) -> dict[str, Any]:
    return {
        "node_id": str(row.node_id),
        "tenant_id": str(row.tenant_id),
        "session_id": str(row.session_id) if row.session_id else None,
        "user_id": row.user_id,
        "display_name": row.display_name,
        "host_label": row.host_label,
        "base_url": row.base_url,
        "capabilities": row.capabilities,
        "share_policy": row.share_policy,
        "allow_host_resource_management": row.allow_host_resource_management,
        "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class ComputeNodeStore(Protocol):
    def register(
        self,
        *,
        tenant_id: UUID,
        user_id: str,
        display_name: str,
        host_label: str,
        base_url: str,
        capabilities: dict[str, Any] | None = None,
        session_id: UUID | None = None,
        share_policy: str = "off",
        allow_host_resource_management: bool = False,
        node_id: UUID | None = None,
    ) -> ComputeNodeRow: ...

    def heartbeat(
        self,
        node_id: UUID,
        *,
        status: str | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> ComputeNodeRow | None: ...

    def get(self, node_id: UUID) -> ComputeNodeRow | None: ...

    def list_for_session(self, session_id: UUID) -> list[ComputeNodeRow]: ...

    def set_delegate_control(
        self,
        *,
        session_id: UUID,
        user_id: str,
        allow_host_resource_management: bool,
    ) -> ComputeNodeRow | None: ...


class InMemoryComputeNodeStore:
    def __init__(self) -> None:
        self._nodes: dict[UUID, ComputeNodeRow] = {}

    def register(
        self,
        *,
        tenant_id: UUID,
        user_id: str,
        display_name: str,
        host_label: str,
        base_url: str,
        capabilities: dict[str, Any] | None = None,
        session_id: UUID | None = None,
        share_policy: str = "off",
        allow_host_resource_management: bool = False,
        node_id: UUID | None = None,
    ) -> ComputeNodeRow:
        policy = share_policy if share_policy in SHARE_POLICIES else "off"
        now = _utc_now()
        nid = node_id or uuid4()
        row = ComputeNodeRow(
            node_id=nid,
            tenant_id=tenant_id,
            session_id=session_id,
            user_id=user_id,
            display_name=display_name,
            host_label=host_label,
            base_url=base_url,
            capabilities=dict(capabilities or {}),
            share_policy=policy,
            allow_host_resource_management=allow_host_resource_management,
            last_heartbeat_at=now,
            status="online",
            created_at=now,
        )
        self._nodes[nid] = row
        return row

    def heartbeat(
        self,
        node_id: UUID,
        *,
        status: str | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> ComputeNodeRow | None:
        row = self._nodes.get(node_id)
        if row is None:
            return None
        st = status if status in NODE_STATUSES else row.status
        caps = dict(capabilities) if capabilities is not None else row.capabilities
        updated = ComputeNodeRow(
            node_id=row.node_id,
            tenant_id=row.tenant_id,
            session_id=row.session_id,
            user_id=row.user_id,
            display_name=row.display_name,
            host_label=row.host_label,
            base_url=row.base_url,
            capabilities=caps,
            share_policy=row.share_policy,
            allow_host_resource_management=row.allow_host_resource_management,
            last_heartbeat_at=_utc_now(),
            status=st,
            created_at=row.created_at,
        )
        self._nodes[node_id] = updated
        return updated

    def get(self, node_id: UUID) -> ComputeNodeRow | None:
        return self._nodes.get(node_id)

    def list_for_session(self, session_id: UUID) -> list[ComputeNodeRow]:
        return [r for r in self._nodes.values() if r.session_id == session_id]

    def set_delegate_control(
        self,
        *,
        session_id: UUID,
        user_id: str,
        allow_host_resource_management: bool,
    ) -> ComputeNodeRow | None:
        for row in self._nodes.values():
            if row.session_id != session_id or row.user_id != user_id:
                continue
            updated = ComputeNodeRow(
                node_id=row.node_id,
                tenant_id=row.tenant_id,
                session_id=row.session_id,
                user_id=row.user_id,
                display_name=row.display_name,
                host_label=row.host_label,
                base_url=row.base_url,
                capabilities=row.capabilities,
                share_policy=row.share_policy,
                allow_host_resource_management=allow_host_resource_management,
                last_heartbeat_at=row.last_heartbeat_at,
                status=row.status,
                created_at=row.created_at,
            )
            self._nodes[row.node_id] = updated
            return updated
        return None


class PostgresComputeNodeStore:
    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def register(
        self,
        *,
        tenant_id: UUID,
        user_id: str,
        display_name: str,
        host_label: str,
        base_url: str,
        capabilities: dict[str, Any] | None = None,
        session_id: UUID | None = None,
        share_policy: str = "off",
        allow_host_resource_management: bool = False,
        node_id: UUID | None = None,
    ) -> ComputeNodeRow:
        policy = share_policy if share_policy in SHARE_POLICIES else "off"
        caps = dict(capabilities or {})
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if node_id is not None and self.get(node_id) is not None:
                    cur.execute(
                        """
                        UPDATE nimbusware_compute_node
                        SET display_name = %s, host_label = %s, base_url = %s,
                            capabilities = %s, session_id = %s, share_policy = %s,
                            allow_host_resource_management = %s,
                            last_heartbeat_at = NOW(), status = 'online'
                        WHERE node_id = %s
                        RETURNING node_id, tenant_id, session_id, user_id, display_name,
                                  host_label, base_url, capabilities, share_policy,
                                  allow_host_resource_management, last_heartbeat_at,
                                  status, created_at
                        """,
                        (
                            display_name,
                            host_label,
                            base_url,
                            Jsonb(caps),
                            session_id,
                            policy,
                            allow_host_resource_management,
                            node_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO nimbusware_compute_node (
                          node_id, tenant_id, session_id, user_id, display_name,
                          host_label, base_url, capabilities, share_policy,
                          allow_host_resource_management, last_heartbeat_at, status
                        ) VALUES (
                          COALESCE(%s, gen_random_uuid()), %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, NOW(), 'online'
                        )
                        RETURNING node_id, tenant_id, session_id, user_id, display_name,
                                  host_label, base_url, capabilities, share_policy,
                                  allow_host_resource_management, last_heartbeat_at,
                                  status, created_at
                        """,
                        (
                            node_id,
                            tenant_id,
                            session_id,
                            user_id,
                            display_name,
                            host_label,
                            base_url,
                            Jsonb(caps),
                            policy,
                            allow_host_resource_management,
                        ),
                    )
                rec = cur.fetchone()
            conn.commit()
        return _row_from_record(rec)

    def heartbeat(
        self,
        node_id: UUID,
        *,
        status: str | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> ComputeNodeRow | None:
        sets = ["last_heartbeat_at = NOW()"]
        params: list[Any] = []
        if status is not None and status in NODE_STATUSES:
            sets.append("status = %s")
            params.append(status)
        if capabilities is not None:
            sets.append("capabilities = %s")
            params.append(Jsonb(dict(capabilities)))
        params.append(node_id)
        sql = f"""
            UPDATE nimbusware_compute_node
            SET {", ".join(sets)}
            WHERE node_id = %s
            RETURNING node_id, tenant_id, session_id, user_id, display_name,
                      host_label, base_url, capabilities, share_policy,
                      allow_host_resource_management, last_heartbeat_at,
                      status, created_at
        """
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                rec = cur.fetchone()
            conn.commit()
        if rec is None:
            return None
        return _row_from_record(rec)

    def get(self, node_id: UUID) -> ComputeNodeRow | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT node_id, tenant_id, session_id, user_id, display_name,
                           host_label, base_url, capabilities, share_policy,
                           allow_host_resource_management, last_heartbeat_at,
                           status, created_at
                    FROM nimbusware_compute_node
                    WHERE node_id = %s
                    """,
                    (node_id,),
                )
                rec = cur.fetchone()
        if rec is None:
            return None
        return _row_from_record(rec)

    def list_for_session(self, session_id: UUID) -> list[ComputeNodeRow]:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT node_id, tenant_id, session_id, user_id, display_name,
                           host_label, base_url, capabilities, share_policy,
                           allow_host_resource_management, last_heartbeat_at,
                           status, created_at
                    FROM nimbusware_compute_node
                    WHERE session_id = %s
                    ORDER BY last_heartbeat_at DESC
                    """,
                    (session_id,),
                )
                rows = cur.fetchall()
        return [_row_from_record(r) for r in rows]

    def set_delegate_control(
        self,
        *,
        session_id: UUID,
        user_id: str,
        allow_host_resource_management: bool,
    ) -> ComputeNodeRow | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE nimbusware_compute_node
                    SET allow_host_resource_management = %s
                    WHERE session_id = %s AND user_id = %s
                    RETURNING node_id, tenant_id, session_id, user_id, display_name,
                              host_label, base_url, capabilities, share_policy,
                              allow_host_resource_management, last_heartbeat_at,
                              status, created_at
                    """,
                    (allow_host_resource_management, session_id, user_id),
                )
                rec = cur.fetchone()
            conn.commit()
        return _row_from_record(rec) if rec else None


_IN_MEMORY_SINGLETON: InMemoryComputeNodeStore | None = None


def build_compute_node_store(database_url: str | None) -> ComputeNodeStore:
    global _IN_MEMORY_SINGLETON
    if database_url:
        return PostgresComputeNodeStore(database_url)
    if _IN_MEMORY_SINGLETON is None:
        _IN_MEMORY_SINGLETON = InMemoryComputeNodeStore()
    return _IN_MEMORY_SINGLETON


def default_tenant_id() -> UUID:
    return DEFAULT_TENANT_ID

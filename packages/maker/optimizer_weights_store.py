from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from iam.constants import DEFAULT_TENANT_ID

DEFAULT_OPTIMIZER_WEIGHTS: dict[str, float] = {
    "headroom": 0.35,
    "model_fit": 0.30,
    "latency": 0.20,
    "cost": 0.15,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class OptimizerWeightsRecord:
    user_id: UUID
    tenant_id: UUID
    weights: dict[str, float]
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "tenant_id": str(self.tenant_id),
            "weights": dict(self.weights),
            "updated_at": self.updated_at.isoformat(),
        }


class OptimizerWeightsStore(Protocol):
    def get(self, *, user_id: UUID, tenant_id: UUID | None = None) -> OptimizerWeightsRecord: ...

    def put(
        self,
        *,
        user_id: UUID,
        weights: dict[str, float],
        tenant_id: UUID | None = None,
    ) -> OptimizerWeightsRecord: ...


def _normalize_weights(raw: dict[str, Any] | None) -> dict[str, float]:
    if not raw:
        return dict(DEFAULT_OPTIMIZER_WEIGHTS)
    out: dict[str, float] = {}
    for key, default in DEFAULT_OPTIMIZER_WEIGHTS.items():
        val = raw.get(key, default)
        try:
            out[key] = float(val)
        except (TypeError, ValueError):
            out[key] = default
    return out


class InMemoryOptimizerWeightsStore:
    def __init__(self) -> None:
        self._rows: dict[tuple[UUID, UUID], OptimizerWeightsRecord] = {}

    def get(self, *, user_id: UUID, tenant_id: UUID | None = None) -> OptimizerWeightsRecord:
        tid = tenant_id or DEFAULT_TENANT_ID
        row = self._rows.get((user_id, tid))
        if row is None:
            now = _utc_now()
            return OptimizerWeightsRecord(
                user_id=user_id,
                tenant_id=tid,
                weights=dict(DEFAULT_OPTIMIZER_WEIGHTS),
                updated_at=now,
            )
        return row

    def put(
        self,
        *,
        user_id: UUID,
        weights: dict[str, float],
        tenant_id: UUID | None = None,
    ) -> OptimizerWeightsRecord:
        tid = tenant_id or DEFAULT_TENANT_ID
        now = _utc_now()
        row = OptimizerWeightsRecord(
            user_id=user_id,
            tenant_id=tid,
            weights=_normalize_weights(weights),
            updated_at=now,
        )
        self._rows[(user_id, tid)] = row
        return row


class PostgresOptimizerWeightsStore:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

    def get(self, *, user_id: UUID, tenant_id: UUID | None = None) -> OptimizerWeightsRecord:
        tid = tenant_id or DEFAULT_TENANT_ID
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT user_id, tenant_id, weights, updated_at
                FROM nimbusware_user_optimizer_weights
                WHERE user_id = %s AND tenant_id = %s
                """,
                (user_id, tid),
            )
            row = cur.fetchone()
        if row is None:
            return OptimizerWeightsRecord(
                user_id=user_id,
                tenant_id=tid,
                weights=dict(DEFAULT_OPTIMIZER_WEIGHTS),
                updated_at=_utc_now(),
            )
        weights = row.get("weights")
        return OptimizerWeightsRecord(
            user_id=row["user_id"],
            tenant_id=row["tenant_id"],
            weights=_normalize_weights(weights if isinstance(weights, dict) else None),
            updated_at=row["updated_at"],
        )

    def put(
        self,
        *,
        user_id: UUID,
        weights: dict[str, float],
        tenant_id: UUID | None = None,
    ) -> OptimizerWeightsRecord:
        tid = tenant_id or DEFAULT_TENANT_ID
        normalized = _normalize_weights(weights)
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_user_optimizer_weights (user_id, tenant_id, weights, updated_at)
                VALUES (%s, %s, %s::jsonb, %s)
                ON CONFLICT (user_id, tenant_id) DO UPDATE SET
                  weights = EXCLUDED.weights,
                  updated_at = EXCLUDED.updated_at
                RETURNING user_id, tenant_id, weights, updated_at
                """,
                (user_id, tid, Jsonb(normalized), now),
            )
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        w = row.get("weights")
        return OptimizerWeightsRecord(
            user_id=row["user_id"],
            tenant_id=row["tenant_id"],
            weights=_normalize_weights(w if isinstance(w, dict) else None),
            updated_at=row["updated_at"],
        )


_store: InMemoryOptimizerWeightsStore | None = None


def build_optimizer_weights_store(database_url: str | None) -> OptimizerWeightsStore:
    global _store
    if database_url:
        return PostgresOptimizerWeightsStore(database_url)
    if _store is None:
        _store = InMemoryOptimizerWeightsStore()
    return _store

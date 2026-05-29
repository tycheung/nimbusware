"""Postgres and in-memory configuration stores."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from hermes_config.protocol import ConfigDocumentRow, ConfigStore

_NS = "namespace"
_KEY = "document_key"


def _content_digest(content: dict[str, Any]) -> str:
    raw = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _row_from_record(rec: dict[str, Any]) -> ConfigDocumentRow:
    content = rec["content"]
    if not isinstance(content, dict):
        msg = "config document content must be a JSON object"
        raise ValueError(msg)
    updated = rec.get("updated_at")
    if isinstance(updated, datetime):
        updated_at = updated.astimezone(timezone.utc)
    else:
        updated_at = None
    return ConfigDocumentRow(
        namespace=str(rec[_NS]),
        document_key=str(rec[_KEY]),
        version=int(rec["version"]),
        content=content,
        content_sha256_16=str(rec["content_sha256_16"]),
        updated_at=updated_at,
    )


class PostgresConfigStore:
    """Authoritative config in ``hermes_config_document``."""

    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def get(self, namespace: str, document_key: str) -> ConfigDocumentRow | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT namespace, document_key, version, content,
                           content_sha256_16, updated_at
                    FROM hermes_config_document
                    WHERE namespace = %s AND document_key = %s
                    """,
                    (namespace, document_key),
                )
                rec = cur.fetchone()
        if rec is None:
            return None
        return _row_from_record(rec)

    def upsert(
        self,
        namespace: str,
        document_key: str,
        content: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> ConfigDocumentRow:
        if not isinstance(content, dict):
            msg = "content must be a mapping"
            raise ValueError(msg)
        digest = _content_digest(content)
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if expected_version is not None:
                    cur.execute(
                        """
                        UPDATE hermes_config_document
                        SET version = version + 1,
                            content = %s,
                            content_sha256_16 = %s,
                            updated_at = NOW()
                        WHERE namespace = %s AND document_key = %s
                          AND version = %s
                        RETURNING namespace, document_key, version, content,
                                  content_sha256_16, updated_at
                        """,
                        (
                            Jsonb(content),
                            digest,
                            namespace,
                            document_key,
                            expected_version,
                        ),
                    )
                    rec = cur.fetchone()
                    if rec is None:
                        msg = (
                            f"config version conflict: {namespace}/{document_key} "
                            f"expected version {expected_version}"
                        )
                        raise ValueError(msg)
                else:
                    cur.execute(
                        """
                        INSERT INTO hermes_config_document (
                          namespace, document_key, version, content,
                          content_sha256_16, updated_at
                        ) VALUES (%s, %s, 1, %s, %s, NOW())
                        ON CONFLICT (namespace, document_key) DO UPDATE SET
                          version = hermes_config_document.version + 1,
                          content = EXCLUDED.content,
                          content_sha256_16 = EXCLUDED.content_sha256_16,
                          updated_at = NOW()
                        RETURNING namespace, document_key, version, content,
                                  content_sha256_16, updated_at
                        """,
                        (namespace, document_key, Jsonb(content), digest),
                    )
                    rec = cur.fetchone()
                conn.commit()
        if rec is None:
            msg = "config upsert failed"
            raise RuntimeError(msg)
        return _row_from_record(rec)

    def list_keys(self, namespace: str) -> list[str]:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT document_key FROM hermes_config_document
                    WHERE namespace = %s ORDER BY document_key
                    """,
                    (namespace,),
                )
                rows = cur.fetchall()
        return [str(r[0]) for r in rows]

    def delete(self, namespace: str, document_key: str) -> bool:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM hermes_config_document
                    WHERE namespace = %s AND document_key = %s
                    """,
                    (namespace, document_key),
                )
                deleted = cur.rowcount > 0
                conn.commit()
        return deleted


class InMemoryConfigStore:
    """Volatile store for unit tests without Postgres."""

    def __init__(self) -> None:
        self._docs: dict[tuple[str, str], ConfigDocumentRow] = {}

    def get(self, namespace: str, document_key: str) -> ConfigDocumentRow | None:
        return self._docs.get((namespace, document_key))

    def upsert(
        self,
        namespace: str,
        document_key: str,
        content: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> ConfigDocumentRow:
        if not isinstance(content, dict):
            msg = "content must be a mapping"
            raise ValueError(msg)
        key = (namespace, document_key)
        existing = self._docs.get(key)
        if expected_version is not None:
            if existing is None or existing.version != expected_version:
                msg = (
                    f"config version conflict: {namespace}/{document_key} "
                    f"expected version {expected_version}"
                )
                raise ValueError(msg)
            new_ver = expected_version + 1
        elif existing is not None:
            new_ver = existing.version + 1
        else:
            new_ver = 1
        row = ConfigDocumentRow(
            namespace=namespace,
            document_key=document_key,
            version=new_ver,
            content=dict(content),
            content_sha256_16=_content_digest(content),
            updated_at=datetime.now(timezone.utc),
        )
        self._docs[key] = row
        return row

    def list_keys(self, namespace: str) -> list[str]:
        keys = [k for (ns, k) in self._docs if ns == namespace]
        return sorted(keys)

    def delete(self, namespace: str, document_key: str) -> bool:
        return self._docs.pop((namespace, document_key), None) is not None


# Satisfy structural typing for tests that annotate ConfigStore
def _as_config_store(store: PostgresConfigStore | InMemoryConfigStore) -> ConfigStore:
    return store

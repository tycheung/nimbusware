from __future__ import annotations

import re
from typing import Any

from config.keys import NS_TENANT_POLICY
from config.store import PostgresConfigStore
from env.env_flags import env_str


def _store() -> PostgresConfigStore | None:
    conn = env_str("NIMBUSWARE_DATABASE_URL")
    if not conn:
        return None
    return PostgresConfigStore(conn)


def _tenant_key(kind: str, tenant_slug: str) -> str:
    slug = tenant_slug.strip()
    if not slug:
        raise ValueError("tenant_slug required")
    return f"{kind}/{slug}"


def load_tenant_collab_policy(tenant_slug: str) -> dict[str, Any]:
    store = _store()
    if store is None:
        from config.collab_policy_store import load_collab_policy
        from env import find_repo_root

        return load_collab_policy(find_repo_root())
    row = store.get(NS_TENANT_POLICY, _tenant_key("collab", tenant_slug))
    if row is None:
        return {"version": 1}
    return dict(row.content)


def save_tenant_collab_policy(tenant_slug: str, doc: dict[str, Any]) -> dict[str, Any]:
    store = _store()
    if store is None:
        from config.collab_policy_store import save_collab_policy
        from env import find_repo_root

        save_collab_policy(find_repo_root(), doc)
        return doc
    row = store.upsert(NS_TENANT_POLICY, _tenant_key("collab", tenant_slug), doc)
    return dict(row.content)


def load_tenant_model_policy(tenant_slug: str) -> dict[str, Any]:
    store = _store()
    if store is None:
        from config.model_policy_store import load_model_policy
        from env import find_repo_root

        return load_model_policy(find_repo_root())
    row = store.get(NS_TENANT_POLICY, _tenant_key("model", tenant_slug))
    if row is None:
        return {"version": 1}
    return dict(row.content)


def save_tenant_model_policy(tenant_slug: str, doc: dict[str, Any]) -> dict[str, Any]:
    store = _store()
    if store is None:
        from config.model_policy_store import save_model_policy
        from env import find_repo_root

        save_model_policy(find_repo_root(), doc)
        return doc
    row = store.upsert(NS_TENANT_POLICY, _tenant_key("model", tenant_slug), doc)
    return dict(row.content)


def load_tenant_audit_policy(tenant_slug: str) -> dict[str, Any]:
    store = _store()
    if store is None:
        return {"version": 1, "legal_hold": False, "redaction_patterns": []}
    row = store.get(NS_TENANT_POLICY, _tenant_key("audit", tenant_slug))
    if row is None:
        return {"version": 1, "legal_hold": False, "redaction_patterns": []}
    return dict(row.content)


def save_tenant_audit_policy(tenant_slug: str, doc: dict[str, Any]) -> dict[str, Any]:
    store = _store()
    if store is None:
        return doc
    row = store.upsert(NS_TENANT_POLICY, _tenant_key("audit", tenant_slug), doc)
    return dict(row.content)


def audit_redaction(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    secret_keys = frozenset(
        {"api_key", "token", "password", "secret", "connection_id", "api_key_ref"},
    )
    for key, value in payload.items():
        lk = str(key).lower()
        if any(part in lk for part in secret_keys):
            out[key] = "[redacted]"
        elif isinstance(value, dict):
            out[key] = audit_redaction(value)
        elif isinstance(value, list):
            out[key] = [audit_redaction(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, str) and re.search(r"(sk-|api[_-]?key)", value, re.I):
            out[key] = "[redacted]"
        else:
            out[key] = value
    return out

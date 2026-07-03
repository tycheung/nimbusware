from __future__ import annotations

import os
from uuid import uuid4

import pytest

from iam.store import PostgresIamStore, hash_api_key

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_iam_create_and_verify_api_key() -> None:
    store = PostgresIamStore(_url())
    store.ensure_default_tenant()
    tenant = store.create_tenant(slug=f"lane-v2-{uuid4().hex[:8]}", display_name="Lane V2")
    created = store.create_api_key(tenant_id=tenant.tenant_id, label="integration")
    assert hash_api_key(created.api_key)
    ctx = store.verify_api_key(created.api_key)
    assert ctx is not None
    assert ctx.tenant_id == tenant.tenant_id
    assert "maker_user" in ctx.api_scopes or "maker_admin" in ctx.api_scopes

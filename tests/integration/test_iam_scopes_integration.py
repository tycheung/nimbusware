"""Enterprise IAM scope wiring on Postgres."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from nimbusware_iam.store import PostgresIamStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_iam_admin_scope_on_bootstrap_key() -> None:
    store = PostgresIamStore(_url())
    store.ensure_default_tenant()
    tenant = store.create_tenant(slug=f"admin-{uuid4().hex[:8]}", display_name="Admin scope")
    created = store.create_api_key(
        tenant_id=tenant.tenant_id,
        label="admin-integration",
        api_scopes=["maker_admin"],
    )
    ctx = store.verify_api_key(created.api_key)
    assert ctx is not None
    assert "maker_admin" in ctx.api_scopes

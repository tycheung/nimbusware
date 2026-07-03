from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from config.provider_connections import ProviderConnectionRow
from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN


@pytest.fixture(autouse=True)
def _subscription_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_ISSUER", "https://tenant.auth0.com")
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_CLIENT_ID", "desktop-client")
    monkeypatch.setenv(
        "NIMBUSWARE_SUBSCRIPTION_OAUTH_REDIRECT_URI",
        "http://testserver/v1/platform/provider-subscriptions/oauth/callback",
    )
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_MOCK", "1")


def test_subscription_oauth_status_lists_providers(client: TestClient) -> None:
    res = client.get(
        "/v1/platform/provider-subscriptions/oauth/status",
        headers={"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["mock_mode"] is True
    ids = {row["provider_id"] for row in body["providers"]}
    assert "chatgpt_plus" in ids
    chatgpt = next(row for row in body["providers"] if row["provider_id"] == "chatgpt_plus")
    assert chatgpt["oauth_ready"] is True
    assert chatgpt["authorize_path"].endswith("/chatgpt_plus/oauth/authorize")


def test_subscription_oauth_mock_flow_upserts_vault(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = uuid4()
    mock_store = MagicMock()
    mock_store.list_for_user.return_value = []
    mock_store.upsert.return_value = ProviderConnectionRow(
        connection_id=cid,
        tenant_id=None,
        user_id="",
        provider_id="chatgpt_plus",
        label="ChatGPT Plus (desktop)",
        connection_kind="subscription",
        base_url=None,
        default_model_id=None,
        secret_set=True,
        last_probe_at=None,
        last_probe_ok=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(
        "api.routes.provider_subscription_oauth._connection_store",
        lambda: mock_store,
    )
    start = client.get(
        "/v1/platform/provider-subscriptions/chatgpt_plus/oauth/authorize",
        headers={"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN},
        follow_redirects=False,
    )
    assert start.status_code == 302
    assert "mock-authorize" in start.headers["location"]
    mid = client.get(
        start.headers["location"],
        headers={"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN},
        follow_redirects=False,
    )
    assert mid.status_code == 302
    done = client.get(
        mid.headers["location"],
        headers={"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN},
        follow_redirects=False,
    )
    assert done.status_code == 302
    assert "desktop-subscriptions" in done.headers["location"]
    mock_store.upsert.assert_called_once()
    assert mock_store.upsert.call_args.kwargs["provider_id"] == "chatgpt_plus"


def test_subscription_honor_system_link_works_when_oauth_configured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cid = uuid4()
    mock_store = MagicMock()
    mock_store.list_for_user.return_value = []
    mock_store.upsert.return_value = ProviderConnectionRow(
        connection_id=cid,
        tenant_id=None,
        user_id="",
        provider_id="chatgpt_plus",
        label="ChatGPT Plus (desktop)",
        connection_kind="subscription",
        base_url=None,
        default_model_id=None,
        secret_set=True,
        last_probe_at=None,
        last_probe_ok=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(
        "api.routes.provider_connections._store",
        lambda: mock_store,
    )
    res = client.post(
        "/v1/platform/provider-connections/subscription-link",
        headers={
            "X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
            "Content-Type": "application/json",
        },
        json={"provider_id": "chatgpt_plus", "subscription_connected": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["connection"]["provider_id"] == "chatgpt_plus"
    assert body["connection"]["connection_kind"] == "subscription"
    mock_store.upsert.assert_called_once()


def test_subscription_oauth_status_reports_not_ready_without_client_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_ISSUER", "https://tenant.auth0.com")
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_MOCK", "0")
    res = client.get(
        "/v1/platform/provider-subscriptions/oauth/status",
        headers={"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN},
    )
    assert res.status_code == 200
    chatgpt = next(row for row in res.json()["providers"] if row["provider_id"] == "chatgpt_plus")
    assert chatgpt["oauth_ready"] is False

from __future__ import annotations

from fastapi.testclient import TestClient


def test_external_chat_capabilities_requires_admin(client: TestClient) -> None:
    r = client.get("/v1/integrations/external-chat")
    assert r.status_code == 401


def test_external_chat_webhook_with_admin_token(client: TestClient) -> None:
    from nimbusware_env.admin_token import nimbusware_admin_token

    r = client.post(
        "/v1/integrations/external-chat/webhook",
        headers={"X-Nimbusware-Admin-Token": nimbusware_admin_token()},
        json={"text": "/help", "source": "test"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "Commands" in body["reply"]
    assert body["note"]


def test_external_chat_webhook_with_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_WEBHOOK_SECRET", "test-hook-secret")
    r = client.post(
        "/v1/integrations/external-chat/webhook",
        headers={"X-Nimbusware-Webhook-Secret": "test-hook-secret"},
        json={"text": "/help"},
    )
    assert r.status_code == 200

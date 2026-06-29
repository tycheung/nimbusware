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


def test_external_chat_webhook_persists_session_run_id(client: TestClient, monkeypatch) -> None:
    from nimbusware_env.admin_token import nimbusware_admin_token

    run_resp = type("Resp", (), {"status_code": 200, "text": ""})()
    run_resp.json = lambda: {"run_id": "00000000-0000-4000-8000-000000000088"}  # type: ignore[method-assign]

    monkeypatch.setattr(
        "nimbusware_console.operator_chat_core.chat_svc.create_run",
        lambda _payload: run_resp,
    )

    headers = {"X-Nimbusware-Admin-Token": nimbusware_admin_token()}
    session = "slack-channel-99"
    started = client.post(
        "/v1/integrations/external-chat/webhook",
        headers=headers,
        json={"text": "/run micro_slice", "source": "slack", "session_id": session},
    )
    assert started.status_code == 200
    assert started.json()["last_run_id"] == "00000000-0000-4000-8000-000000000088"

    follow = client.post(
        "/v1/integrations/external-chat/webhook",
        headers=headers,
        json={"text": "add caching layer", "source": "slack", "session_id": session},
    )
    assert follow.status_code == 200
    assert follow.json()["last_run_id"] == "00000000-0000-4000-8000-000000000088"

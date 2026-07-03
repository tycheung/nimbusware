from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app
from maker.push_subscriptions import clear_push_subscriptions


def test_push_subscription_register_and_list(monkeypatch, tmp_path) -> None:
    clear_push_subscriptions()
    monkeypatch.setenv("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY", "test-vapid-public-key")
    monkeypatch.setenv(
        "NIMBUSWARE_MAKER_PUSH_SUBSCRIPTIONS_FILE",
        str(tmp_path / "push.json"),
    )
    with TestClient(app) as client:
        resp = client.post(
            "/v1/maker/push-subscriptions",
            json={
                "endpoint": "https://push.example/sub/abc",
                "keys": {"p256dh": "k1", "auth": "k2"},
                "run_id": "run-abc",
            },
        )
        assert resp.status_code == 200
        listed = client.get("/v1/maker/push-subscriptions")
        assert listed.status_code == 200
        body = listed.json()
        assert body["enabled"] is True
        assert len(body["subscriptions"]) == 1
        assert body["subscriptions"][0]["run_id"] == "run-abc"


def test_push_subscription_disabled_without_vapid(monkeypatch) -> None:
    clear_push_subscriptions()
    monkeypatch.delenv("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY", raising=False)
    with TestClient(app) as client:
        resp = client.post(
            "/v1/maker/push-subscriptions",
            json={"endpoint": "https://push.example/sub/x", "keys": {}},
        )
        assert resp.status_code == 503

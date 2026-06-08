from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from nimbusware_maker.push_subscriptions import clear_push_subscriptions, register_push_subscription
from nimbusware_maker.web_push_notify import send_campaign_push


def test_send_campaign_push_skips_without_vapid(monkeypatch) -> None:
    clear_push_subscriptions()
    monkeypatch.delenv("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("NIMBUSWARE_MAKER_VAPID_PRIVATE_KEY", raising=False)
    out = send_campaign_push(uuid4(), event_type="campaign.created", title="t", body="b")
    assert out["status"] == "skipped"


def test_send_campaign_push_delivers(monkeypatch) -> None:
    clear_push_subscriptions()
    monkeypatch.setenv("NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY", "pub")
    monkeypatch.setenv("NIMBUSWARE_MAKER_VAPID_PRIVATE_KEY", "priv")
    run_id = uuid4()
    register_push_subscription(
        {
            "endpoint": "https://push.example/sub/1",
            "keys": {"p256dh": "k1", "auth": "k2"},
        },
        run_id=str(run_id),
    )
    mock_webpush = MagicMock()
    with patch("pywebpush.webpush", mock_webpush):
        out = send_campaign_push(
            run_id,
            event_type="campaign.completed",
            title="Done",
            body="All slices passed",
        )
    assert out["status"] == "sent"
    assert out["sent"] == 1
    mock_webpush.assert_called_once()
    data = mock_webpush.call_args.kwargs["data"]
    payload = json.loads(data)
    assert payload["run_id"] == str(run_id)
    assert payload["title"] == "Done"

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from config.provider_connections import (
    ProviderConnectionRow,
    _row_from_record,
    _row_to_public,
    decode_secret_payload,
    encode_secret_payload,
)
from config.provider_vault import decrypt_secret, encrypt_secret
from orchestrator.provider_registry import (
    load_provider_presets,
    probe_connection_row,
    probe_subscription_connection,
)

REPO = Path(__file__).resolve().parents[2]


def test_provider_vault_roundtrip() -> None:
    blob = encrypt_secret("sk-test-key-123")
    assert decrypt_secret(blob) == "sk-test-key-123"


def test_provider_vault_rejects_invalid_blob() -> None:
    with pytest.raises(ValueError, match="invalid provider secret blob"):
        decrypt_secret(b"\x00" + b"x" * 20)


def test_subscription_secret_payload() -> None:
    blob = encode_secret_payload(connection_kind="subscription", subscription_connected=True)
    decoded = decode_secret_payload(blob, connection_kind="subscription")
    assert decoded is not None
    assert decoded.subscription_connected is True
    assert decoded.api_key is None
    assert decoded.oauth_refresh_token is None


def test_subscription_oauth_secret_payload() -> None:
    blob = encode_secret_payload(
        connection_kind="subscription",
        subscription_connected=True,
        oauth_refresh_token="rt-xyz",
    )
    decoded = decode_secret_payload(blob, connection_kind="subscription")
    assert decoded is not None
    assert decoded.subscription_connected is True
    assert decoded.oauth_refresh_token == "rt-xyz"


def test_load_provider_presets_includes_gemini() -> None:
    presets = load_provider_presets(REPO)
    ids = {p["id"] for p in presets}
    assert "google" in ids
    assert "openai_subscription" not in ids
    assert "anthropic_subscription" not in ids
    google = next(p for p in presets if p["id"] == "google")
    assert "generativelanguage.googleapis.com" in (google.get("default_base_url") or "")


def test_api_key_secret_payload_roundtrip() -> None:
    blob = encode_secret_payload(connection_kind="api_key", api_key="sk-abc")
    decoded = decode_secret_payload(blob, connection_kind="api_key")
    assert decoded is not None
    assert decoded.api_key == "sk-abc"
    assert decoded.subscription_connected is False


def test_encode_api_key_required() -> None:
    with pytest.raises(ValueError, match="api_key required"):
        encode_secret_payload(connection_kind="api_key", api_key="")


def test_provider_connection_row_mapping() -> None:
    cid = uuid4()
    now = datetime.now(timezone.utc)
    row = _row_from_record(
        {
            "connection_id": cid,
            "tenant_id": None,
            "user_id": "u1",
            "provider_id": "openai",
            "label": "work",
            "connection_kind": "api_key",
            "base_url": "https://api.openai.com/v1",
            "default_model_id": "gpt-4o-mini",
            "secret_blob": b"x",
            "last_probe_at": now,
            "last_probe_ok": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    assert isinstance(row, ProviderConnectionRow)
    public = _row_to_public(row)
    assert public["connection_id"] == str(cid)
    assert public["secret_set"] is True
    assert public["last_probe_ok"] is True


def test_decode_secret_payload_missing_blob() -> None:
    assert decode_secret_payload(None, connection_kind="api_key") is None


def test_probe_subscription_disconnected() -> None:
    result = probe_subscription_connection(subscription_connected=False)
    assert result["ok"] is False


def test_probe_connection_row_missing_key() -> None:
    result = probe_connection_row(
        REPO,
        provider_id="openai",
        connection_kind="api_key",
        base_url=None,
        api_key=None,
        subscription_connected=False,
    )
    assert result["ok"] is False

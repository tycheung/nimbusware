from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_config.provider_connections import encode_secret_payload, decode_secret_payload
from nimbusware_config.provider_vault import decrypt_secret, encrypt_secret
from nimbusware_orchestrator.provider_registry import (
    load_provider_presets,
    probe_connection_row,
    probe_subscription_connection,
)

REPO = Path(__file__).resolve().parents[2]


def test_provider_vault_roundtrip() -> None:
    blob = encrypt_secret("sk-test-key-123")
    assert decrypt_secret(blob) == "sk-test-key-123"


def test_subscription_secret_payload() -> None:
    blob = encode_secret_payload(connection_kind="subscription", subscription_connected=True)
    decoded = decode_secret_payload(blob, connection_kind="subscription")
    assert decoded is not None
    assert decoded.subscription_connected is True
    assert decoded.api_key is None


def test_load_provider_presets_includes_gemini() -> None:
    presets = load_provider_presets(REPO)
    ids = {p["id"] for p in presets}
    assert "google" in ids
    assert "openai_subscription" in ids
    google = next(p for p in presets if p["id"] == "google")
    assert "generativelanguage.googleapis.com" in (google.get("default_base_url") or "")


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

from __future__ import annotations

import pytest

from nimbusware_compute.worker_policy import (
    DEFAULT_MAX_PAYLOAD_BYTES,
    sanitize_work_unit_payload,
)


def test_sanitize_strips_api_key_fields() -> None:
    out = sanitize_work_unit_payload(
        {"stage": "implement", "api_key": "sk-secret", "model_id": "qwen"},
    )
    assert "api_key" not in out
    assert out["model_id"] == "qwen"


def test_sanitize_rejects_oversized_payload() -> None:
    huge = {"blob": "x" * (DEFAULT_MAX_PAYLOAD_BYTES + 1)}
    with pytest.raises(ValueError, match="exceeds"):
        sanitize_work_unit_payload(huge)


def test_sanitize_blocks_env_path_literal() -> None:
    out = sanitize_work_unit_payload({"path": ".env", "workspace": "/repo"})
    assert out == {"workspace": "/repo"}

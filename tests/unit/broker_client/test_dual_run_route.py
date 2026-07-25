from __future__ import annotations

import pytest
from fastapi import HTTPException

from broker_client.dual_run_route import map_domain_broker_http_miss
from broker_client.peel_assert import normalize_domain_tool_result, normalize_tool_result


def test_map_domain_broker_http_miss_peel_off_reraises() -> None:
    with pytest.raises(RuntimeError, match="legacy down"):
        map_domain_broker_http_miss(
            RuntimeError("legacy down"),
            feature="memory_search",
            enabled=lambda: False,
            only=lambda: False,
            only_code="broker_memory_only",
        )


def test_map_domain_broker_http_miss_dual_run_returns_miss() -> None:
    out = map_domain_broker_http_miss(
        RuntimeError("broker down"),
        feature="memory_search",
        enabled=lambda: True,
        only=lambda: False,
        only_code="broker_memory_only",
    )
    assert out["via"] == "broker_miss"
    assert out["status"] == "degraded"
    assert out["feature"] == "memory_search"
    assert "broker down" in out["error"]


def test_map_domain_broker_http_miss_broker_only_raises_503() -> None:
    with pytest.raises(HTTPException) as exc_info:
        map_domain_broker_http_miss(
            RuntimeError("broker down"),
            feature="memory_search",
            enabled=lambda: True,
            only=lambda: True,
            only_code="broker_memory_only",
            only_msg="memory broker-only",
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "code": "broker_memory_only",
        "message": "memory broker-only",
    }


def test_map_domain_broker_http_miss_merges_defaults() -> None:
    out = map_domain_broker_http_miss(
        "chat miss",
        feature="compute_chat",
        only=lambda: False,
        only_code="broker_compute_only",
        defaults={"node": None},
    )
    assert out["node"] is None
    assert out["feature"] == "compute_chat"


def test_normalize_domain_tool_result_parity() -> None:
    assert normalize_domain_tool_result({"ok": True}) == {"ok": True}
    assert normalize_domain_tool_result("text") == {"result": "text"}
    assert normalize_tool_result("text") == {"result": "text"}

from __future__ import annotations

from orchestrator.integrator_live_context import (
    integration_adapter_http_probe_from_rows,
    integrator_live_context_from_rows,
)


def test_integration_adapter_http_probe_from_rows_empty() -> None:
    assert integration_adapter_http_probe_from_rows([]) is None


def test_integration_adapter_http_probe_from_rows_latest() -> None:
    rows = [
        {
            "metadata": {
                "integration_adapter_writer": {
                    "http_probe": {"reachable": False, "attempts": 3},
                },
            },
        },
        {
            "metadata": {
                "integration_adapter_writer": {
                    "http_probe": {
                        "reachable": True,
                        "status_code": 200,
                        "ok": True,
                        "content_type": "text/plain",
                        "body_preview": "ok",
                        "attempts": 1,
                    },
                },
            },
        },
    ]
    probe = integration_adapter_http_probe_from_rows(rows)
    assert probe is not None
    assert probe["reachable"] is True
    assert probe["status_code"] == 200
    assert probe["body_preview"] == "ok"


def test_integrator_live_context_from_rows() -> None:
    rows = [
        {
            "metadata": {
                "integration_adapter_writer": {
                    "target_adapter_kind": "api_bridge",
                    "target_integration_status": "integrated",
                    "target_connected": True,
                    "http_probe": {
                        "reachable": True,
                        "status_code": 503,
                        "ok": False,
                        "content_type": "application/json",
                        "body_preview": '{"status":"degraded"}',
                        "attempts": 1,
                    },
                },
            },
        },
    ]
    ctx = integrator_live_context_from_rows(rows)
    assert ctx["target_adapter_kind"] == "api_bridge"
    assert ctx["adapter_integration_status"] == "integrated"
    assert ctx["target_connected"] is True
    assert ctx["http_probe"]["status_code"] == 503

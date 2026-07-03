from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from orchestrator.put_e2e_runner import run_put_e2e_flow


def test_run_put_e2e_pass_attaches_live_trace_when_playwright_ready(tmp_path: Path) -> None:
    trace_path = tmp_path / ".nimbusware" / "put_e2e" / "todo_api" / "trace.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_bytes(b"trace")
    with (
        patch(
            "orchestrator.put_e2e_runner._playwright_module_ready",
            return_value=(True, "ok"),
        ),
        patch(
            "orchestrator.put_e2e_browser.capture_failure_browser_trace",
            return_value={
                "trace_mode": "live",
                "trace_path": str(trace_path),
                "trace_backend": "local",
                "findings": [{"kind": "console", "message": "[log] ok", "severity": "info"}],
            },
        ),
        patch(
            "orchestrator.put_e2e_runner._run_http_step",
            return_value=True,
        ),
    ):
        result = run_put_e2e_flow(
            "http://127.0.0.1:8080",
            "todo_api",
            workspace=tmp_path,
            timeout_seconds=5.0,
        )
    assert result.verdict == "PASS"
    trace = (result.capture or {}).get("trace") or {}
    assert trace.get("trace_mode") == "live"

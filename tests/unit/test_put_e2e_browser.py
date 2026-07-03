from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch

from orchestrator.factory.e2e_evidence import write_put_e2e_failure_evidence
from orchestrator.factory.runner import PutE2EResult, run_put_e2e_flow


def test_write_evidence_includes_trace_zip_when_live(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.zip"
    trace_path.write_bytes(b"trace-bytes")
    result = PutE2EResult(
        verdict="FAIL",
        flow_id="crm",
        base_url="http://127.0.0.1:8080",
        detail="failed",
        capture={"trace": {"trace_mode": "live", "trace_path": str(trace_path)}},
    )
    refs = write_put_e2e_failure_evidence(tmp_path, result)
    with zipfile.ZipFile(refs["evidence_zip"]) as archive:
        assert "trace.zip" in archive.namelist()
    assert refs["trace_mode"] == "live"


def test_run_put_e2e_flow_attaches_live_trace_metadata(tmp_path: Path) -> None:
    trace_path = tmp_path / ".nimbusware" / "put_e2e" / "crm" / "trace.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_bytes(b"trace")
    with patch(
        "orchestrator.factory.browser.capture_failure_browser_trace",
        return_value={
            "trace_mode": "live",
            "trace_path": str(trace_path),
            "trace_backend": "local",
            "findings": [
                {"kind": "console", "message": "[error] boom", "severity": "operational"},
                {"kind": "network", "message": "HTTP 500 /api", "severity": "operational"},
            ],
        },
    ):
        result = run_put_e2e_flow(
            "http://127.0.0.1:9",
            "crm",
            workspace=tmp_path,
            timeout_seconds=1.0,
        )
    assert result.verdict == "FAIL"
    trace = (result.capture or {}).get("trace") or {}
    assert trace.get("trace_mode") == "live"
    evidence = (result.capture or {}).get("evidence") or {}
    assert evidence.get("trace_mode") == "live"
    assert any(row.get("kind") == "console" for row in (result.capture or {}).get("console") or [])
    assert any(row.get("kind") == "network" for row in (result.capture or {}).get("network") or [])

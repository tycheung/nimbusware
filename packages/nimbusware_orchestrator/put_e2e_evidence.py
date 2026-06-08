from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.put_e2e_runner import PutE2EResult


def put_e2e_evidence_dir(workspace: Path, flow_id: str) -> Path:
    safe = flow_id.replace("/", "_") or "flow"
    return workspace.resolve() / ".nimbusware" / "put_e2e" / safe


def write_put_e2e_failure_evidence(
    workspace: Path,
    result: PutE2EResult,
) -> dict[str, Any]:
    evidence_dir = put_e2e_evidence_dir(workspace, result.flow_id)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    zip_path = evidence_dir / "evidence.zip"
    summary = result.to_dict()
    trace_stub = {
        "mode": "http_flow",
        "flow_id": result.flow_id,
        "base_url": result.base_url,
        "detail": result.detail,
        "playwright_trace": "stub — HTTP-only PUT E2E runner (no browser session)",
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.json", json.dumps(summary, indent=2))
        archive.writestr("trace_stub.json", json.dumps(trace_stub, indent=2))
        if result.capture:
            archive.writestr("capture.json", json.dumps(result.capture, indent=2))
    return {
        "evidence_dir": str(evidence_dir),
        "evidence_zip": str(zip_path),
        "trace_stub": trace_stub,
    }

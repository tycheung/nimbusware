from __future__ import annotations

from pathlib import Path
import zipfile

from nimbusware_orchestrator.put_e2e_evidence import write_put_e2e_failure_evidence
from nimbusware_orchestrator.put_e2e_runner import PutE2EFinding, PutE2EResult


def test_write_put_e2e_failure_evidence_creates_zip(tmp_path: Path) -> None:
    result = PutE2EResult(
        verdict="FAIL",
        flow_id="crm",
        base_url="http://127.0.0.1:8080",
        detail="step failed",
        exercised_paths={"/", "/health"},
        findings=[PutE2EFinding(kind="step_fail", message="boom", surface_path="/health")],
        capture={"network": []},
    )
    refs = write_put_e2e_failure_evidence(tmp_path, result)
    zip_path = Path(refs["evidence_zip"])
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert "summary.json" in names
    assert "trace_stub.json" in names
    assert "capture.json" in names


def test_run_put_e2e_flow_writes_evidence_on_failure(tmp_path: Path) -> None:
    from nimbusware_orchestrator.put_e2e_runner import run_put_e2e_flow

    result = run_put_e2e_flow(
        "http://127.0.0.1:9",
        "crm",
        workspace=tmp_path,
        timeout_seconds=1.0,
    )
    assert result.verdict == "FAIL"
    evidence = (result.capture or {}).get("evidence") or {}
    assert Path(str(evidence.get("evidence_zip", ""))).is_file()

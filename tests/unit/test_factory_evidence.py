from __future__ import annotations

import io
import zipfile
from pathlib import Path

from nimbusware_orchestrator.factory_evidence import (
    build_factory_evidence_bundle,
    export_factory_evidence_zip,
)

REPO = Path(__file__).resolve().parents[2]


def test_factory_evidence_bundle_from_stage_events() -> None:
    events = [
        {
            "event_type": "stage.passed",
            "payload": {"stage_name": "factory.cadence"},
            "metadata": {
                "factory": {"tier": "T2", "ism_coverage_pct": 80.0, "put_e2e_passed": True},
                "put_e2e": {
                    "verdict": "PASS",
                    "flow_id": "crm",
                    "base_url": "http://127.0.0.1:8080",
                    "capture": {"network": []},
                    "exercised_paths": ["/", "/health"],
                    "findings": [],
                },
            },
        },
        {
            "event_type": "stage.passed",
            "payload": {"stage_name": "factory.complete"},
            "metadata": {
                "factory": {"tier": "T2", "factory_complete": True, "put_e2e_passed": True},
            },
        },
    ]
    bundle = build_factory_evidence_bundle(events)
    assert bundle["factory_complete"] is True
    assert bundle["factory_status"]["tier"] == "T2"
    assert bundle["put_e2e"]["flow_id"] == "crm"
    assert len(bundle["factory_stages"]) == 2


def test_factory_evidence_reads_put_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / ".nimbusware" / "put_artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "manifest.json").write_text('{"reason":"stop"}', encoding="utf-8")
    bundle = build_factory_evidence_bundle([], workspace=tmp_path)
    assert bundle["put_artifacts"]["manifest"]["reason"] == "stop"


def test_export_factory_evidence_zip_contains_bundle(tmp_path: Path) -> None:
    events = [
        {
            "event_type": "stage.passed",
            "payload": {"stage_name": "factory.cadence"},
            "metadata": {
                "put_e2e": {"verdict": "PASS", "flow_id": "crm", "capture": {}},
                "factory": {"tier": "T2", "put_e2e_passed": True},
            },
        },
    ]
    payload = export_factory_evidence_zip(events, workspace=tmp_path)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert "factory_evidence.json" in archive.namelist()

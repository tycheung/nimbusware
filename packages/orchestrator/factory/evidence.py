from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from orchestrator.factory.cadence import (
    FACTORY_CADENCE_STAGE,
    FACTORY_COMPLETE_STAGE,
)
from orchestrator.factory.evidence_html import render_factory_evidence_html
from projections.builders.factory_status import factory_status_from_events


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("metadata")
    return dict(meta) if isinstance(meta, dict) else {}


def _latest_put_e2e(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in events:
        block = _metadata(row).get("put_e2e")
        if isinstance(block, dict):
            latest = block
    return latest


def _factory_stages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in events:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage_name") or "")
        if stage not in {FACTORY_CADENCE_STAGE, FACTORY_COMPLETE_STAGE}:
            continue
        if row.get("event_type") not in {EventType.STAGE_PASSED.value, "stage.passed"}:
            continue
        latest[stage] = {
            "stage_name": stage,
            "occurred_at": row.get("occurred_at"),
            "metadata": _metadata(row),
        }
    return list(latest.values())


def _read_put_artifacts(workspace: Path | None) -> dict[str, Any]:
    if workspace is None or not workspace.is_dir():
        return {}
    artifacts_dir = workspace / ".nimbusware" / "put_artifacts"
    if not artifacts_dir.is_dir():
        return {}
    manifest_path = artifacts_dir / "manifest.json"
    payload: dict[str, Any] = {"artifacts_dir": str(artifacts_dir)}
    if manifest_path.is_file():
        try:
            payload["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload["manifest"] = None
        payload["manifest_path"] = str(manifest_path)
    return payload


def build_factory_evidence_bundle(
    events: list[dict[str, Any]],
    *,
    workspace: Path | None = None,
) -> dict[str, Any]:
    factory_status = factory_status_from_events(events)
    put_e2e = _latest_put_e2e(events)
    stages = _factory_stages(events)
    complete = any(s.get("stage_name") == FACTORY_COMPLETE_STAGE for s in stages)
    put_e2e_map = mapping_or_empty(put_e2e)
    capture = mapping_or_empty(put_e2e_map.get("capture"))
    ism_diff = None
    for stage in reversed(stages):
        meta = mapping_or_empty(stage.get("metadata"))
        ism_raw = meta.get("ism_diff")
        if isinstance(ism_raw, dict):
            ism_diff = ism_raw
            break
    bundle: dict[str, Any] = {
        "factory_complete": complete,
        "factory_status": factory_status,
        "put_e2e": put_e2e,
        "ism_diff": ism_diff,
        "factory_stages": stages,
        "put_artifacts": _read_put_artifacts(workspace),
        "evidence": {
            "capture": capture,
            "exercised_paths": put_e2e_map.get("exercised_paths") or [],
            "findings": put_e2e_map.get("findings") or [],
        },
    }
    bundle["scorecard_rows"] = factory_evidence_scorecard_rows(bundle)
    return bundle


def factory_evidence_scorecard_rows(bundle: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    fs = mapping_or_empty(bundle.get("factory_status"))
    if fs:
        tier = str(fs.get("tier") or "—")
        cov = fs.get("ism_coverage_pct")
        cov_s = f"{float(cov):.0f}%" if isinstance(cov, (int, float)) else "—"
        put_ok = fs.get("put_e2e_passed")
        put_s = "pass" if put_ok is True else "fail" if put_ok is False else "—"
        rows.append({"dimension": "Factory tier", "value": tier})
        rows.append({"dimension": "ISM coverage", "value": cov_s})
        rows.append({"dimension": "PUT E2E", "value": put_s})
    put_e2e = mapping_or_empty(bundle.get("put_e2e"))
    verdict = str(put_e2e.get("verdict") or "").upper()
    if verdict:
        rows.append({"dimension": "PUT verdict", "value": verdict})
    complete = bundle.get("factory_complete")
    rows.append(
        {
            "dimension": "Factory complete",
            "value": "yes" if complete else "no",
        },
    )
    evidence_block = mapping_or_empty(bundle.get("evidence"))
    findings = evidence_block.get("findings")
    if isinstance(findings, list) and findings:
        rows.append({"dimension": "Open findings", "value": str(len(findings))})
    ism_diff = mapping_or_empty(bundle.get("ism_diff"))
    uncovered = ism_diff.get("uncovered_surfaces")
    if isinstance(uncovered, list) and uncovered:
        rows.append({"dimension": "Uncovered ISM surfaces", "value": str(len(uncovered))})
    return rows


def export_factory_evidence_zip(
    events: list[dict[str, Any]],
    *,
    workspace: Path | None = None,
    run_id: str | None = None,
) -> bytes:
    bundle = build_factory_evidence_bundle(events, workspace=workspace)
    rid = (run_id or str(events[0].get("run_id") or "") if events else "").strip()
    if rid:
        bundle["run_id"] = rid
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("factory_evidence.json", json.dumps(bundle, indent=2))
        archive.writestr("scorecard.html", render_factory_evidence_html(bundle))
        put_artifacts = mapping_or_empty(bundle.get("put_artifacts"))
        manifest_path = put_artifacts.get("manifest_path")
        if manifest_path and Path(str(manifest_path)).is_file():
            archive.write(str(manifest_path), arcname="put_artifacts/manifest.json")
        put_e2e = mapping_or_empty(bundle.get("put_e2e"))
        capture = mapping_or_empty(put_e2e.get("capture"))
        evidence = mapping_or_empty(capture.get("evidence"))
        zip_path = evidence.get("evidence_zip")
        if zip_path and Path(str(zip_path)).is_file():
            archive.write(str(zip_path), arcname="put_e2e/evidence.zip")
    payload = buffer.getvalue()
    if rid:
        from orchestrator.factory.evidence_object_store import (
            put_factory_evidence_object,
        )

        put_factory_evidence_object(run_id=rid, payload=payload)
    return payload

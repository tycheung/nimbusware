"""Factory completion evidence bundle from run events and workspace artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_core.models import EventType
from nimbusware_orchestrator.factory_cadence import (
    FACTORY_COMPLETE_STAGE,
    FACTORY_CADENCE_STAGE,
)
from nimbusware_projections.builders.factory_status import factory_status_from_events


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
    capture = put_e2e.get("capture") if isinstance(put_e2e, dict) else None
    return {
        "factory_complete": complete,
        "factory_status": factory_status,
        "put_e2e": put_e2e,
        "factory_stages": stages,
        "put_artifacts": _read_put_artifacts(workspace),
        "evidence": {
            "capture": capture if isinstance(capture, dict) else {},
            "exercised_paths": put_e2e.get("exercised_paths") if isinstance(put_e2e, dict) else [],
            "findings": put_e2e.get("findings") if isinstance(put_e2e, dict) else [],
        },
    }

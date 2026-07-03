from __future__ import annotations

from typing import Any

from maker.api_client import get_json


def _summaries_from_list_payload(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    run_ids = payload.get("run_ids")
    if not isinstance(run_ids, list):
        return [], {}
    summaries = payload.get("summaries")
    if not isinstance(summaries, dict):
        summaries = {}
    return [str(x) for x in run_ids], summaries


def latest_run_id_for_project(project_id: str, *, limit: int = 50) -> str | None:
    runs = list_runs_for_project(project_id, limit=limit)
    return runs[0]["run_id"] if runs else None


def list_runs_for_project(project_id: str, *, limit: int = 50) -> list[dict[str, str]]:
    payload = get_json(f"/runs?limit={limit}&include_summary=1")
    run_ids, summaries = _summaries_from_list_payload(payload)
    target = str(project_id).strip()
    out: list[dict[str, str]] = []
    for run_id in run_ids:
        summary = summaries.get(str(run_id))
        if not isinstance(summary, dict):
            continue
        meta = summary.get("run_created_metadata")
        if not isinstance(meta, dict):
            continue
        project = meta.get("project")
        if not isinstance(project, dict):
            continue
        pid = str(project.get("id") or project.get("project_id") or "").strip()
        if pid != target:
            continue
        status = str(summary.get("status") or "unknown")
        out.append({"run_id": str(run_id), "status": status})
    return out

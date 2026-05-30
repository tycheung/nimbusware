from __future__ import annotations

from nimbusware_maker.api_client import get_json


def latest_run_id_for_project(project_id: str, *, limit: int = 50) -> str | None:
    payload = get_json(f"/runs?limit={limit}&include_summary=1")
    summaries = payload.get("summaries")
    if not isinstance(summaries, dict):
        summaries = {}
    run_ids = payload.get("run_ids")
    if not isinstance(run_ids, list):
        return None
    target = str(project_id).strip()
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
        if pid == target:
            return str(run_id)
    return None

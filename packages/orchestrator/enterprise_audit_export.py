from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def audit_redaction(payload: dict[str, Any]) -> dict[str, Any]:
    from config.tenant_policy_store import audit_redaction as _redact

    return _redact(payload)


def audit_retention_days() -> int:
    from env.settings_resolve import resolve_int

    return max(1, min(3650, resolve_int("NIMBUSWARE_AUDIT_RETENTION_DAYS", default=90)))


def build_enterprise_audit_bundle_bytes(
    *,
    iam_store: Any,
    event_store: Any,
    repo_root: Path | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> bytes:
    if until is None:
        until = datetime.now(timezone.utc)
    if since is None:
        since = until - timedelta(days=audit_retention_days())

    iam_rows = []
    if hasattr(iam_store, "list_iam_actions"):
        iam_rows = [r.to_dict() for r in iam_store.list_iam_actions(since=since, until=until)]

    events: list[dict[str, Any]] = []
    if hasattr(event_store, "list_all_event_rows"):
        for row in event_store.list_all_event_rows():
            occurred = row.get("occurred_at")
            if isinstance(occurred, datetime):
                if occurred < since or occurred > until:
                    continue
            events.append(
                audit_redaction(
                    {
                        "store_seq": row.get("store_seq"),
                        "run_id": str(row.get("run_id", "")),
                        "event_type": row.get("event_type"),
                        "occurred_at": str(occurred),
                        "metadata": row.get("metadata")
                        if isinstance(row.get("metadata"), dict)
                        else {},
                        "payload": row.get("payload")
                        if isinstance(row.get("payload"), dict)
                        else {},
                    },
                ),
            )

    policy_snapshots: list[dict[str, Any]] = []
    slice_commits: list[dict[str, Any]] = []
    learnings_rows: list[dict[str, Any]] = []
    for row in events:
        raw_meta = row.get("metadata")
        meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
        raw_payload = row.get("payload")
        payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
        snap = meta.get("policy_snapshot") or payload.get("policy_snapshot")
        if snap:
            policy_snapshots.append(
                audit_redaction(
                    {
                        "run_id": row.get("run_id"),
                        "occurred_at": row.get("occurred_at"),
                        "policy_snapshot": snap,
                    },
                ),
            )
        stage = str(payload.get("stage_name") or "")
        if stage == "slice.git_commit":
            slice_commits.append(
                audit_redaction(
                    {
                        "run_id": row.get("run_id"),
                        "occurred_at": row.get("occurred_at"),
                        **meta,
                    },
                ),
            )

    research_rows: list[dict[str, Any]] = []
    egress_rows: list[dict[str, Any]] = []
    if repo_root is not None:
        from research.enterprise_index import (
            export_egress_audit_rows,
            list_enterprise_research_index,
        )

        research_rows = list_enterprise_research_index(repo_root)
        egress_rows = export_egress_audit_rows(repo_root)
        from orchestrator.learnings_catalog import list_workspace_learnings

        workspace_paths: set[str] = set()
        for row in events:
            raw_ws_meta = row.get("metadata")
            ws_meta: dict[str, Any] = raw_ws_meta if isinstance(raw_ws_meta, dict) else {}
            raw_project = ws_meta.get("project")
            project: dict[str, Any] = raw_project if isinstance(raw_project, dict) else {}
            ws = project.get("workspace_path")
            if isinstance(ws, str) and ws.strip():
                workspace_paths.add(ws.strip())
        for ws_str in sorted(workspace_paths):
            ws = Path(ws_str)
            if not ws.is_dir():
                continue
            for item in list_workspace_learnings(ws, limit=20):
                learnings_rows.append(audit_redaction({**item, "workspace": ws_str}))

    manifest = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "retention_days": audit_retention_days(),
        "iam_action_count": len(iam_rows),
        "event_row_count": len(events),
        "research_index_row_count": len(research_rows),
        "egress_audit_row_count": len(egress_rows),
        "policy_snapshot_count": len(policy_snapshots),
        "slice_commit_count": len(slice_commits),
        "learnings_index_row_count": len(learnings_rows),
    }
    entries: list[tuple[str, str]] = [
        ("manifest.json", json.dumps(manifest, indent=2)),
        ("iam_actions.jsonl", "\n".join(json.dumps(r) for r in iam_rows)),
        ("events.jsonl", "\n".join(json.dumps(e) for e in events)),
    ]
    if policy_snapshots:
        entries.append(
            ("policy_snapshot.json", json.dumps(policy_snapshots, indent=2)),
        )
    if slice_commits:
        entries.append(
            ("slice_commits.jsonl", "\n".join(json.dumps(r) for r in slice_commits)),
        )
    if learnings_rows:
        entries.append(
            ("learnings_index.jsonl", "\n".join(json.dumps(r) for r in learnings_rows)),
        )
    if research_rows:
        entries.append(
            ("research_index.jsonl", "\n".join(json.dumps(r) for r in research_rows)),
        )
    if egress_rows:
        entries.append(
            ("egress_audit.jsonl", "\n".join(json.dumps(r) for r in egress_rows)),
        )
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, file_body in entries:
            data = file_body.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()

from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime, timedelta, timezone
from typing import Any


def audit_retention_days() -> int:
    from nimbusware_env.settings_resolve import resolve_int

    return max(1, min(3650, resolve_int("NIMBUSWARE_AUDIT_RETENTION_DAYS", default=90)))


def build_enterprise_audit_bundle_bytes(
    *,
    iam_store: Any,
    event_store: Any,
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
                {
                    "store_seq": row.get("store_seq"),
                    "run_id": str(row.get("run_id", "")),
                    "event_type": row.get("event_type"),
                    "occurred_at": str(occurred),
                },
            )

    manifest = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "retention_days": audit_retention_days(),
        "iam_action_count": len(iam_rows),
        "event_row_count": len(events),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, payload in (
            ("manifest.json", json.dumps(manifest, indent=2)),
            ("iam_actions.jsonl", "\n".join(json.dumps(r) for r in iam_rows)),
            ("events.jsonl", "\n".join(json.dumps(e) for e in events)),
        ):
            data = payload.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()

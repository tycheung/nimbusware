"""Compare frozen ``policy_snapshot`` metadata on two runs."""

from __future__ import annotations

from typing import Any


def policy_snapshot_from_run_created_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    snap = meta.get("policy_snapshot")
    return dict(snap) if isinstance(snap, dict) else {}


def diff_policy_snapshots(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(a.keys()) | set(b.keys()))
    changed: list[dict[str, Any]] = []
    for key in keys:
        va, vb = a.get(key), b.get(key)
        if va != vb:
            changed.append({"key": key, "run_a": va, "run_b": vb})
    return {
        "keys_compared": len(keys),
        "changed_count": len(changed),
        "changed": changed,
        "identical": len(changed) == 0,
    }

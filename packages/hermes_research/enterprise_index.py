"""Tenant-scoped research index + egress audit export hook."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID


def enterprise_research_enabled() -> bool:
    return os.environ.get("NIMBUSWARE_EDITION", "").strip().lower() == "enterprise"


def tenant_namespace() -> str:
    return os.environ.get("NIMBUSWARE_TENANT_ID", "default").strip() or "default"


def append_enterprise_research_index(
    repo_root: Path,
    *,
    run_id: UUID,
    pattern_id: str,
    domain_tag: str,
) -> dict[str, Any] | None:
    if not enterprise_research_enabled():
        return None
    ns = tenant_namespace()
    rel = Path(".hermes") / "enterprise" / ns / "research_index.jsonl"
    abs_path = repo_root / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "run_id": str(run_id),
        "pattern_id": pattern_id,
        "domain_tag": domain_tag,
        "tenant_id": ns,
    }
    with abs_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return {"enterprise_index_path": str(rel).replace("\\", "/"), "tenant_id": ns}


def export_egress_audit_rows(repo_root: Path) -> list[dict[str, Any]]:
    if not enterprise_research_enabled():
        return []
    ns = tenant_namespace()
    rel = Path(".hermes") / "enterprise" / ns / "egress_audit.jsonl"
    path = repo_root / rel
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def list_enterprise_research_index(repo_root: Path, *, limit: int = 500) -> list[dict[str, Any]]:
    if not enterprise_research_enabled():
        return []
    ns = tenant_namespace()
    rel = Path(".hermes") / "enterprise" / ns / "research_index.jsonl"
    path = repo_root / rel
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(rows) >= limit:
            break
    return rows

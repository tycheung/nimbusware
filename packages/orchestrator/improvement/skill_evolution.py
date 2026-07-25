"""L2 skill library evolution — draft / probation / promoted / shelved."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID

from orchestrator.improvement.evolution_ledger import (
    EvolutionLayer,
    EvolutionPhase,
    emit_evolution_event,
)
from orchestrator.merge import load_yaml


def _skills_dir(repo_root: Path) -> Path:
    return repo_root.resolve() / "configs" / "skills"


def _workspace_skills_dir(workspace: Path) -> Path:
    path = workspace.resolve() / ".nimbusware" / "evolution" / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def propose_skill_from_fingerprint(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    fingerprint: str,
    excerpt: str = "",
) -> dict[str, Any] | None:
    fp = fingerprint.strip()
    if not fp:
        return None
    skill_id = f"evolved-{fp[:12]}"
    artifact_id = f"skill-{skill_id}"
    body = (
        f"# Evolved skill `{skill_id}`\n\n"
        f"Fingerprint: `{fp}`\n\n"
        f"Derived from repeated failure:\n\n```\n{excerpt[:1500]}\n```\n"
    )
    body_path = _workspace_skills_dir(workspace) / f"{skill_id}.md"
    body_path.write_text(body, encoding="utf-8")
    index_path = _workspace_skills_dir(workspace) / "index.yaml"
    entry = {
        "id": skill_id,
        "name": f"Evolved {fp[:8]}",
        "description": f"Auto-drafted skill for fingerprint {fp[:12]}",
        "path": f"{skill_id}.md",
        "status": "draft",
        "fingerprint": fp,
        "tags": ["evolved"],
        "surfaces": [],
        "parent_id": None,
        "success_count": 0,
        "use_count": 0,
    }
    _upsert_workspace_skill_index(index_path, entry)
    emit_evolution_event(
        store,
        run_id,
        phase=EvolutionPhase.PROPOSED,
        layer=EvolutionLayer.SKILL,
        artifact_id=artifact_id,
        detail={"skill_id": skill_id, "path": str(body_path), "status": "draft"},
    )
    return entry


def record_skill_outcome(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    skill_ids: list[str],
    gate_passed: bool,
    has_p0: bool = False,
) -> None:
    index_path = _workspace_skills_dir(workspace) / "index.yaml"
    for skill_id in skill_ids:
        entry = _load_skill_entry(index_path, skill_id)
        if entry is None:
            continue
        entry["use_count"] = int(entry.get("use_count") or 0) + 1
        if gate_passed and not has_p0:
            entry["success_count"] = int(entry.get("success_count") or 0) + 1
        status = str(entry.get("status") or "draft")
        if status == "draft" and int(entry.get("use_count") or 0) >= 1:
            entry["status"] = "probation"
        if (
            str(entry.get("status")) == "probation"
            and int(entry.get("success_count") or 0) >= 2
            and not has_p0
        ):
            entry["status"] = "promoted"
            emit_evolution_event(
                store,
                run_id,
                phase=EvolutionPhase.PROMOTED,
                layer=EvolutionLayer.SKILL,
                artifact_id=f"skill-{skill_id}",
                detail={"skill_id": skill_id, "status": "promoted"},
            )
        elif has_p0 and status in ("draft", "probation"):
            entry["status"] = "shelved"
            emit_evolution_event(
                store,
                run_id,
                phase=EvolutionPhase.REJECTED,
                layer=EvolutionLayer.SKILL,
                artifact_id=f"skill-{skill_id}",
                detail={"skill_id": skill_id, "reason": "p0_security"},
            )
        else:
            emit_evolution_event(
                store,
                run_id,
                phase=EvolutionPhase.SCORED,
                layer=EvolutionLayer.SKILL,
                artifact_id=f"skill-{skill_id}",
                detail={
                    "skill_id": skill_id,
                    "gate_passed": gate_passed,
                    "status": entry.get("status"),
                    "success_count": entry.get("success_count"),
                    "use_count": entry.get("use_count"),
                },
            )
        _upsert_workspace_skill_index(index_path, entry)


def list_evolved_skill_briefs(workspace: Path) -> list[dict[str, Any]]:
    index_path = _workspace_skills_dir(workspace) / "index.yaml"
    if not index_path.is_file():
        return []
    raw = load_yaml(index_path)
    entries = raw.get("skills") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and str(e.get("status")) != "shelved"]


def _load_skill_entry(index_path: Path, skill_id: str) -> dict[str, Any] | None:
    if not index_path.is_file():
        return None
    raw = load_yaml(index_path)
    entries = raw.get("skills") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return None
    for item in entries:
        if isinstance(item, dict) and str(item.get("id") or "") == skill_id:
            return dict(item)
    return None


def _upsert_workspace_skill_index(index_path: Path, entry: dict[str, Any]) -> None:
    skills: list[dict[str, Any]] = []
    if index_path.is_file():
        raw = load_yaml(index_path)
        existing = raw.get("skills") if isinstance(raw, dict) else None
        if isinstance(existing, list):
            skills = [e for e in existing if isinstance(e, dict)]
    sid = str(entry.get("id") or "")
    skills = [e for e in skills if str(e.get("id") or "") != sid]
    skills.append(entry)
    lines = ["skills:"]
    for e in skills:
        lines.append(f"  - id: {e.get('id')}")
        lines.append(f"    name: {json_escape(str(e.get('name') or e.get('id')))}")
        lines.append(
            f"    description: {json_escape(str(e.get('description') or '')[:200])}",
        )
        lines.append(f"    path: {e.get('path')}")
        lines.append(f"    status: {e.get('status') or 'draft'}")
        if e.get("fingerprint"):
            lines.append(f"    fingerprint: {e.get('fingerprint')}")
        lines.append(f"    success_count: {int(e.get('success_count') or 0)}")
        lines.append(f"    use_count: {int(e.get('use_count') or 0)}")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def json_escape(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def skill_ids_from_metadata(metadata: dict[str, Any] | None) -> list[str]:
    if not isinstance(metadata, dict):
        return []
    raw = metadata.get("skill_ids_used")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    single = metadata.get("skill")
    if single is None:
        return []
    text = str(single).strip()
    if text.startswith("skill:"):
        text = text.split(":", 1)[1].strip()
    return [text] if text else []


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

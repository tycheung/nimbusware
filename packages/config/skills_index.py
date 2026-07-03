from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from env import find_repo_root
from orchestrator.merge import load_yaml


@dataclass(frozen=True)
class SkillBrief:
    id: str
    name: str
    description: str


def _skills_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "skills"


def list_skill_briefs(*, repo_root: Path | None = None) -> tuple[SkillBrief, ...]:
    index_path = _skills_dir(repo_root) / "index.yaml"
    if not index_path.is_file():
        return ()
    raw = load_yaml(index_path)
    entries = raw.get("skills") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return ()
    briefs: list[SkillBrief] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("id") or "").strip()
        if not skill_id:
            continue
        desc = str(item.get("description") or "")[:200]
        briefs.append(
            SkillBrief(
                id=skill_id,
                name=str(item.get("name") or skill_id),
                description=desc,
            ),
        )
    return tuple(briefs)


def load_skill(skill_id: str, *, repo_root: Path | None = None) -> str:
    index_path = _skills_dir(repo_root) / "index.yaml"
    if not index_path.is_file():
        msg = f"skills index missing: {index_path}"
        raise FileNotFoundError(msg)
    raw = load_yaml(index_path)
    entries = raw.get("skills") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        msg = "invalid skills index"
        raise FileNotFoundError(msg)
    rel_path: str | None = None
    for item in entries:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "").strip() == skill_id:
            rel_path = str(item.get("path") or "").strip()
            break
    if not rel_path:
        msg = f"unknown skill_id: {skill_id}"
        raise FileNotFoundError(msg)
    body_path = _skills_dir(repo_root) / rel_path
    if not body_path.is_file():
        msg = f"skill body missing: {body_path}"
        raise FileNotFoundError(msg)
    return body_path.read_text(encoding="utf-8")


def skill_briefs_prompt_block(*, repo_root: Path | None = None) -> str:
    briefs = list_skill_briefs(repo_root=repo_root)
    if not briefs:
        return ""
    lines = ["Available skills (request full text via stage metadata skill:<id>):"]
    for b in briefs:
        lines.append(f"- {b.id}: {b.description}")
    return "\n".join(lines)


def resolve_stage_skill(stage_metadata: dict[str, object] | None) -> str | None:
    if not isinstance(stage_metadata, dict):
        return None
    raw = stage_metadata.get("skill")
    if raw is None:
        return None
    text = str(raw).strip()
    if text.startswith("skill:"):
        return text.split(":", 1)[1].strip() or None
    return text or None

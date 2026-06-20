from __future__ import annotations

import hashlib
from pathlib import Path

_MAX_PATCH_BYTES = 400_000


def _is_safe_rel_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return bool(rel) and ".." not in parts


def workspace_file_digests(workspace: Path) -> dict[str, str]:
    ws = workspace.resolve()
    digests: dict[str, str] = {}
    for path in ws.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(ws).parts):
            continue
        rel = path.relative_to(ws).as_posix()
        digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def diff_workspace_files(
    before: dict[str, str],
    after: dict[str, str],
    workspace: Path,
    *,
    max_bytes: int = _MAX_PATCH_BYTES,
) -> dict[str, str]:
    changed: dict[str, str] = {}
    total = 0
    ws = workspace.resolve()
    for rel, digest in after.items():
        if not _is_safe_rel_path(rel) or before.get(rel) == digest:
            continue
        path = ws / rel
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if total + len(raw) > max_bytes:
            break
        try:
            changed[rel] = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        total += len(raw)
    return changed


def apply_workspace_files(workspace: Path, files: dict[str, str]) -> list[str]:
    ws = workspace.resolve()
    applied: list[str] = []
    for rel, content in files.items():
        if not _is_safe_rel_path(rel):
            continue
        target = ws / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        applied.append(rel)
    return applied

"""Apply LLM-proposed slice patches only within plan allowlist."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from nimbusware_orchestrator.micro_slice import SlicePlan


def _normalise_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def apply_slice_file_edits(
    workspace: Path,
    plan: SlicePlan,
    edits: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    """Write ``edits`` when ``path`` is in ``plan.target_paths``. Returns touched, errors."""
    allowed = {_normalise_rel(p) for p in plan.target_paths}
    touched: list[str] = []
    errors: list[str] = []

    for raw in edits:
        if not isinstance(raw, dict):
            continue
        rel = _normalise_rel(str(raw.get("path", "")))
        if not rel or rel not in allowed:
            errors.append(f"rejected path outside slice plan: {rel!r}")
            continue
        if ".." in rel.split("/"):
            errors.append(f"rejected unsafe path: {rel!r}")
            continue
        content = raw.get("content")
        if content is None:
            errors.append(f"missing content for {rel!r}")
            continue
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_name = tempfile.mkstemp(
                dir=str(target.parent),
                prefix=".slice_patch_",
                suffix=".tmp",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(str(content))
            os.replace(tmp_name, target)
            touched.append(rel)
        except OSError as exc:
            errors.append(f"write failed {rel!r}: {exc}")
    return touched, errors

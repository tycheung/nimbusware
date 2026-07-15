from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Any

from standards.fs_walk import iter_workspace_files
from standards.stream_results import CheckResult


def check_bare_except(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    globs = list(params.get("path_globs") or ["**/*.py"])
    hits: list[str] = []
    for path in iter_workspace_files(workspace, suffix=".py"):
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        if not any(fnmatch.fnmatch(rel, g) for g in globs):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                hits.append(f"{rel}:{node.lineno}")
    return CheckResult(
        check_id="err.no_bare_except",
        passed=not hits,
        verdict="hard_gate",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )

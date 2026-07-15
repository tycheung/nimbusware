from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from standards.fs_walk import iter_workspace_files
from standards.stream_results import CheckResult


def check_function_loc(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_loc = int(params.get("max_function_loc") or 60)
    hits: list[str] = []
    for path in iter_workspace_files(workspace, suffix=".py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end = getattr(node, "end_lineno", node.lineno)
            loc = end - node.lineno + 1
            if loc > max_loc:
                hits.append(f"{path.relative_to(workspace)}:{node.name} ({loc} lines)")
    passed = not hits
    return CheckResult(
        check_id="nasa.function_max_loc",
        passed=passed,
        verdict="hard_gate",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if passed else 1,
    )

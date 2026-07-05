from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def check_class_loc(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_loc = int(params.get("max_class_loc") or 200)
    hits: list[str] = []
    for path in workspace.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            end = getattr(node, "end_lineno", node.lineno)
            loc = end - node.lineno + 1
            if loc > max_loc:
                hits.append(f"{path.relative_to(workspace)}:{node.name} ({loc} lines)")
    passed = not hits
    return CheckResult(
        check_id="oop.class_max_loc",
        passed=passed,
        verdict="critique",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if passed else 1,
    )

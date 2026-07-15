from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from standards.fs_walk import iter_workspace_files
from standards.stream_results import CheckResult

_MUTATION = re.compile(r"\b(?:push|pop|splice|sort|reverse)\s*\(")


def check_no_array_mutation(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    hits: list[str] = []
    for path in iter_workspace_files(workspace):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _MUTATION.search(text):
            hits.append(str(path.relative_to(workspace)).replace("\\", "/"))
    passed = not hits
    return CheckResult(
        check_id="fp.no_array_mutation",
        passed=passed,
        verdict="warn",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if passed else 1,
    )

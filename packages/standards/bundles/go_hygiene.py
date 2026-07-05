from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult

_IGNORED_ERR = re.compile(r"^\s*_\s*=\s*(err|error)\b", re.MULTILINE)


def check_file_loc(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_loc = int(params.get("max_loc") or 400)
    hits: list[str] = []
    for path in workspace.rglob("*.go"):
        if path.name.endswith("_test.go"):
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_loc:
            hits.append(f"{path.relative_to(workspace)}: {len(lines)} lines")
    return CheckResult(
        check_id="go.file_max_loc",
        passed=not hits,
        verdict="critique",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )


def check_ignored_errors(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    hits: list[str] = []
    for path in workspace.rglob("*.go"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if ", _ :=" in text or ", _ =" in text or _IGNORED_ERR.search(text):
            hits.append(str(path.relative_to(workspace)))
    return CheckResult(
        check_id="go.no_ignored_errors",
        passed=not hits,
        verdict="hard_gate",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )


def check_errcheck(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    if not (workspace / "go.mod").is_file():
        return CheckResult(
            check_id="go.errcheck",
            passed=True,
            verdict="skip",
            detail="no go.mod",
            exit_code=0,
        )
    errcheck = shutil.which("errcheck")
    if errcheck is None:
        return CheckResult(
            check_id="go.errcheck",
            passed=True,
            verdict="warn",
            detail="errcheck not installed",
            exit_code=0,
        )
    proc = subprocess.run(
        [errcheck, "./..."],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    detail = ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
    return CheckResult(
        check_id="go.errcheck",
        passed=proc.returncode == 0,
        verdict="hard_gate",
        detail=detail or "ok",
        exit_code=proc.returncode,
    )

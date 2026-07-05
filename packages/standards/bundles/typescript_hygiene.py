from __future__ import annotations

import fnmatch
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult

_BARREL = re.compile(r"^\s*(export\s+)?(async\s+)?function\s+\w+", re.MULTILINE)
_CONFIG = re.compile(r"config|constants|env", re.IGNORECASE)


def check_config_loc(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_loc = int(params.get("max_loc") or 300)
    hits: list[str] = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        if not _CONFIG.search(rel):
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_loc:
            hits.append(f"{rel}: {len(lines)} lines")
    return CheckResult(
        check_id="ts.config_module_max_loc",
        passed=not hits,
        verdict="critique",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )


def check_barrel_exports(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_loc = int(params.get("max_non_export_loc") or 30)
    hits: list[str] = []
    for name in ("index.ts", "index.tsx", "index.js", "index.jsx"):
        for path in workspace.rglob(name):
            text = path.read_text(encoding="utf-8", errors="replace")
            fn_count = len(_BARREL.findall(text))
            if fn_count > 0 and fn_count * 8 > max_loc:
                hits.append(f"{path.relative_to(workspace)}: {fn_count} inline functions")
    return CheckResult(
        check_id="ts.barrel_exports_only",
        passed=not hits,
        verdict="critique",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )


def check_env_access(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    allow = list(params.get("allow_globs") or ["**/env.ts", "**/config/**"])
    hits: list[str] = []
    for path in workspace.rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        if any(fnmatch.fnmatch(rel, g) for g in allow):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "process.env" in text or "import.meta.env" in text:
            hits.append(rel)
    return CheckResult(
        check_id="ts.env_centralized",
        passed=not hits,
        verdict="warn",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )


def check_eslint(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    if not (workspace / "package.json").is_file():
        return CheckResult(
            check_id="ts.eslint",
            passed=True,
            verdict="skip",
            detail="no package.json",
            exit_code=0,
        )
    eslint = shutil.which("npx") or shutil.which("eslint")
    if eslint is None:
        return CheckResult(
            check_id="ts.eslint",
            passed=True,
            verdict="warn",
            detail="eslint not available",
            exit_code=0,
        )
    cmd = ["npx", "--yes", "eslint", ".", "--max-warnings", "0"]
    proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
    detail = ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
    return CheckResult(
        check_id="ts.eslint",
        passed=proc.returncode == 0,
        verdict="critique",
        detail=detail or "ok",
        exit_code=proc.returncode,
    )


def check_tsc(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    if not (workspace / "package.json").is_file():
        return CheckResult(
            check_id="ts.tsc",
            passed=True,
            verdict="skip",
            detail="no package.json",
            exit_code=0,
        )
    if not (workspace / "tsconfig.json").is_file():
        return CheckResult(
            check_id="ts.tsc",
            passed=True,
            verdict="skip",
            detail="no tsconfig.json",
            exit_code=0,
        )
    proc = subprocess.run(
        ["npx", "--yes", "tsc", "--noEmit"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    detail = ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
    return CheckResult(
        check_id="ts.tsc",
        passed=proc.returncode == 0,
        verdict="hard_gate",
        detail=detail or "ok",
        exit_code=proc.returncode,
    )

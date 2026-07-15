from __future__ import annotations

import ast
import fnmatch
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult

_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".tox",
        ".eggs",
    },
)


def _should_skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.startswith(".")


def _iter_files(workspace: Path, globs: list[str]) -> list[Path]:
    root = workspace.resolve()
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(str(root), topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        for name in filenames:
            path = Path(dirpath, name)
            try:
                rel = str(path.relative_to(root)).replace("\\", "/")
            except ValueError:
                continue
            if any(path.match(g) or fnmatch.fnmatch(rel, g) for g in globs):
                out.append(path)
    return sorted(out)


def check_config_module_loc(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_loc = int(params.get("max_loc") or 250)
    globs = list(params.get("path_globs") or ["**/settings.py", "**/config.py"])
    violations: list[str] = []
    for path in _iter_files(workspace, globs):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_loc:
            rel = path.relative_to(workspace)
            violations.append(f"{rel}: {len(lines)} lines (max {max_loc})")
    passed = not violations
    return CheckResult(
        check_id="py.config_module_max_loc",
        passed=passed,
        verdict="critique",
        detail="; ".join(violations[:20]) or "ok",
        exit_code=0 if passed else 1,
    )


def check_pydantic_v2(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    globs = list(params.get("path_globs") or ["**/*.py"])
    forbidden = (
        "class Config:",
        "@validator",
        "@root_validator",
        ".dict(",
        "parse_obj",
        "parse_raw",
    )
    hits: list[str] = []
    for path in _iter_files(workspace, globs):
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            if token in text:
                hits.append(f"{path.relative_to(workspace)}: {token}")
                break
    passed = not hits
    return CheckResult(
        check_id="py.pydantic_v2_only",
        passed=passed,
        verdict="hard_gate",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if passed else 1,
    )


def check_init_exports_only(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_non_import = int(params.get("max_non_import_loc") or 40)
    violations: list[str] = []
    for path in _iter_files(workspace, ["**/__init__.py"]):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        non_import = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue
            if isinstance(node, ast.Assign) and node.targets:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == "__all__":
                    continue
            non_import += getattr(node, "end_lineno", node.lineno) - node.lineno + 1
        if non_import > max_non_import:
            violations.append(f"{path.relative_to(workspace)}: {non_import} non-import lines")
    passed = not violations
    return CheckResult(
        check_id="py.package_init_exports_only",
        passed=passed,
        verdict="critique",
        detail="; ".join(violations[:20]) or "ok",
        exit_code=0 if passed else 1,
    )


def check_env_access_pattern(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    allow = list(params.get("allow_globs") or ["**/env.py", "**/settings.py"])
    hits: list[str] = []
    for path in _iter_files(workspace, ["**/*.py"]):
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        if any(fnmatch.fnmatch(rel, g) for g in allow):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "os.environ" in text or "os.getenv" in text:
            hits.append(rel)
    passed = not hits
    return CheckResult(
        check_id="py.env_no_raw_environ",
        passed=passed,
        verdict="warn",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if passed else 1,
    )


def check_orphan_modules(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    package_roots = list(params.get("package_roots") or ["src", "app", "packages"])
    orphans: list[str] = []
    for root_name in package_roots:
        root = workspace / root_name
        if not root.is_dir():
            continue
        for path in _iter_files(root, ["**/*.py"]):
            # _iter_files paths are relative to ``root`` matching; rebase to workspace.
            try:
                rel_to_ws = path.relative_to(workspace.resolve())
            except ValueError:
                continue
            if path.name == "__init__.py" or path.name.startswith("test_"):
                continue
            parent_init = path.parent / "__init__.py"
            if not parent_init.is_file() and path.parent != root:
                orphans.append(str(rel_to_ws).replace("\\", "/"))
    passed = not orphans
    return CheckResult(
        check_id="py.no_orphan_modules",
        passed=passed,
        verdict="critique",
        detail="; ".join(orphans[:20]) or "ok",
        exit_code=0 if passed else 1,
    )


def check_mypy_on_paths(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    globs = list(params.get("path_globs") or ["**/*.py"])
    targets: list[str] = []
    for path in _iter_files(workspace, globs):
        targets.append(str(path.relative_to(workspace)).replace("\\", "/"))
    if not targets:
        return CheckResult(
            check_id="py.mypy_scoped",
            passed=True,
            verdict="warn",
            detail="no python targets",
            exit_code=0,
        )
    cmd = [sys.executable, "-m", "mypy", *targets[:40]]
    proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
    detail = ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
    return CheckResult(
        check_id="py.mypy_scoped",
        passed=proc.returncode == 0,
        verdict="critique",
        detail=detail or "ok",
        exit_code=proc.returncode,
    )

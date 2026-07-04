from __future__ import annotations

import ast
import fnmatch
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def _iter_files(workspace: Path, globs: list[str]) -> list[Path]:
    out: list[Path] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        if any(path.match(g) for g in globs):
            out.append(path)
    return out


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
    for path in workspace.rglob("__init__.py"):
        if not path.is_file():
            continue
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
    for path in workspace.rglob("*.py"):
        if not path.is_file():
            continue
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

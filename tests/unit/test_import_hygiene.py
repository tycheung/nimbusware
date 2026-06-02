"""AST guard: star imports with F403 only in documented facade paths (fo502)."""

from __future__ import annotations

import ast
import fnmatch
from pathlib import Path

_PACKAGES_ROOT = Path(__file__).resolve().parents[2] / "packages"

# Relative to ``packages/<pkg>/`` — documented facade paths only.
_STAR_IMPORT_F403_ALLOWED: frozenset[str] = frozenset(
    {
        "models/events.py",
        "store.py",
        "llm/__init__.py",
        "llm/test_writer_critique.py",
        "llm/plan_stage.py",
        "llm/agent_evaluator.py",
        "llm_plan.py",
        "openapi.py",
        "scraper_artifacts.py",
        "routes/runs/__init__.py",
        "*_display.py",
        "*_explainer.py",
        "bundle_catalog.py",
        "integrator_workflow_preview.py",
        "pages/**/_shared*.py",
        "pages/config_tooling/workflows/**",
        "pages/config_tooling/bundles/**",
        "pages/run_detail/_imports*.py",
    },
)


def _packages_rel_posix(path: Path) -> str:
    rel = path.relative_to(_PACKAGES_ROOT)
    return rel.as_posix()


def _path_matches_pattern(within_pkg: str, pattern: str) -> bool:
    if fnmatch.fnmatch(within_pkg, pattern):
        return True
    basename = Path(within_pkg).name
    if fnmatch.fnmatch(basename, pattern):
        return True
    if "**" not in pattern:
        return False
    prefix, suffix = pattern.split("**", 1)
    prefix = prefix.rstrip("/")
    suffix = suffix.lstrip("/")
    if prefix and not within_pkg.startswith(prefix + "/") and within_pkg != prefix:
        return False
    rest = within_pkg[len(prefix) :].lstrip("/") if prefix else within_pkg
    return fnmatch.fnmatch(rest, suffix) or fnmatch.fnmatch(basename, suffix)


def _star_import_allowed(rel_posix: str) -> bool:
    """``rel_posix`` is ``<package>/...`` under ``packages/``."""
    parts = rel_posix.split("/", 1)
    if len(parts) != 2:
        return False
    within_pkg = parts[1]
    return any(_path_matches_pattern(within_pkg, pattern) for pattern in _STAR_IMPORT_F403_ALLOWED)


def _star_imports_with_f403(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if not any(alias.name == "*" for alias in node.names):
            continue
        line_no = node.lineno
        source_line = path.read_text(encoding="utf-8").splitlines()[line_no - 1]
        if "noqa: F403" in source_line or "noqa:F403" in source_line.replace(" ", ""):
            lines.append(line_no)
    return lines


def test_star_import_f403_only_in_documented_facade_paths() -> None:
    offenders: list[str] = []
    for path in sorted(_PACKAGES_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = _packages_rel_posix(path)
        star_lines = _star_imports_with_f403(path)
        if not star_lines:
            continue
        if _star_import_allowed(rel):
            continue
        offenders.append(f"{rel}: star import with F403 at lines {star_lines}")
    assert not offenders, "Star imports with F403 outside documented facades:\n" + "\n".join(
        offenders
    )

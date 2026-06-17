"""Regenerate root display/explainer facades from package __init__.py exports."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONSOLE = REPO / "packages" / "nimbusware_console"


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module or node.module == "__future__":
            continue
        for alias in node.names:
            if alias.name != "*":
                names.append(alias.asname or alias.name)
    return sorted(set(names))


def _facade_package_module(facade_path: Path) -> tuple[str, Path] | None:
    stem = facade_path.stem
    pkg_dir = CONSOLE / stem
    if pkg_dir.is_dir() and (pkg_dir / "__init__.py").is_file():
        return f"nimbusware_console.{stem}", pkg_dir / "__init__.py"
    alt = stem.removesuffix("_display").removesuffix("_explainer")
    alt_dir = CONSOLE / alt
    if alt_dir.is_dir() and (alt_dir / "__init__.py").is_file():
        return f"nimbusware_console.{alt}", alt_dir / "__init__.py"
    return None


def _discover_facades() -> list[Path]:
    paths: list[Path] = []
    for pattern in ("*_display.py", "*_explainer.py", "bundle_catalog.py", "integrator_workflow_preview.py"):
        paths.extend(CONSOLE.glob(pattern))
    return sorted(paths)


def sync_facade(facade_path: Path, *, dry_run: bool = False) -> bool:
    resolved = _facade_package_module(facade_path)
    if resolved is None:
        return False
    module, pkg_init = resolved
    names = _imported_names(pkg_init)
    if not names:
        return False
    body = f"from {module} import (\n    " + ",\n    ".join(names) + ",\n)\n"
    existing = facade_path.read_text(encoding="utf-8")
    if existing == body:
        return False
    if dry_run:
        print(f"would sync {facade_path.relative_to(REPO)} ({len(names)} names)")
    else:
        facade_path.write_text(body, encoding="utf-8")
        print(f"synced {facade_path.relative_to(REPO)} ({len(names)} names)")
    return True


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    changed = 0
    skipped: list[str] = []
    for path in _discover_facades():
        if sync_facade(path, dry_run=dry_run):
            changed += 1
        elif _facade_package_module(path) is None:
            skipped.append(path.name)
    if skipped:
        print(f"skipped (no package): {', '.join(skipped)}")
    print(f"{'would sync' if dry_run else 'synced'} {changed} facade(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

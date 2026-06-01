"""Convert `from module import *` lines to explicit symbol imports (Lane C).

Safe targets: display package __init__.py files and root *_display.py facades.
Do not run repo-wide `ruff check --fix`; use this script instead for re-exports.
"""

from __future__ import annotations

import ast
import importlib
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "packages"

STAR_LINE = re.compile(
    r"^from (?P<module>[a-zA-Z0-9_.]+) import \*  # noqa: F403\s*$"
)


def _module_path(module: str) -> Path | None:
    parts = module.split(".")
    if parts[0] not in {p.name for p in PACKAGES.iterdir() if p.is_dir()}:
        return None
    pkg_init = PACKAGES / parts[0] / Path(*parts[1:]) / "__init__.py"
    if pkg_init.is_file():
        return pkg_init
    rel = Path(*parts[1:]).with_suffix(".py")
    direct = PACKAGES / parts[0] / rel
    if direct.is_file():
        return direct
    return None


def _parse_all(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                value = node.value
                if isinstance(value, (ast.List, ast.Tuple)):
                    out: list[str] = []
                    for elt in value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            out.append(elt.value)
                    return out
    return None


def _defined_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    explicit_all = _parse_all(tree)
    if explicit_all is not None:
        return set(explicit_all)
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            names.add(elt.id)
    return names


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if node.module == "__future__":
            continue
        for alias in node.names:
            if alias.name != "*":
                names.append(alias.asname or alias.name)
    return sorted(set(names))


def _star_import_modules(text: str) -> list[str]:
    return [
        STAR_LINE.match(line.rstrip("\n")).group("module")
        for line in text.splitlines()
        if STAR_LINE.match(line.rstrip("\n"))
    ]


def _init_all(text: str) -> list[str] | None:
    tree = ast.parse(text)
    return _parse_all(tree)


def _names_for_module(module: str, *, allowed: set[str] | None) -> list[str]:
    path = _module_path(module)
    if path is None:
        raise FileNotFoundError(f"Cannot resolve module {module!r}")
    if path.name == "__init__.py":
        names = set(_imported_names(path))
        if not names:
            names = _defined_names(path)
    else:
        names = _defined_names(path)
    if allowed is not None:
        names &= allowed
    return sorted(names)


def explicitize_file(path: Path, *, dry_run: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    star_modules = _star_import_modules(text)
    if not star_modules:
        return False

    allowed = set(_init_all(text) or ())
    use_filter = bool(allowed) and not path.name == "__init__.py"
    new_blocks: list[str] = []
    for module in star_modules:
        names = _names_for_module(module, allowed=allowed if use_filter else None)
        if not names:
            raise RuntimeError(f"{path}: no public names resolved for {module!r}")
        joined = ",\n    ".join(names)
        new_blocks.append(f"from {module} import (\n    {joined},\n)")

    tail_lines = [line for line in text.splitlines(keepends=True) if not STAR_LINE.match(line.rstrip("\n"))]
    future_lines = [line for line in tail_lines if line.startswith("from __future__")]
    other_tail = [line for line in tail_lines if not line.startswith("from __future__")]
    body = "".join(future_lines)
    if body and not body.endswith("\n"):
        body += "\n"
    if future_lines and new_blocks:
        body += "\n"
    if new_blocks:
        seen: set[str] = set()
        deduped_blocks: list[str] = []
        for block in new_blocks:
            block_names = re.findall(r"^\s{4}(\w+),?\s*$", block, re.MULTILINE)
            unique: list[str] = []
            for n in block_names:
                if n not in seen:
                    seen.add(n)
                    unique.append(n)
            if not unique:
                continue
            mod_match = re.match(r"from ([\w.]+) import \(", block.split("\n", 1)[0])
            if not mod_match:
                deduped_blocks.append(block)
                continue
            joined = ",\n    ".join(unique)
            deduped_blocks.append(f"from {mod_match.group(1)} import (\n    {joined},\n)")
        new_blocks = deduped_blocks
    body += "\n".join(new_blocks)
    if new_blocks:
        body += "\n"
    body += "".join(other_tail)
    new_text = body
    if new_text == text:
        return False
    if dry_run:
        print(f"would update {path.relative_to(REPO)}")
    else:
        path.write_text(new_text, encoding="utf-8")
        print(f"updated {path.relative_to(REPO)}")
    return True


def _console_targets() -> list[Path]:
    console = PACKAGES / "nimbusware_console"
    targets: list[Path] = []
    thin_shim_paths = (
        "persona_catalog/summary.py",
        "integrator_gate/latest_delta.py",
        "integrator_preview/merge.py",
        "bundle_catalog/catalog_local/search.py",
        "bundle_catalog/faiss_status/drilldown.py",
    )
    for rel in thin_shim_paths:
        path = console / rel
        if path.is_file() and " import *  # noqa: F403" in path.read_text(encoding="utf-8"):
            targets.append(path)
    for path in console.rglob("__init__.py"):
        rel = path.relative_to(console).as_posix()
        if rel.startswith("pages/"):
            continue
        if " import *  # noqa: F403" in path.read_text(encoding="utf-8"):
            targets.append(path)
    for pattern in ("*_display.py", "*_explainer.py", "bundle_catalog.py", "integrator_workflow_preview.py"):
        for path in console.glob(pattern):
            if " import *  # noqa: F403" in path.read_text(encoding="utf-8"):
                targets.append(path)
    return sorted(set(targets))


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    paths = _console_targets()
    changed = 0
    for path in paths:
        if explicitize_file(path, dry_run=dry_run):
            changed += 1
    print(f"{'would change' if dry_run else 'changed'} {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

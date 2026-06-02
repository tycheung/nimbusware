"""Display/explainer root facades must match sibling package public exports."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

_CONSOLE = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"


def _facade_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        "*_display.py",
        "*_explainer.py",
        "bundle_catalog.py",
        "integrator_workflow_preview.py",
    ):
        paths.extend(_CONSOLE.glob(pattern))
    return sorted(paths)


def _package_module_name(facade_path: Path) -> str | None:
    stem = facade_path.stem
    if (_CONSOLE / stem).is_dir():
        return f"nimbusware_console.{stem}"
    alt = stem.removesuffix("_display").removesuffix("_explainer")
    if (_CONSOLE / alt).is_dir():
        return f"nimbusware_console.{alt}"
    return None


def _facade_import_names(facade_path: Path) -> tuple[str, set[str]]:
    tree = ast.parse(facade_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module == "__future__":
            continue
        names = {alias.name for alias in node.names if alias.name != "*"}
        if names:
            return node.module, names
    raise AssertionError(f"{facade_path.name}: no explicit import block")


def _imported_names_from_init(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module or node.module == "__future__":
            continue
        for alias in node.names:
            if alias.name != "*":
                names.append(alias.asname or alias.name)
    return sorted(set(names))


def test_display_facades_import_from_expected_package() -> None:
    mismatches: list[str] = []
    for facade in _facade_paths():
        expected = _package_module_name(facade)
        if expected is None:
            continue
        actual_mod, imported = _facade_import_names(facade)
        if actual_mod != expected:
            mismatches.append(f"{facade.name}: imports {actual_mod!r}, expected {expected!r}")
            continue
        pkg = importlib.import_module(expected)
        missing = sorted(name for name in imported if not hasattr(pkg, name))
        if missing:
            mismatches.append(
                f"{facade.name}: not exported by {expected}: "
                f"{missing[:8]}{'...' if len(missing) > 8 else ''}"
            )
    assert not mismatches, "\n".join(mismatches)


def test_display_facades_match_package_init_imports() -> None:
    stale: list[str] = []
    for facade in _facade_paths():
        expected = _package_module_name(facade)
        if expected is None:
            continue
        pkg_init = _CONSOLE / expected.removeprefix("nimbusware_console.") / "__init__.py"
        if not pkg_init.is_file():
            continue
        init_names = _imported_names_from_init(pkg_init)
        _, imported = _facade_import_names(facade)
        if sorted(imported) != init_names:
            stale.append(facade.name)
    assert not stale, "Re-run: poetry run python scripts/sync_display_facade.py\n" + "\n".join(
        stale
    )


def test_display_facades_have_explicit_imports() -> None:
    offenders: list[str] = []
    for facade in _facade_paths():
        text = facade.read_text(encoding="utf-8")
        if "import *  # noqa: F403" in text:
            offenders.append(facade.name)
    assert not offenders, "Star-import facades:\n" + "\n".join(offenders)

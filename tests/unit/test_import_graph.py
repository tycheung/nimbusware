"""Package import graph — no cycles among top-level packages."""

from __future__ import annotations
from nimbusware_env import find_repo_root

import importlib
import pkgutil
from pathlib import Path

import pytest

PACKAGE_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1]) / "packages"

TOP_LEVEL = sorted(
    p.name
    for p in PACKAGE_ROOT.iterdir()
    if p.is_dir() and (p / "__init__.py").exists()
)


@pytest.mark.parametrize("package", TOP_LEVEL)
def test_package_imports_without_cycle(package: str) -> None:
    mod = importlib.import_module(package)
    assert mod is not None


def test_extensions_imports_without_orchestrator_pipeline() -> None:
    """Extensions must not import orchestrator pipeline (cycle breaker)."""
    import hermes_extensions.catalog as catalog

    source = Path(catalog.__file__).read_text(encoding="utf-8")
    assert "hermes_orchestrator.pipeline" not in source
    assert "hermes_orchestrator.merge" not in source

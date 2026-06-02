from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"
_TARGETS = _REPO / "scripts" / "mypy_ci_targets.py"

_TRANCHE_D_MODULES = frozenset(
    {
        "nimbusware_api.read_models",
        "nimbusware_api.read_models.*",
        "nimbusware_api.facade",
        "nimbusware_api.deps",
        "nimbusware_api.routes.enterprise",
        "nimbusware_api.routes.enterprise.*",
        "nimbusware_api.routes.personas_helpers",
    },
)


def test_tranche_d_listed_in_mypy_strict_override() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    marker = "fo732 (Lane X2)"
    idx = text.find(marker)
    assert idx >= 0, "missing tranche D mypy override block"
    block = text[idx : idx + 700]
    assert "ignore_errors = false" in block
    for module in _TRANCHE_D_MODULES:
        assert module in block, f"missing strict mypy override entry for {module}"


def test_tranche_d_paths_in_ci_targets() -> None:
    text = _TARGETS.read_text(encoding="utf-8")
    assert "packages/nimbusware_api/read_models" in text
    assert "packages/nimbusware_console" in text
    assert "packages/nimbusware_maker" in text

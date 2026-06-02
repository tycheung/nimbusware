from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"

_TRANCHE_B_MODULES = frozenset(
    {
        "nimbusware_projections",
        "nimbusware_projections.*",
        "nimbusware_client",
        "nimbusware_client.*",
        "hermes_agent_tools",
        "hermes_agent_tools.*",
    },
)


def test_tranche_b_listed_in_mypy_strict_override() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    marker = "fo720 (Lane W2)"
    idx = text.find(marker)
    assert idx >= 0, "missing Lane W2 mypy override block"
    block = text[idx : idx + 600]
    assert "ignore_errors = false" in block
    for module in _TRANCHE_B_MODULES:
        assert module in block, f"missing strict mypy override entry for {module}"

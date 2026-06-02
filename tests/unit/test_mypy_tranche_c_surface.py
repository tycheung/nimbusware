from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"
_TARGETS = _REPO / "scripts" / "mypy_ci_targets.py"

_TRANCHE_C_MODULES = frozenset(
    {
        "agent_core",
        "agent_core.*",
        "hermes_store",
        "hermes_store.*",
        "nimbusware_config",
        "nimbusware_config.*",
        "hermes_executor",
        "hermes_executor.*",
        "hermes_extensions",
        "hermes_extensions.*",
        "hermes_memory",
        "hermes_memory.*",
        "nimbusware_iam",
        "nimbusware_iam.*",
        "nimbusware_env",
        "nimbusware_env.*",
    },
)


def test_tranche_c_listed_in_mypy_strict_override() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    marker = "fo730 (Lane X1)"
    idx = text.find(marker)
    assert idx >= 0, "missing Lane X1 / tranche C mypy override block"
    block = text[idx : idx + 900]
    assert "ignore_errors = false" in block
    for module in _TRANCHE_C_MODULES:
        assert module in block, f"missing strict mypy override entry for {module}"


def test_tranche_c_paths_in_ci_targets() -> None:
    text = _TARGETS.read_text(encoding="utf-8")
    for pkg in (
        "agent_core",
        "hermes_store",
        "nimbusware_config",
        "hermes_executor",
        "hermes_extensions",
        "hermes_memory",
        "nimbusware_iam",
        "nimbusware_env",
    ):
        assert f"packages/{pkg}" in text, f"missing CI mypy path for {pkg}"

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"

_STRICT_MODULES = frozenset(
    {
        "nimbusware_console.services",
        "nimbusware_console.services.*",
        "nimbusware_maker.services",
        "nimbusware_maker.services.*",
    },
)


def test_services_listed_in_mypy_strict_override_after_ui_ignore() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    ui_marker = text.find("fo731 (Lane X2)")
    assert ui_marker >= 0
    services_marker = text.find("fo610 (Lane V1)")
    assert services_marker >= 0
    assert services_marker > ui_marker
    services_block = text[services_marker : services_marker + 400]
    assert "ignore_errors = false" in services_block
    for module in _STRICT_MODULES:
        assert module in services_block, f"missing strict mypy override entry for {module}"

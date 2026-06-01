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
    ui_ignore = text.find('module = ["nimbusware_console.*", "nimbusware_maker.*"]')
    assert ui_ignore >= 0
    services_block = text[ui_ignore:]
    assert "ignore_errors = false" in services_block
    for module in _STRICT_MODULES:
        assert module in services_block, f"missing strict mypy override entry for {module}"

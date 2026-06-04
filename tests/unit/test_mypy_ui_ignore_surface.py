from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"

# Narrowed UI ignores — must not use blanket console.*/maker.*.
_NARROWED_MARKERS = (
    "nimbusware_console.pages",
    "nimbusware_console.bundle_catalog",
    "nimbusware_maker.ui",
)

_BLANKET_UI_IGNORE = 'module = ["nimbusware_console.*", "nimbusware_maker.*"]'


def test_ui_ignore_is_narrowed_not_blanket_wildcard() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert _BLANKET_UI_IGNORE not in text, "blanket UI mypy ignore must stay removed"
    marker = "fo731 (Lane X2)"
    idx = text.find(marker)
    assert idx >= 0, "missing fo731 narrowed UI ignore block"
    block = text[idx : idx + 2400]
    assert "ignore_errors = true" in block
    for entry in _NARROWED_MARKERS:
        assert entry in block, f"missing narrowed UI ignore entry {entry}"

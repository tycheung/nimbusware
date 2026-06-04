from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MAKER_UI = _REPO / "packages" / "nimbusware_maker" / "ui"


def test_maker_streamlit_ui_package_removed() -> None:
    """Maker Streamlit ui/ was removed; web UI lives in nimbusware_maker_web."""
    assert not _MAKER_UI.is_dir()

from __future__ import annotations

from env.launcher_theme import BG, BG_LOG, BG_PANEL, resolve_logo_path


def test_resolve_logo_path_prefers_png() -> None:
    path = resolve_logo_path()
    assert path is not None
    assert path.suffix.lower() == ".png"
    assert path.is_file()


def test_brand_colors() -> None:
    assert BG == "#00132d"
    assert BG_PANEL != BG
    assert BG_LOG != BG

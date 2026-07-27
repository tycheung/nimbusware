from __future__ import annotations

from env.launcher_theme import (
    BG,
    BG_BUTTON_ACCENT,
    BG_BUTTON_DANGER,
    BG_LOG,
    BG_PANEL,
    resolve_logo_path,
)


def test_resolve_logo_path_prefers_png() -> None:
    path = resolve_logo_path()
    assert path is not None
    assert path.suffix.lower() == ".png"
    assert path.is_file()


def test_brand_colors_night_harbor() -> None:
    assert BG == "#00132d"
    assert BG_PANEL != BG
    assert BG_LOG != BG
    assert BG_BUTTON_ACCENT != BG
    assert BG_BUTTON_DANGER != BG_PANEL


def test_customtkinter_available() -> None:
    import customtkinter as ctk

    assert hasattr(ctk, "CTk")

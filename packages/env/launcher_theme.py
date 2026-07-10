"""Visual theme for the Nimbusware desktop launcher."""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

BG = "#00132d"
BG_PANEL = "#001a3d"
BG_LOG = "#000b1a"
BG_BUTTON = "#0f2f5c"
BG_BUTTON_HOVER = "#1a4a85"
BG_BUTTON_ACCENT = "#f0f4fa"
TEXT = "#f0f4fa"
TEXT_MUTED = "#8fa3c4"
TEXT_ACCENT = "#4d9fff"
BORDER = "#1e3a5f"
LOG_FG = "#c8d6ea"


@dataclass(frozen=True)
class LauncherTheme:
    bg: str = BG
    panel: str = BG_PANEL
    log_bg: str = BG_LOG
    text: str = TEXT
    text_muted: str = TEXT_MUTED
    logo: tk.PhotoImage | None = None


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass) / "assets"
            if bundled.is_dir():
                return bundled
    return Path(__file__).resolve().parent / "assets"


def resolve_logo_path() -> Path | None:
    assets = _assets_dir()
    for name in ("nimbusware_logo.png", "nimbusware_logo.svg"):
        candidate = assets / name
        if candidate.is_file():
            return candidate
    return None


def load_logo_photo(master: tk.Misc) -> tk.PhotoImage | None:
    path = resolve_logo_path()
    if path is None or path.suffix.lower() != ".png":
        return None
    try:
        return tk.PhotoImage(master=master, file=str(path))
    except tk.TclError:
        return None


def _ui_family() -> str:
    if sys.platform == "win32":
        return "Segoe UI"
    if sys.platform == "darwin":
        return "SF Pro Text"
    return "DejaVu Sans"


def apply_launcher_theme(root: tk.Tk) -> LauncherTheme:
    root.configure(bg=BG)
    logo = load_logo_photo(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    family = _ui_family()
    title_font = tkfont.Font(family=family, size=22, weight="bold")
    body_font = tkfont.Font(family=family, size=10)
    mono_font = tkfont.Font(
        family="Consolas" if sys.platform == "win32" else "Menlo",
        size=10,
    )

    style.configure(".", background=BG, foreground=TEXT, font=body_font)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure(
        "TLabel",
        background=BG,
        foreground=TEXT,
        font=body_font,
    )
    style.configure(
        "Muted.TLabel",
        background=BG,
        foreground=TEXT_MUTED,
        font=body_font,
    )
    style.configure(
        "Title.TLabel",
        background=BG,
        foreground=TEXT,
        font=title_font,
    )
    style.configure(
        "PanelTitle.TLabel",
        background=BG_PANEL,
        foreground=TEXT_MUTED,
        font=tkfont.Font(family=family, size=9, weight="bold"),
    )
    style.configure(
        "TButton",
        background=BG_BUTTON,
        foreground=TEXT,
        borderwidth=0,
        focusthickness=0,
        padding=(12, 7),
        font=body_font,
    )
    style.map(
        "TButton",
        background=[("active", BG_BUTTON_HOVER), ("disabled", BG_PANEL)],
        foreground=[("disabled", TEXT_MUTED)],
    )
    style.configure(
        "Accent.TButton",
        background=BG_BUTTON_ACCENT,
        foreground=BG,
        padding=(14, 8),
        font=tkfont.Font(family=family, size=10, weight="bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#ffffff"), ("disabled", BG_PANEL)],
        foreground=[("disabled", TEXT_MUTED)],
    )
    style.configure(
        "TLabelframe",
        background=BG_PANEL,
        bordercolor=BORDER,
        relief="flat",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=BG_PANEL,
        foreground=TEXT_MUTED,
        font=tkfont.Font(family=family, size=9, weight="bold"),
    )

    root._launcher_fonts = (title_font, body_font, mono_font)  # type: ignore[attr-defined]
    return LauncherTheme(logo=logo)


def mono_font(root: tk.Misc) -> tkfont.Font:
    fonts = getattr(root, "_launcher_fonts", None)
    if fonts:
        return fonts[2]
    return tkfont.Font(family="Consolas" if sys.platform == "win32" else "Menlo", size=10)


def style_log_widget(widget: tk.Text) -> None:
    widget.configure(
        bg=BG_LOG,
        fg=LOG_FG,
        insertbackground=TEXT_ACCENT,
        selectbackground=BG_BUTTON_HOVER,
        selectforeground=TEXT,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=BORDER,
        padx=10,
        pady=8,
    )


def style_dialog(root: tk.Toplevel) -> None:
    root.configure(bg=BG_PANEL)
    style = ttk.Style(root)
    style.configure("Dialog.TFrame", background=BG_PANEL)
    style.configure("Dialog.TLabel", background=BG_PANEL, foreground=TEXT)
    style.configure("DialogMuted.TLabel", background=BG_PANEL, foreground=TEXT_MUTED)
    style.configure("Dialog.TEntry", fieldbackground=BG_LOG, foreground=TEXT)

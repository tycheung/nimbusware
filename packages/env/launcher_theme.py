"""Night Harbor — Nimbusware launcher visual system.

Inspired by modern desktop control panels (Docker Desktop–style hero CTA +
option cards) rather than classic ttk wizards. Built with CustomTkinter for
rounded surfaces, hover states, and HighDPI-friendly widgets.

Brand ground stays ``#00132d`` (docs/deploy/launcher.md).
"""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk
from PIL import Image

# --- Night Harbor tokens ----------------------------------------------------
BG = "#00132d"
BG_RAISED = "#071937"
BG_CARD = "#0c2348"
BG_CARD_HOVER = "#123057"
BG_INPUT = "#061428"
BG_STATUS = "#0a2a4f"
TEXT = "#eef3fb"
TEXT_MUTED = "#8fa6c7"
TEXT_SOFT = "#b7c7de"
ACCENT = "#4da3ff"
ACCENT_HOVER = "#6bb4ff"
ACCENT_SOFT = "#1a3f6e"
CTA_FG = "#00132d"
CTA_BG = "#e8eef8"
CTA_HOVER = "#ffffff"
DANGER = "#c45c6a"
DANGER_HOVER = "#d97884"
OK = "#5fbf95"
WARN = "#d4a84b"
BORDER = "#1a3a63"

RADIUS = 14
RADIUS_SM = 10


@dataclass(frozen=True)
class LauncherTheme:
    bg: str = BG
    panel: str = BG_CARD
    log_bg: str = BG_INPUT
    text: str = TEXT
    text_muted: str = TEXT_MUTED
    logo: ctk.CTkImage | None = None


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


def load_logo_image(*, size: tuple[int, int] = (52, 48)) -> ctk.CTkImage | None:
    path = resolve_logo_path()
    if path is None or path.suffix.lower() != ".png":
        return None
    try:
        image = Image.open(path)
    except OSError:
        return None
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)


def ui_font(*, size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    if sys.platform == "win32":
        family = "Segoe UI"
    elif sys.platform == "darwin":
        family = "SF Pro Text"
    else:
        family = "DejaVu Sans"
    return ctk.CTkFont(family=family, size=size, weight=weight)


def mono_font(*, size: int = 12) -> ctk.CTkFont:
    family = "Consolas" if sys.platform == "win32" else "Menlo"
    return ctk.CTkFont(family=family, size=size)


def apply_launcher_theme(root: ctk.CTk | None = None) -> tuple[ctk.CTk, LauncherTheme]:
    """Configure CustomTkinter Night Harbor appearance; return root + theme."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    window = root or ctk.CTk()
    window.configure(fg_color=BG)
    try:
        window.iconbitmap(default="")  # type: ignore[call-arg]
    except (tk.TclError, AttributeError):
        pass

    logo = load_logo_image()
    return window, LauncherTheme(logo=logo)


def style_dialog(root: tk.Toplevel) -> None:
    """Keep Postgres/setup dialogs readable on Night Harbor (ttk fallback)."""
    root.configure(bg=BG_CARD)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Dialog.TFrame", background=BG_CARD)
    style.configure("Dialog.TLabel", background=BG_CARD, foreground=TEXT)
    style.configure("DialogMuted.TLabel", background=BG_CARD, foreground=TEXT_MUTED)
    style.configure("Dialog.TEntry", fieldbackground=BG_INPUT, foreground=TEXT)
    style.configure(
        "Accent.TButton",
        background=CTA_BG,
        foreground=CTA_FG,
        padding=(14, 8),
    )
    style.map("Accent.TButton", background=[("active", CTA_HOVER)])
    style.configure("TButton", background=ACCENT_SOFT, foreground=TEXT, padding=(12, 7))
    style.map("TButton", background=[("active", ACCENT)])


# Back-compat aliases used by older tests / callers
BG_PANEL = BG_CARD
BG_LOG = BG_INPUT
BG_BUTTON_ACCENT = CTA_BG
BG_BUTTON_DANGER = DANGER


def style_log_widget(widget: tk.Text) -> None:
    widget.configure(
        bg=BG_INPUT,
        fg=TEXT_SOFT,
        insertbackground=ACCENT,
        selectbackground=ACCENT_SOFT,
        selectforeground=TEXT,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=BORDER,
        padx=12,
        pady=10,
    )

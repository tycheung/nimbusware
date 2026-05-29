"""Streamlit theme / white-label operator hints (PLAN_GAP §14 #11)."""

from __future__ import annotations

from pathlib import Path


def streamlit_theme_defaults_caption(*, repo_root: Path | None = None) -> str:
    """Read-only blurb for repo ``.streamlit/config.toml`` theme defaults."""
    root = repo_root if repo_root is not None else Path(".")
    cfg = root.resolve() / ".streamlit" / "config.toml"
    exists = cfg.is_file()
    loc = "present" if exists else "missing (Streamlit built-in defaults apply)"
    return (
        "Console theme: repo **``.streamlit/config.toml``** is "
        f"**{loc}** — override locally for branding; committed defaults use "
        "``base=light`` and ``primaryColor=#1f77b4``."
    )


def streamlit_white_label_deferred_caption() -> str:
    """Document Lane A close-out: custom CSS / white-label branding deferred."""
    return (
        "White-label: **optional branding deferred** (§14 #11) — no per-tenant CSS injection. "
        "See the deferral note at the top of ``.streamlit/config.toml``; use ``[theme]`` keys "
        "locally or fork the console for custom skins."
    )

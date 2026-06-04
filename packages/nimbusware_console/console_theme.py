from __future__ import annotations

from pathlib import Path


def streamlit_theme_defaults_caption(*, repo_root: Path | None = None) -> str:
    root = repo_root if repo_root is not None else Path(".")
    cfg = root.resolve() / ".streamlit" / "config.toml"
    loc = "present" if cfg.is_file() else "missing (built-in light theme)"
    return f"Theme: ``.streamlit/config.toml`` is **{loc}** (``base=light``, ``primaryColor=#1f77b4``)."


def streamlit_white_label_deferred_caption() -> str:
    return "White-label branding is not injected per tenant; use ``[theme]`` in ``.streamlit/config.toml`` locally."

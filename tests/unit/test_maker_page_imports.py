from __future__ import annotations

from pathlib import Path

_STATIC = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_maker_web" / "static"


def test_maker_web_shell_assets_present() -> None:
    assert (_STATIC / "index.html").is_file()
    assert (_STATIC / "js" / "app-shell.js").is_file()
    assert (_STATIC / "js" / "tab-loader.js").is_file()
    assert (_STATIC / "vendor" / "alpine.min.js").is_file()


def test_maker_tab_modules_present() -> None:
    tabs = _STATIC / "js" / "tabs"
    for name in ("chat", "home", "build", "review", "progress", "models", "settings"):
        assert (tabs / f"{name}.js").is_file()

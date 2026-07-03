from __future__ import annotations

from pathlib import Path

_DIST = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "dist"
_MAX_JS_KB = 160


def test_admin_ui_dist_present() -> None:
    assert (_DIST / "index.html").is_file()


def test_admin_ui_bundle_size_reasonable() -> None:
    assets = _DIST / "assets"
    if not assets.is_dir():
        return
    total = sum(p.stat().st_size for p in assets.glob("*.js"))
    assert total < _MAX_JS_KB * 1024, f"Admin JS bundle {total} bytes exceeds {_MAX_JS_KB}KB cap"

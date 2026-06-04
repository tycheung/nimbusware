"""Maker web mobile PWA static assets."""

from __future__ import annotations

import json
from pathlib import Path

_STATIC = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_maker_web" / "static"


def test_maker_web_has_pwa_and_slice_panel() -> None:
    html = (_STATIC / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html
    assert "manifest.json" in html
    assert "viewport" in html
    assert "apple-mobile-web-app-capable" in html
    assert 'id="slice-panel"' in html
    assert 'id="approval-panel"' in html

    manifest = json.loads((_STATIC / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("display") == "standalone"
    icons = manifest.get("icons") or []
    assert any("icon.svg" in str(i.get("src", "")) for i in icons)

    assert (_STATIC / "icon.svg").is_file()
    app_js = (_STATIC / "app.js").read_text(encoding="utf-8")
    assert "maker-progress" in app_js
    assert "slice-panel" in html or "slice-list" in app_js


def test_maker_web_has_slice_approval_controls() -> None:
    html = (_STATIC / "index.html").read_text(encoding="utf-8")
    app_js = (_STATIC / "app.js").read_text(encoding="utf-8")
    assert "btn-load-pending" in html
    assert "/maker/pending" in app_js
    assert "/maker/plan/approve" in app_js
    assert "/maker/slices/apply" in app_js
    assert "/maker/slices/skip" in app_js
    assert "/maker/slices/prepare" in app_js

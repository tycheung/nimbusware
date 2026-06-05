"""Maker web mobile PWA static assets."""

from __future__ import annotations

import json
from pathlib import Path

_STATIC = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_maker_web" / "static"


def test_maker_web_has_pwa_manifest_and_mobile_shell() -> None:
    html = (_STATIC / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html
    assert "manifest.json" in html
    assert "viewport" in html
    assert "apple-mobile-web-app-capable" in html
    assert "apple-touch-icon" in html
    assert "mobile-bottom-nav" in html
    assert "mobile-run-bar" in html
    assert "run-theater-run-id" in html

    manifest = json.loads((_STATIC / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("display") == "standalone"
    assert manifest.get("scope") == "/v1/maker/app/"
    assert "#/progress" in manifest.get("start_url", "")
    icons = manifest.get("icons") or []
    png_sizes = {i.get("sizes") for i in icons if str(i.get("type", "")).endswith("png")}
    assert "192x192" in png_sizes
    assert "512x512" in png_sizes
    assert (_STATIC / "icon-192.png").is_file()
    assert (_STATIC / "icon-512.png").is_file()


def test_maker_web_mobile_css_and_tabs() -> None:
    css = (_STATIC / "styles.css").read_text(encoding="utf-8")
    assert "body.mobile-mode" in css
    assert ".mobile-bottom-nav" in css
    assert ".mobile-advanced" in css

    shell_js = (_STATIC / "js" / "app-shell.js").read_text(encoding="utf-8")
    assert "MOBILE_TABS" in shell_js
    assert "mobileMode" in shell_js
    assert "detectMobileMode" in shell_js


def test_maker_web_review_progress_approval_paths() -> None:
    review_js = (_STATIC / "js" / "tabs" / "review.js").read_text(encoding="utf-8")
    assert "/maker/pending" in review_js
    assert "/maker/plan/approve" in review_js
    assert "maker/slices" in review_js
    assert "Apply" in review_js and "Skip" in review_js
    assert "mobile-advanced" in review_js

    progress_js = (_STATIC / "js" / "tabs" / "progress.js").read_text(encoding="utf-8")
    assert "maker-progress" in progress_js or "theater" in progress_js

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
    assert "serviceWorker" in shell_js
    assert "maybeEnableMobilePush" in shell_js
    assert "maybeRegisterPushSubscription" in shell_js
    assert (_STATIC / "sw.js").is_file()
    sw = (_STATIC / "sw.js").read_text(encoding="utf-8")
    assert 'addEventListener("push"' in sw
    assert "notificationclick" in sw


def test_maker_models_preset_wizard_paths() -> None:
    models_js = (_STATIC / "js" / "tabs" / "models.js").read_text(encoding="utf-8")
    assert "/platform/models/ranked" in models_js
    assert "/platform/models/apply-preset" in models_js
    assert "/platform/hardware" in models_js
    assert "gpu_only" in models_js
    assert "gpu_group_index" in models_js
    assert "models-gpu-only" in models_js
    assert "model_id" in models_js
    assert "models-wizard" in models_js
    assert 'preset: "recommended"' not in models_js


def test_maker_settings_governor_panel_paths() -> None:
    settings_js = (_STATIC / "js" / "tabs" / "settings.js").read_text(encoding="utf-8")
    assert "governor-panel" in settings_js
    assert "NIMBUSWARE_MAX_VRAM_PCT" in settings_js
    assert "max_parallel_writer_stages" in settings_js
    assert "/platform/hardware" in settings_js


def test_maker_web_review_progress_approval_paths() -> None:
    review_js = (_STATIC / "js" / "tabs" / "review.js").read_text(encoding="utf-8")
    assert "/maker/pending" in review_js
    assert "/maker/plan/approve" in review_js
    assert "maker/slices" in review_js
    assert "Apply" in review_js and "Skip" in review_js
    assert "mobile-advanced" in review_js

    progress_js = (_STATIC / "js" / "tabs" / "progress.js").read_text(encoding="utf-8")
    progress_tpl = (_STATIC / "js" / "tabs" / "progress" / "template.js").read_text(
        encoding="utf-8"
    )
    assert "maker-progress" in progress_js or "theater" in progress_js
    assert "maker-completion-cockpit" in progress_tpl
    assert "critic-reliability" in progress_tpl

    plan_js = (_STATIC / "js" / "tabs" / "plan.js").read_text(encoding="utf-8")
    assert "/campaigns/" in plan_js and "maker-plan-tree" in plan_js

    settings_js = (_STATIC / "js" / "tabs" / "settings.js").read_text(encoding="utf-8")
    assert "maker-settings-memory-library" in settings_js
    assert "promote-stitch-pending" in settings_js

    theater_css = (_STATIC / "css" / "theater.css").read_text(encoding="utf-8")
    assert "body.mobile-mode #theater-list" in theater_css

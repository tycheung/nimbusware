"""Maker facade structure and import shim contracts (Phase S2 / fo502)."""

from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root


def test_app_entry_is_thin_facade() -> None:
    path = find_repo_root(start=Path(__file__).resolve().parents[1]) / "packages" / "nimbusware_maker" / "app.py"
    text = path.read_text(encoding="utf-8")
    assert "from nimbusware_maker.ui import render_main" in text
    assert "st.set_page_config" in text
    assert len(text.splitlines()) <= 20


def test_ui_exports_render_main() -> None:
    from nimbusware_maker.ui import render_main

    assert callable(render_main)


def test_package_exports_project_record_and_store_builder() -> None:
    from nimbusware_maker import ProjectRecord, build_project_store

    assert ProjectRecord is not None
    assert callable(build_project_store)


def test_home_section_exports() -> None:
    from nimbusware_maker.ui.home import render_projects_panel, render_readiness_strip

    assert callable(render_projects_panel)
    assert callable(render_readiness_strip)


def test_wizard_section_export() -> None:
    from nimbusware_maker.ui.wizard import render_first_run_wizard

    assert callable(render_first_run_wizard)


def test_maker_ui_module_paths() -> None:
    base = find_repo_root(start=Path(__file__).resolve().parents[1]) / "packages" / "nimbusware_maker" / "ui"
    for name in (
        "home.py",
        "intent.py",
        "approval.py",
        "progress.py",
        "settings.py",
        "wizard.py",
    ):
        assert (base / name).is_file(), name

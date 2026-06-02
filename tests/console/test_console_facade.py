"""Console facade structure and import shim contracts (Phase 4)."""

from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root


def test_app_entry_is_thin_facade() -> None:
    path = (
        find_repo_root(start=Path(__file__).resolve().parents[1])
        / "packages"
        / "nimbusware_console"
        / "app.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "from nimbusware_console.main import render_main" in text
    assert "st.set_page_config" in text
    assert len(text.splitlines()) <= 20


def test_main_exports_render_main() -> None:
    from nimbusware_console.main import render_main

    assert callable(render_main)


def test_settings_api_base_default() -> None:
    from nimbusware_console.settings import default_api_base

    assert default_api_base().endswith("/v1")


def test_run_list_section_export() -> None:
    from nimbusware_console.pages.run_list import render_run_list_section

    assert callable(render_run_list_section)


def test_preflight_fleet_section_export() -> None:
    from nimbusware_console.pages.preflight_fleet import render_preflight_fleet_section

    assert callable(render_preflight_fleet_section)


def test_config_tooling_section_export() -> None:
    from nimbusware_console.pages.config_tooling import render_config_tooling_section

    assert callable(render_config_tooling_section)


def test_run_detail_section_export() -> None:
    from nimbusware_console.pages.run_detail import render_run_detail_section

    assert callable(render_run_detail_section)


def test_legacy_sections_shim_exports() -> None:
    from nimbusware_console.legacy_sections import (
        render_config_tooling_section,
        render_run_detail_section,
    )

    assert callable(render_config_tooling_section)
    assert callable(render_run_detail_section)


def test_console_pages_module_paths() -> None:
    base = (
        find_repo_root(start=Path(__file__).resolve().parents[1])
        / "packages"
        / "nimbusware_console"
        / "pages"
    )
    assert (base / "config_tooling").is_dir()
    assert (base / "run_detail").is_dir()
    assert (base / "run_list.py").is_file()
    assert (base / "preflight_fleet.py").is_file()


def test_run_detail_section_modules() -> None:
    base = (
        find_repo_root(start=Path(__file__).resolve().parents[1])
        / "packages"
        / "nimbusware_console"
        / "pages"
        / "run_detail"
    )
    for name in (
        "summary.py",
        "timeline_core.py",
        "timeline_integrator.py",
        "timeline_personas.py",
        "timeline_escalation.py",
        "timeline_misc.py",
        "critic_matrix.py",
        "findings.py",
        "actions.py",
    ):
        assert (base / name).is_file(), name

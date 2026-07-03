from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root


def test_console_exports_web_entry() -> None:
    from nimbusware_console import WEB_ENTRY

    assert "/v1/admin/app/" in WEB_ENTRY


def test_settings_api_base_default() -> None:
    from nimbusware_console.settings import default_api_base

    assert default_api_base().endswith("/v1")


def test_admin_web_dist_present() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    dist = root / "packages" / "nimbusware_admin_ui" / "dist" / "index.html"
    assert dist.is_file()


def test_display_helpers_remain() -> None:
    from nimbusware_console.critic_reliability_display import fleet_critic_reliability_caption

    assert callable(fleet_critic_reliability_caption)

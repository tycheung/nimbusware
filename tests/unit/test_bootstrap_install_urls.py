from __future__ import annotations

from bootstrap.cli import curl_bootstrap_line
from bootstrap.platform import github_repo_parts, install_script_raw_url


def test_github_repo_parts_strips_git_suffix() -> None:
    assert github_repo_parts("https://github.com/tycheung/nimbusware.git") == (
        "tycheung",
        "nimbusware",
    )


def test_install_script_raw_url_uses_raw_githubusercontent() -> None:
    url = install_script_raw_url("https://github.com/tycheung/nimbusware.git")
    assert url == (
        "https://raw.githubusercontent.com/tycheung/nimbusware/main/"
        "scripts/install/install_nimbusware.py"
    )
    assert ".git/" not in url
    assert "/scripts/install_nimbusware.py" not in url  # not the thin wrapper


def test_curl_bootstrap_line_points_at_real_installer() -> None:
    line = curl_bootstrap_line(
        "https://github.com/tycheung/nimbusware.git",
        profile="barebones",
    )
    assert "raw.githubusercontent.com/tycheung/nimbusware/main/" in line
    assert "scripts/install/install_nimbusware.py" in line
    assert "--install-profile barebones" in line
    assert "--skip-postgres" in line


def test_curl_bootstrap_recommended_matches_full_setup_flags() -> None:
    line = curl_bootstrap_line(
        "https://github.com/tycheung/nimbusware.git",
        profile="recommended",
    )
    assert "--postgres-choice provided" in line
    assert "--skip-docker" in line
    assert "--seed-config" in line
    assert "--install-profile recommended" in line

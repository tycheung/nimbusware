from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root


def test_maker_web_package_present() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    static = root / "packages" / "nimbusware_maker_web" / "static"
    assert (static / "index.html").is_file()
    assert (static / "js" / "app-shell.js").is_file()


def test_package_exports_project_record_and_store_builder() -> None:
    from nimbusware_maker import ProjectRecord, build_project_store

    assert ProjectRecord is not None
    assert callable(build_project_store)


def test_maker_cli_entry() -> None:
    from nimbusware_maker.cli import main

    assert callable(main)

from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.workspace import copy_fixture_repo, fixture_repo_root

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_tiny_api_app_fixture_exists() -> None:
    root = fixture_repo_root("tiny_api_app")
    assert (root / "src" / "app" / "routes.py").is_file()


def test_tiny_api_app_fixture_copy(tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_api_app", tmp_path / "api-ws")
    assert (ws / "src" / "app" / "routes.py").is_file()

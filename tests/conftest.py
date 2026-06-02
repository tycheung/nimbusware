"""Pytest: load repository ``.env`` before any Nimbusware / Hermes imports in tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root, load_dotenv

_REPO = find_repo_root(start=Path(__file__).resolve().parent)
load_dotenv(repo_root=_REPO)


@pytest.fixture(autouse=True)
def _unit_tests_use_file_config(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unit tests use on-disk ``configs/`` or ``tmp_path`` trees.

      ``NIMBUSWARE_DATABASE_URL`` from ``.env`` applies only to ``@pytest.mark.integration``
    tests (and tests that ``setenv`` Postgres explicitly mid-test).
    """
    if request.node.get_closest_marker("integration") is not None:
        return
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)

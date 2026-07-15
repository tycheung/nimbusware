from __future__ import annotations

from pathlib import Path

import pytest

from env import find_repo_root, load_dotenv

_REPO = find_repo_root(start=Path(__file__).resolve().parent)
load_dotenv(repo_root=_REPO)


@pytest.fixture(autouse=True)
def _unit_tests_use_file_config(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unit tests use on-disk ``configs/`` or ``tmp_path`` trees.

    Strip ``NIMBUSWARE_DATABASE_URL`` from ``.env`` for non-integration tests
    (and tests that ``setenv`` Postgres explicitly mid-test).
    """
    if request.node.get_closest_marker("integration") is not None:
        return
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    # GitHub unit job has no NIMBUSWARE_USE_LLM; local .env often sets 0 for stub runs.
    monkeypatch.delenv("NIMBUSWARE_USE_LLM", raising=False)
    # Avoid spawning pyright-langserver during ordinary unit runs (slow / flaky).
    monkeypatch.setenv("NIMBUSWARE_SLICE_LSP_ENABLED", "0")


@pytest.fixture(autouse=True)
def _reset_collab_runtime_override() -> None:
    yield
    from env.collab_runtime import clear_runtime_collab_override

    clear_runtime_collab_override()


@pytest.fixture(autouse=True)
def _reset_playwright_sessions() -> None:
    yield
    from orchestrator.browser_controller import close_all_persistent_browsers

    close_all_persistent_browsers()

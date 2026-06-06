from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_micro_slice_web_profile_loads() -> None:
    from nimbusware_env import find_repo_root
    from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict

    repo = find_repo_root()
    profile = workflow_profile_dict(repo, "micro_slice_web")
    assert profile.get("slice", {}).get("e2e", {}).get("enabled") is True


def test_tiny_web_app_fixture_copy(tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_web_app", tmp_path / "web-ws")
    assert (ws / "index.html").is_file()

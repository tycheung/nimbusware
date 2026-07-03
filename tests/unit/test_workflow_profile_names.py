from __future__ import annotations

from env import find_repo_root
from orchestrator.workflow_profiles import list_workflow_profile_names


def test_list_workflow_profile_names_includes_defaults() -> None:
    names = list_workflow_profile_names(find_repo_root())
    assert "default" in names
    assert "micro_slice" in names
    assert "critique_test_base" in names
    assert all(not name.startswith("_") for name in names)

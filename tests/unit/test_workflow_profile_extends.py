from __future__ import annotations

from env import find_repo_root
from orchestrator.workflow_profiles import workflow_profile_dict


def test_workflow_profile_extends_merges_universal_critique_stub() -> None:
    repo = find_repo_root()
    merged = workflow_profile_dict(repo, "universal_critique_stub_on")
    uc = merged.get("universal_critique")
    assert isinstance(uc, dict)
    tw = uc.get("test_writer")
    assert isinstance(tw, dict)
    assert tw.get("stub") is True
    assert tw.get("enabled") is True
    assert merged.get("version") == 1
    assert "extends" not in merged

from __future__ import annotations

from pathlib import Path

from config.workflow_read import resolved_workflow_profile_dict


def test_resolved_workflow_profile_dict_micro_slice() -> None:
    root = Path(__file__).resolve().parents[2]
    profile, trace = resolved_workflow_profile_dict(root, "micro_slice")
    assert isinstance(profile, dict)
    assert profile.get("workflow") or profile.get("extends") or profile
    assert any("micro_slice" in step for step in trace)

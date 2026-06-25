from __future__ import annotations

from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]


def test_safe_coding_workflow_profile() -> None:
    path = _REPO / "configs" / "workflows" / "safe_coding.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["maker_approval"]["enabled"] is True
    assert data["agent_evaluator"]["enabled"] is True
    assert data["universal_critique"]["critic_pack_id"] == "default-security"
    assert data["fast_slice"] is False
    stages = [s["stage_name"] for s in data["stage_graph"]]
    assert "slice.gate" in stages
    assert "launch_test.plan" in stages

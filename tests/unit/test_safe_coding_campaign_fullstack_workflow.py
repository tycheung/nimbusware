from __future__ import annotations

from pathlib import Path

import yaml

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.workflow_campaign import (
    parse_backlog_workflow_block,
    parse_campaign_workflow_block,
)

_REPO = Path(__file__).resolve().parents[2]


def test_safe_coding_campaign_fullstack_workflow_profile() -> None:
    path = _REPO / "configs" / "workflows" / "safe_coding_campaign_fullstack.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["workflow_profile"] == "safe_coding_campaign_fullstack"
    assert data["maker_approval"]["enabled"] is True
    assert data["campaign"]["enabled"] is True
    assert "frontend-owasp" in data["universal_critique"]["industry_critic_pack_ids"]
    stages = [s["stage_name"] for s in data["stage_graph"]]
    assert "slice.contract" in stages
    assert "slice.gate" in stages


def test_safe_coding_campaign_fullstack_parses_campaign_blocks() -> None:
    repo = find_repo_root(start=_REPO)
    profile = "safe_coding_campaign_fullstack"
    campaign = parse_campaign_workflow_block(repo, profile)
    assert campaign.enabled is True
    backlog = parse_backlog_workflow_block(repo, profile)
    assert backlog.generator == "heuristic"

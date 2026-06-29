from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_maker.collab_invite_templates import list_invite_templates


def test_list_invite_templates_loads_yaml_catalog() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    templates = list_invite_templates(repo_root=repo)
    ids = {row["id"] for row in templates}
    assert "pair-devs-qa" in ids
    assert "security-review" in ids
    security = next(row for row in templates if row["id"] == "security-review")
    assert "architect" in security["disciplines"]

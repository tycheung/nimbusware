from __future__ import annotations

from pathlib import Path

from maker.tenant_collab_defaults import (
    tenant_default_agent_overlay,
    tenant_default_join_discipline,
)


def test_tenant_defaults_from_collab_policy(tmp_path: Path, monkeypatch) -> None:
    policy = tmp_path / "configs" / "collab_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        "version: 1\ndefault_join_discipline: qa\ndefault_agent_overlays:\n  qa: Verify acceptance criteria\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("maker.tenant_collab_defaults.find_repo_root", lambda: tmp_path)
    assert tenant_default_join_discipline(None) == "qa"
    assert tenant_default_agent_overlay(None, "qa") == "Verify acceptance criteria"

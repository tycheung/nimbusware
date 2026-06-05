from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.critic_pack_resolve import (
    critic_pack_id_from_workflow,
    load_critic_pack,
    resolve_critic_pack_for_workflow,
)


def test_load_critic_pack_from_repo(tmp_path: Path) -> None:
    pack_dir = tmp_path / "configs" / "critic_packs"
    pack_dir.mkdir(parents=True)
    (pack_dir / "default-security.yaml").write_text(
        "id: default-security\ndomain: security\nblocking_authority: advisory\n",
        encoding="utf-8",
    )
    pack = load_critic_pack(tmp_path, "default-security")
    assert pack is not None
    assert pack.get("domain") == "security"


def test_critic_pack_id_from_workflow() -> None:
    wf = {"universal_critique": {"critic_pack_id": "default-security"}}
    assert critic_pack_id_from_workflow(wf) == "default-security"


def test_resolve_critic_pack_for_workflow(tmp_path: Path) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "micro_slice.yaml").write_text(
        "universal_critique:\n  critic_pack_id: default-security\n",
        encoding="utf-8",
    )
    pack_dir = tmp_path / "configs" / "critic_packs"
    pack_dir.mkdir(parents=True)
    (pack_dir / "default-security.yaml").write_text(
        "domain: security\nblocking_authority: advisory\n",
        encoding="utf-8",
    )
    resolved = resolve_critic_pack_for_workflow(tmp_path, "micro_slice")
    assert resolved is not None
    assert resolved.get("resolved") is True
    assert resolved.get("domain") == "security"

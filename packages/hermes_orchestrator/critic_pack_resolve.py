from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from nimbusware_config.persist import load_workflow_profile_dict


def critic_pack_id_from_workflow(wf_content: dict[str, Any]) -> str | None:
    uc = wf_content.get("universal_critique")
    if not isinstance(uc, dict):
        return None
    raw = uc.get("critic_pack_id")
    if raw is None:
        return None
    pack_id = str(raw).strip()
    return pack_id or None


def load_critic_pack(
    repo_root: Path,
    pack_id: str,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            return cast(
                dict[str, Any],
                config_materializer.get_critic_pack(pack_id),
            )
        except KeyError:
            return None
    path = repo_root / "configs" / "critic_packs" / f"{pack_id}.yaml"
    if not path.is_file():
        return None
    from hermes_orchestrator.merge import load_yaml

    raw = load_yaml(path)
    return raw if isinstance(raw, dict) else None


def resolve_critic_pack_for_workflow(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    wf = load_workflow_profile_dict(
        repo_root,
        workflow_profile,
        materializer=config_materializer,
    )
    pack_id = critic_pack_id_from_workflow(wf)
    if not pack_id:
        return None
    pack = load_critic_pack(repo_root, pack_id, config_materializer=config_materializer)
    if pack is None:
        return {"critic_pack_id": pack_id, "resolved": False}
    return {
        "critic_pack_id": pack_id,
        "resolved": True,
        "domain": str(pack.get("domain") or ""),
        "blocking_authority": str(pack.get("blocking_authority") or ""),
    }


def list_critic_pack_ids(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> list[str]:
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        return list(config_materializer.list_critic_pack_ids())
    root = repo_root / "configs" / "critic_packs"
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.yaml"))

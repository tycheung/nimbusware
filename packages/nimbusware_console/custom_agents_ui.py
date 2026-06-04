from __future__ import annotations

from pathlib import Path

from hermes_extensions.custom_agents import CustomAgentRegistry
from nimbusware_config.persist import load_custom_agent_registry


def load_registry_local(repo_root: Path) -> CustomAgentRegistry:
    return load_custom_agent_registry(repo_root)


def render_custom_agents_sidebar(repo_root: Path) -> str | None:
    raise RuntimeError("Custom agents UI moved to /v1/admin/app/.")

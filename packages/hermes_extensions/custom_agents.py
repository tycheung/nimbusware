"""Custom operator-defined agents with dedicated system prompts (fo151)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_orchestrator.merge import atomic_write_yaml, load_yaml


@dataclass
class CustomAgent:
    id: str
    display_name: str
    system_prompt: str
    description: str = ""
    bound_role_id: str | None = None
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "display_name": self.display_name,
            "system_prompt": self.system_prompt,
            "description": self.description,
            "version": self.version,
        }
        if self.bound_role_id:
            out["bound_role_id"] = self.bound_role_id
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CustomAgent:
        return cls(
            id=str(raw["id"]).strip(),
            display_name=str(raw.get("display_name", raw["id"])).strip(),
            system_prompt=str(raw.get("system_prompt", "")),
            description=str(raw.get("description", "")).strip(),
            bound_role_id=(
                str(raw["bound_role_id"]).strip() if raw.get("bound_role_id") else None
            ),
            version=int(raw.get("version", 1) or 1),
        )


class CustomAgentRegistry:
    def __init__(self, agents: dict[str, CustomAgent]) -> None:
        self._agents = dict(agents)

    @property
    def agents(self) -> dict[str, CustomAgent]:
        return dict(self._agents)

    def get(self, agent_id: str) -> CustomAgent | None:
        return self._agents.get(agent_id)

    def list(self) -> list[CustomAgent]:
        return sorted(self._agents.values(), key=lambda a: a.id)

    def upsert(self, agent: CustomAgent) -> None:
        if agent.id in self._agents:
            agent = CustomAgent(
                id=agent.id,
                display_name=agent.display_name,
                system_prompt=agent.system_prompt,
                description=agent.description,
                bound_role_id=agent.bound_role_id,
                version=self._agents[agent.id].version + 1,
            )
        self._agents[agent.id] = agent

    def remove(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def to_content(self) -> dict[str, Any]:
        return {"agents": [a.to_dict() for a in self.list()]}

    @classmethod
    def from_content(cls, content: dict[str, Any]) -> CustomAgentRegistry:
        raw = content.get("agents")
        agents: dict[str, CustomAgent] = {}
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("id"):
                    agent = CustomAgent.from_dict(item)
                    agents[agent.id] = agent
        return cls(agents)

    @classmethod
    def load(cls, path: Path) -> CustomAgentRegistry:
        if not path.is_file():
            return cls({})
        content = load_yaml(path)
        if not isinstance(content, dict):
            return cls({})
        return cls.from_content(content)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_yaml(path, self.to_content())


def default_registry_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "custom_agents" / "registry.yaml"

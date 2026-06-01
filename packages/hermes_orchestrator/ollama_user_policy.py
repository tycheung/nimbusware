"""User-facing Ollama model management policy (stored in model-routing.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OllamaUserPolicy:
    allow_pull: bool = False
    allow_delete: bool = False
    allow_update_routing: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "allow_pull": self.allow_pull,
            "allow_delete": self.allow_delete,
            "allow_update_routing": self.allow_update_routing,
        }


def policy_from_mapping(raw: object) -> OllamaUserPolicy:
    if not isinstance(raw, dict):
        return OllamaUserPolicy()
    return OllamaUserPolicy(
        allow_pull=bool(raw.get("allow_pull", False)),
        allow_delete=bool(raw.get("allow_delete", False)),
        allow_update_routing=bool(raw.get("allow_update_routing", False)),
    )


def policy_from_routing(routing: dict[str, Any]) -> OllamaUserPolicy:
    return policy_from_mapping(routing.get("ollama_user_policy"))


def merge_policy_into_routing(
    routing: dict[str, Any],
    *,
    allow_pull: bool | None = None,
    allow_delete: bool | None = None,
    allow_update_routing: bool | None = None,
) -> dict[str, Any]:
    current = policy_from_routing(routing)
    updated = OllamaUserPolicy(
        allow_pull=current.allow_pull if allow_pull is None else allow_pull,
        allow_delete=current.allow_delete if allow_delete is None else allow_delete,
        allow_update_routing=(
            current.allow_update_routing
            if allow_update_routing is None
            else allow_update_routing
        ),
    )
    out = dict(routing)
    out["ollama_user_policy"] = updated.to_dict()
    return out


def assert_user_may(policy: OllamaUserPolicy, action: str) -> None:
    if action == "pull" and not policy.allow_pull:
        raise PermissionError("pull disabled by ollama_user_policy")
    if action == "delete" and not policy.allow_delete:
        raise PermissionError("delete disabled by ollama_user_policy")
    if action == "update_routing" and not policy.allow_update_routing:
        raise PermissionError("routing update disabled by ollama_user_policy")

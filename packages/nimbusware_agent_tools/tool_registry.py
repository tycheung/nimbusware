"""Agent tool allowlist from operator env."""

from __future__ import annotations

_DEFAULT_TOOLS = ("read", "write", "edit", "grep", "shell")
_OPTIONAL_READONLY = ("find", "ls")
_ALL_TOOLS = _DEFAULT_TOOLS + _OPTIONAL_READONLY


def nimbusware_agent_tools_allowlist() -> frozenset[str]:
    from nimbusware_env.env_flags import nimbusware_agent_tools_list

    return frozenset(nimbusware_agent_tools_list())


def agent_tool_list_prompt() -> str:
    tools = sorted(nimbusware_agent_tools_allowlist())
    base = "read, write, edit, grep, shell"
    extras = [t for t in ("find", "ls", "browser_act") if t in tools]
    if extras:
        return base + ", " + ", ".join(extras)
    return base


def is_agent_tool_enabled(name: str) -> bool:
    return name.strip().lower() in nimbusware_agent_tools_allowlist()

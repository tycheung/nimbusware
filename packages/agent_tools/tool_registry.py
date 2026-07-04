from __future__ import annotations

_DEFAULT_TOOLS = ("read", "write", "edit", "grep", "shell")
_OPTIONAL_READONLY = ("find", "ls")
_ALL_TOOLS = _DEFAULT_TOOLS + _OPTIONAL_READONLY


def agent_tools_allowlist() -> frozenset[str]:
    from env.env_flags import agent_tools_list

    return frozenset(agent_tools_list())


def agent_tool_list_prompt(*, shorthand: bool = True) -> str:
    from agent_core.tool_schema import default_tool_schema_resolver

    tools = agent_tools_allowlist()
    if shorthand:
        return default_tool_schema_resolver().shorthand_list(tools)
    names = sorted(tools)
    base = "read, write, edit, grep, shell"
    extras = [t for t in ("find", "ls", "browser_act", "memory_fetch") if t in names]
    if extras:
        return base + ", " + ", ".join(extras)
    return base


def is_agent_tool_enabled(name: str) -> bool:
    return name.strip().lower() in agent_tools_allowlist()

from __future__ import annotations

import os
from typing import Literal

_BROKER_LLM_ENV = "NIMBUSWARE_BROKER_LLM"
_BROKER_MCP_ENV = "NIMBUSWARE_BROKER_MCP"
_BROKER_SANDBOX_ENV = "NIMBUSWARE_BROKER_SANDBOX"
_BROKER_TOOLS_ENV = "NIMBUSWARE_BROKER_TOOLS"
_BROKER_MEMORY_ENV = "NIMBUSWARE_BROKER_MEMORY"
_BROKER_RESEARCH_ENV = "NIMBUSWARE_BROKER_RESEARCH"
_BROKER_EGRESS_ENV = "NIMBUSWARE_BROKER_EGRESS"
_BROKER_COMPUTE_ENV = "NIMBUSWARE_BROKER_COMPUTE"
_BROKER_CAPACITY_ENV = "NIMBUSWARE_BROKER_CAPACITY"

Backend = Literal["broker", "python"]
LlmBackend = Backend
FlagMode = Literal[0, 1, 2]

_DOMAIN_ENV: dict[str, str] = {
    "llm": _BROKER_LLM_ENV,
    "sandbox": _BROKER_SANDBOX_ENV,
    "tools": _BROKER_TOOLS_ENV,
    "memory": _BROKER_MEMORY_ENV,
    "research": _BROKER_RESEARCH_ENV,
    "egress": _BROKER_EGRESS_ENV,
    "compute": _BROKER_COMPUTE_ENV,
    "capacity": _BROKER_CAPACITY_ENV,
}

_MODE_0 = frozenset({"", "0", "false", "no", "off"})
_MODE_1 = frozenset({"1", "true", "yes", "on"})
_MODE_2 = frozenset({"2", "broker-only", "broker_only"})


def _env_mode(name: str) -> FlagMode:
    raw = os.environ.get(name, "").strip().lower()
    if raw in _MODE_0:
        return 0
    if raw in _MODE_2:
        return 2
    if raw in _MODE_1:
        return 1
    return 0


def broker_only(domain: str) -> bool:
    env_name = _DOMAIN_ENV.get(domain.strip().lower())
    if env_name is None:
        raise ValueError(f"unknown peel domain: {domain!r}")
    return _env_mode(env_name) == 2


def broker_llm_enabled() -> bool:
    return _env_mode(_BROKER_LLM_ENV) in (1, 2)


def broker_llm_only() -> bool:
    return _env_mode(_BROKER_LLM_ENV) == 2


def broker_mcp_enabled() -> bool:
    return bool(os.environ.get(_BROKER_MCP_ENV, "").strip())


def broker_sandbox_enabled() -> bool:
    return _env_mode(_BROKER_SANDBOX_ENV) in (1, 2)


def broker_sandbox_only() -> bool:
    return _env_mode(_BROKER_SANDBOX_ENV) == 2


def broker_tools_enabled() -> bool:
    return _env_mode(_BROKER_TOOLS_ENV) in (1, 2)


def broker_tools_only() -> bool:
    return _env_mode(_BROKER_TOOLS_ENV) == 2


def broker_memory_enabled() -> bool:
    return _env_mode(_BROKER_MEMORY_ENV) in (1, 2)


def broker_memory_only() -> bool:
    return _env_mode(_BROKER_MEMORY_ENV) == 2


def broker_research_enabled() -> bool:
    return _env_mode(_BROKER_RESEARCH_ENV) in (1, 2)


def broker_research_only() -> bool:
    return _env_mode(_BROKER_RESEARCH_ENV) == 2


def broker_egress_enabled() -> bool:
    return _env_mode(_BROKER_EGRESS_ENV) in (1, 2)


def broker_egress_only() -> bool:
    return _env_mode(_BROKER_EGRESS_ENV) == 2


def broker_compute_enabled() -> bool:
    return _env_mode(_BROKER_COMPUTE_ENV) in (1, 2)


def broker_compute_only() -> bool:
    return _env_mode(_BROKER_COMPUTE_ENV) == 2


def broker_capacity_enabled() -> bool:
    return _env_mode(_BROKER_CAPACITY_ENV) in (1, 2)


def broker_capacity_only() -> bool:
    return _env_mode(_BROKER_CAPACITY_ENV) == 2


def select_llm_backend() -> LlmBackend:
    return "broker" if broker_llm_enabled() else "python"


def select_backend(domain: str) -> Backend:
    env_name = _DOMAIN_ENV.get(domain.strip().lower())
    if env_name is None:
        raise ValueError(f"unknown peel domain: {domain!r}")
    return "broker" if _env_mode(env_name) in (1, 2) else "python"

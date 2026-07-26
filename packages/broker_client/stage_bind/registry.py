from __future__ import annotations

from collections.abc import Callable
from typing import Any

from broker_client.client import BrokerClient
from broker_client.stage_bind.capacity import bind_capacity_probe
from broker_client.stage_bind.compute import bind_compute_work
from broker_client.stage_bind.llm import bind_llm_chat
from broker_client.stage_bind.memory import bind_memory_search
from broker_client.stage_bind.research import bind_egress_check, bind_research_fetch
from broker_client.stage_bind.sandbox import bind_sandbox_exec
from broker_client.stage_bind.tools import bind_tools_shell

BindFn = Callable[[BrokerClient | None], dict[str, Any]]

DOMAIN_BINDS: dict[str, BindFn] = {
    "llm": bind_llm_chat,
    "sandbox": bind_sandbox_exec,
    "tools": bind_tools_shell,
    "memory": bind_memory_search,
    "research": bind_research_fetch,
    "egress": bind_egress_check,
    "compute": bind_compute_work,
    "capacity": bind_capacity_probe,
}


def bind_plan(domain: str, client: BrokerClient | None = None) -> dict[str, Any]:
    key = domain.strip().lower()
    bind_fn = DOMAIN_BINDS.get(key)
    if bind_fn is None:
        raise ValueError(f"unknown peel domain: {domain!r}")
    return bind_fn(client)


def list_bind_domains() -> list[str]:
    """Sorted peel domains with registered bind helpers."""
    return sorted(DOMAIN_BINDS.keys())

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def integration_adapter_writer_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    env = payload.get("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER")
    if not isinstance(env, Mapping):
        return None
    if env.get("forces_off"):
        return (
            "Integration Adapter Writer env: **NIMBUSWARE_INTEGRATION_ADAPTER_WRITER** "
            "kill-switch active — workflow enable ignored."
        )
    if env.get("forces_on"):
        return (
            "Integration Adapter Writer env: **NIMBUSWARE_INTEGRATION_ADAPTER_WRITER** "
            "force-on — scaffold may activate when pipeline wiring lands."
        )
    if env.get("unset"):
        return (
            "Integration Adapter Writer env: unset — "
            "workflow ``integration_adapter_writer.enabled`` controls scaffold."
        )
    return None


def integration_adapter_writer_effective_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("effective_enabled") is True:
        block = payload.get("workflow_block")
        kind = ""
        if isinstance(block, Mapping):
            raw_kind = block.get("target_adapter_kind")
            if isinstance(raw_kind, str) and raw_kind.strip():
                kind = f" ({raw_kind.strip()})"
        return f"Integration Adapter Writer: **effective on**{kind}."
    return "Integration Adapter Writer: **off** (env or workflow gate)."

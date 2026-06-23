from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.env_captions import env_tri_state_gate_caption


def integration_adapter_writer_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    cap = env_tri_state_gate_caption(
        payload,
        "NIMBUSWARE_INTEGRATION_ADAPTER_WRITER",
        label="Integration Adapter Writer env",
        forces_off_text=(
            "Integration Adapter Writer env: **{env_key}** "
            "kill-switch active{detail} — workflow enable ignored."
        ),
        forces_on_text=(
            "Integration Adapter Writer env: **{env_key}** "
            "force-on{detail} — scaffold may activate when pipeline wiring lands."
        ),
        unset_text=(
            "Integration Adapter Writer env: unset — "
            "workflow ``integration_adapter_writer.enabled`` controls scaffold."
        ),
        unrecognised_text="",
    )
    return cap or None


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

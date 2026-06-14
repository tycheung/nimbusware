from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from nimbusware_env.env_flags import env_bool, env_str
from nimbusware_orchestrator.interaction_surface_map import discover_surfaces_combined
from nimbusware_orchestrator.ollama_chat import ollama_chat_json
from nimbusware_orchestrator.ui_flow_synthesis import validate_ui_flow_yaml


class _LlmUiFlowResponse(BaseModel):
    model_config = {"extra": "ignore"}

    flow: dict[str, Any] = Field(default_factory=dict)


def launch_test_llm_enabled() -> bool:
    if not env_bool("NIMBUSWARE_USE_LLM", default=False):
        return False
    return bool(launch_test_writer_model())


def launch_test_writer_model() -> str:
    return (
        env_str("NIMBUSWARE_LAUNCH_TEST_WRITER_MODEL") or env_str("NIMBUSWARE_DEFAULT_MODEL") or ""
    ).strip()


def launch_test_ollama_base_url() -> str:
    from nimbusware_env.env_flags import nimbusware_ollama_base_url

    return nimbusware_ollama_base_url()


def generate_llm_ui_flow_dict(
    workspace: Path,
    *,
    flow_id: str = "launch_draft",
    preview_base_url: str | None = None,
    critique_errors: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    model = launch_test_writer_model()
    if not model:
        return None
    ism = discover_surfaces_combined(workspace, preview_base_url=preview_base_url)
    surfaces = [{"kind": s.kind, "label": s.label, "path": s.path} for s in ism.surfaces[:20]]
    from nimbusware_orchestrator.launch_test_stage import build_launch_test_writer_prompt

    prompt = build_launch_test_writer_prompt(workspace)
    error_block = ""
    if critique_errors:
        error_block = "Critique errors to fix:\n" + "\n".join(f"- {e}" for e in critique_errors)
    user = json.dumps(
        {
            "flow_id": flow_id,
            "surfaces": surfaces,
            "critique_errors": list(critique_errors),
            "shape": {
                "id": flow_id,
                "label": "string",
                "steps": [
                    {
                        "kind": "goto|click|fill|expect_visible|expect_text|press",
                        "url": "optional for goto",
                        "value": "optional",
                        "locator": {
                            "strategy": "role|testid|label|text|css",
                            "role": "optional",
                            "name": "optional",
                            "value": "optional",
                        },
                    }
                ],
            },
        },
        indent=2,
    )
    try:
        raw = ollama_chat_json(
            base_url=launch_test_ollama_base_url(),
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"{error_block}\n\nWorkspace context:\n{user}"},
            ],
            timeout_seconds=90.0,
        )
        parsed = _LlmUiFlowResponse.model_validate(raw)
        flow = dict(parsed.flow)
        if not flow.get("id"):
            flow["id"] = flow_id
        errors = validate_ui_flow_yaml(flow)
        if errors:
            return None
        return flow
    except (ValidationError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return None

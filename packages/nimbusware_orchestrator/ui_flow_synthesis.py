"""Advisory UI flow synthesis from ISM interactive surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_orchestrator.interaction_surface_map import discover_surfaces_combined
from nimbusware_orchestrator.ui_flow_dsl import UiFlowDefinition, UiFlowStep, UiLocator


def synthesize_ui_flow_from_ism(
    workspace: Path,
    *,
    flow_id: str = "ism_draft",
    preview_base_url: str | None = None,
    max_steps: int = 12,
) -> UiFlowDefinition:
    ism = discover_surfaces_combined(workspace, preview_base_url=preview_base_url)
    steps: list[UiFlowStep] = [UiFlowStep(kind="goto", url="/")]
    for surface in ism.surfaces:
        if surface.kind == "button" and len(steps) < max_steps:
            steps.append(
                UiFlowStep(
                    kind="click",
                    locator=UiLocator(
                        strategy="role", role="button", name=surface.label or "button"
                    ),
                ),
            )
        elif surface.kind == "input" and len(steps) < max_steps:
            steps.append(
                UiFlowStep(
                    kind="fill",
                    locator=UiLocator(strategy="testid", value=surface.label or "input"),
                    value="smoke",
                ),
            )
    if len(steps) < max_steps:
        steps.append(
            UiFlowStep(kind="expect_visible", locator=UiLocator(strategy="css", value="body"))
        )
    return UiFlowDefinition(flow_id=flow_id, steps=steps, label="ISM draft flow")


def write_draft_ui_flow(workspace: Path, flow: UiFlowDefinition) -> Path:
    out_dir = workspace.resolve() / ".nimbusware" / "dev_env" / "ui_flows"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{flow.flow_id}.yaml"
    payload: dict[str, Any] = {
        "id": flow.flow_id,
        "label": flow.label,
        "steps": [],
    }
    for step in flow.steps:
        raw: dict[str, Any] = {"kind": step.kind}
        if step.url:
            raw["url"] = step.url
        if step.value:
            raw["value"] = step.value
        loc = step.effective_locator()
        loc_raw: dict[str, Any] = {"strategy": loc.strategy}
        if loc.value:
            loc_raw["value"] = loc.value
        if loc.role:
            loc_raw["role"] = loc.role
        if loc.name:
            loc_raw["name"] = loc.name
        raw["locator"] = loc_raw
        payload["steps"].append(raw)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def validate_ui_flow_yaml(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not raw.get("id"):
        errors.append("missing id")
    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be non-empty list")
        return errors
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"step {idx} must be mapping")
            continue
        if not step.get("kind") and not step.get("action"):
            errors.append(f"step {idx} missing kind")
    return errors

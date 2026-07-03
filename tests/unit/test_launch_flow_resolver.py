from __future__ import annotations

from pathlib import Path

from orchestrator.launch.launch_flow_resolver import (
    load_catalog_ui_flow,
    match_ui_flow_id,
    resolve_launch_flows,
    resolve_ui_flow,
)


def test_match_ui_flow_id_companion_convention() -> None:
    assert match_ui_flow_id("", http_flow_id="todo_api") == "todo_api_ui"


def test_load_catalog_ui_flow_todo() -> None:
    flow = load_catalog_ui_flow("todo_api_ui")
    assert flow.flow_id == "todo_api_ui"
    assert any(s.kind == "click" for s in flow.steps)


def test_resolve_ui_flow_workspace_override(tmp_path: Path) -> None:
    flows_dir = tmp_path / ".nimbusware" / "dev_env" / "ui_flows"
    flows_dir.mkdir(parents=True)
    (flows_dir / "custom.yaml").write_text(
        "id: custom\nsteps:\n  - kind: goto\n    url: /\n",
        encoding="utf-8",
    )
    flow, source = resolve_ui_flow(tmp_path, flow_id="custom")
    assert flow is not None
    assert flow.flow_id == "custom"
    assert source == "workspace"


def test_resolve_launch_flows_from_prompt_id() -> None:
    rows = [{"metadata": {"prompt_id": "todo_api", "business_prompt": "todo app"}}]
    resolved = resolve_launch_flows(rows, Path("."))
    assert resolved.http_flow_id == "todo_api"
    assert resolved.ui_flow_id == "todo_api_ui"
    assert resolved.ui_flow is not None

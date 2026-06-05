"""Integration Adapter Writer workflow scaffold."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.integration_adapter_writer_explainer import (
    integration_adapter_writer_env_gate_caption,
    integration_adapter_writer_fleet_manifest_count,
    integration_adapter_writer_workflow_explainer_operator_metrics,
    integration_adapter_writer_workflow_explainer_operator_metrics_caption,
    integration_adapter_writer_workflow_explainer_payload,
)
from nimbusware_orchestrator.workflow_integration_adapter_writer import (
    DEFAULT_ADAPTER_KIND,
    integration_adapter_writer_effective,
    parse_integration_adapter_writer_workflow_block,
)


def _write_profile(tmp_path: Path, name: str, body: str) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_parse_integration_adapter_writer_defaults() -> None:
    block = parse_integration_adapter_writer_workflow_block(Path("/nonexistent"), None)
    assert block.enabled is False
    assert block.target_adapter_kind == DEFAULT_ADAPTER_KIND
    assert block.stub_only is True


def test_parse_integration_adapter_writer_profile(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "adapter_on",
        """version: 1
integration_adapter_writer:
  enabled: true
  target_adapter_kind: api_bridge
  stub_only: false
""",
    )
    block = parse_integration_adapter_writer_workflow_block(tmp_path, "adapter_on")
    assert block.enabled is True
    assert block.target_adapter_kind == "api_bridge"
    assert block.stub_only is False


def test_integration_adapter_writer_effective_env_kill_switch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_profile(
        tmp_path,
        "adapter_on",
        "integration_adapter_writer:\n  enabled: true\n",
    )
    block = parse_integration_adapter_writer_workflow_block(tmp_path, "adapter_on")
    monkeypatch.setenv("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER", "0")
    assert integration_adapter_writer_effective(block) is False


def test_integration_adapter_writer_explainer_payload(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "adapter_on",
        """integration_adapter_writer:
  enabled: true
  target_adapter_kind: compatibility_shim
""",
    )
    payload = integration_adapter_writer_workflow_explainer_payload(tmp_path, "adapter_on")
    assert payload["effective_enabled"] is True
    assert payload["workflow_block"]["target_adapter_kind"] == "compatibility_shim"
    m = integration_adapter_writer_workflow_explainer_operator_metrics(payload)
    assert m["workflow_yaml_path_present"] is True


def test_integration_adapter_writer_fleet_manifest_count(tmp_path: Path) -> None:
    run_dir = tmp_path / ".nimbusware" / "integration_adapter_writer" / "run-a"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    assert integration_adapter_writer_fleet_manifest_count(tmp_path) == 1


def test_integration_adapter_writer_explainer_operator_metrics() -> None:
    payload = {
        "workflow_block": {
            "enabled": True,
            "stub_only": True,
            "target_adapter_kind": "compatibility_shim",
        },
        "effective_enabled": True,
    }
    m = integration_adapter_writer_workflow_explainer_operator_metrics(payload)
    assert m["effective_enabled"] is True
    assert m["stub_only"] is True
    assert m.get("live_path_active") is not True
    assert m.get("would_emit_stage_started") is not True
    cap = integration_adapter_writer_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "enabled" in cap
    assert "stub-only" in cap


def test_integration_adapter_writer_explainer_operator_metrics_live() -> None:
    payload = {
        "workflow_block": {
            "enabled": True,
            "stub_only": False,
            "target_adapter_kind": "api_bridge",
        },
        "effective_enabled": True,
        "would_emit_stage_started": True,
        "scaffold_status": "live_adapter_recorded",
    }
    m = integration_adapter_writer_workflow_explainer_operator_metrics(payload)
    assert m["live_path_active"] is True
    assert m["scaffold_status"] == "live_adapter_recorded"
    assert m["would_emit_stage_started"] is True
    cap = integration_adapter_writer_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "live path (metadata recorded)" in cap
    assert "live ``stage.started``" in cap


def test_integration_adapter_writer_env_gate_caption() -> None:
    cap = integration_adapter_writer_env_gate_caption(
        {
            "NIMBUSWARE_INTEGRATION_ADAPTER_WRITER": {
                "forces_on": True,
                "raw": "1",
            },
        },
    )
    assert cap is not None
    assert "force-on" in cap


def test_integration_adapter_writer_effective_caption() -> None:
    from nimbusware_console.integration_adapter_writer_explainer import (
        integration_adapter_writer_effective_caption,
    )

    cap_on = integration_adapter_writer_effective_caption(
        {
            "effective_enabled": True,
            "workflow_block": {"target_adapter_kind": "api_bridge"},
        },
    )
    assert cap_on is not None
    assert "effective on" in cap_on
    cap_off = integration_adapter_writer_effective_caption({"effective_enabled": False})
    assert cap_off is not None
    assert "off" in cap_off

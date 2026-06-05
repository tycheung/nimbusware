"""Integration adapter scaffold manifest validation and rollback."""

from __future__ import annotations

import json
from pathlib import Path

from hermes_orchestrator.integration_adapter_scaffold import (
    execute_target_adapter_integration,
    validate_integration_manifest,
)


def test_validate_integration_manifest_rejects_stub_only() -> None:
    errs = validate_integration_manifest(
        {
            "run_id": "r1",
            "target_adapter_kind": "api_bridge",
            "stub_only": True,
        },
    )
    assert any("stub_only" in e for e in errs)


def test_execute_target_adapter_integration_manifest_invalid(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text("{not-json", encoding="utf-8")
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "manifest_invalid"


def test_execute_target_adapter_integration_manifest_rejected(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "r1",
                "target_adapter_kind": "api_bridge",
                "stub_only": True,
            },
        ),
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "manifest_rejected"
    assert out.get("validation_errors")


def test_execute_target_adapter_integration_rolled_back_on_sync_error(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps({"run_id": "r1", "target_adapter_kind": "api_bridge", "stub_only": False}),
        encoding="utf-8",
    )
    (ws / "target_state.json").write_text('{"connected": true, "prior": 1}\n', encoding="utf-8")
    (ws / "adapter_api_bridge.py").write_text(
        """
class ApiBridgeAdapter:
    kind = "api_bridge"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
    def connect(self):
        return True
    def sync_target(self):
        raise RuntimeError("sync failed")
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "rolled_back"
    assert "sync failed" in str(out.get("rollback_reason", ""))
    restored = json.loads((ws / "target_state.json").read_text(encoding="utf-8"))
    assert restored.get("prior") == 1


def test_execute_target_adapter_integration_rolled_back_on_connect_fail(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps({"run_id": "r1", "target_adapter_kind": "custom", "stub_only": False}),
        encoding="utf-8",
    )
    (ws / "adapter_custom.py").write_text(
        """
class CustomAdapter:
    kind = "custom"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
    def connect(self):
        return False
    def sync_target(self):
        path = self._workspace_dir / "target_state.json"
        path.write_text('{"connected": false}', encoding="utf-8")
        return {"ok": True}
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="custom", run_id="r1")
    assert out["target_integration_status"] == "rolled_back"
    assert out.get("rollback_reason") == "connect_failed_after_sync"

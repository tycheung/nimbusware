"""Workspace snapshot roundtrip."""

from __future__ import annotations

from pathlib import Path

from nimbusware_maker.workspace_snapshot import create_workspace_snapshot, restore_workspace_snapshot


def test_snapshot_roundtrip(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    target = ws / "app.py"
    target.write_text("v1\n", encoding="utf-8")
    snap = create_workspace_snapshot(ws, run_id="run-1", label="slice-1", paths=["app.py"])
    target.write_text("v2\n", encoding="utf-8")
    restored = restore_workspace_snapshot(ws, snap)
    assert restored == ["app.py"]
    assert target.read_text(encoding="utf-8") == "v1\n"

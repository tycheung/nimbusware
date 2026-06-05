"""Nimbusware-generated integration adapter (api_bridge).

Run: a26c2dd8-c3e7-49dc-a5f8-0507aaca1aa2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ApiBridgeAdapter:
    """Target adapter for ``api_bridge`` (generated)."""

    kind: str = "api_bridge"

    def __init__(self, workspace_dir: Path, *, run_id: str) -> None:
        self._workspace_dir = workspace_dir
        self._run_id = run_id

    def connect(self) -> bool:
        state_path = self._workspace_dir / "target_state.json"
        if not state_path.is_file():
            return False
        try:
            raw = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return raw.get("connected") is True

    def describe(self) -> dict[str, Any]:
        return {"kind": self.kind, "run_id": self._run_id}

    def sync_target(self) -> dict[str, Any]:
        """Perform target-specific integration I/O (local workspace)."""
        state_path = self._workspace_dir / "target_state.json"
        payload = {
            "connected": True,
            "action": "probe",
            "endpoint": "http://127.0.0.1:8080/health",
        }
        state_path.write_text(__import__('json').dumps(payload, indent=2), encoding='utf-8')
        return payload


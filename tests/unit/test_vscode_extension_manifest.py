from __future__ import annotations

import json
from pathlib import Path

_EXT = Path(__file__).resolve().parents[2] / "extensions" / "nimbusware-status" / "package.json"


def test_nimbusware_status_extension_manifest() -> None:
    data = json.loads(_EXT.read_text(encoding="utf-8"))
    assert data["name"] == "nimbusware-status"
    assert data["publisher"] == "nimbusware"
    assert data.get("repository", {}).get("url")
    assert data.get("license")
    assert "nimbusware.openMakerProgress" in {
        c["command"] for c in data.get("contributes", {}).get("commands", [])
    }
    commands = {c["command"] for c in data.get("contributes", {}).get("commands", [])}
    assert "nimbusware.showScopeCard" in commands
    assert "nimbusware.previewDisciplineRoutes" in commands
    assert "nimbusware.openDeployLinks" in commands
    props = data.get("contributes", {}).get("configuration", {}).get("properties", {})
    assert "nimbusware.activeRunId" in props
    assert "nimbusware.apiBase" in props
    assert "nimbusware.soloDiscipline" in props
    scripts = data.get("scripts", {})
    assert "package" in scripts
    assert "publish:marketplace" in scripts

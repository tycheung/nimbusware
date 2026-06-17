from __future__ import annotations

from pathlib import Path

from nimbusware_config.model_bindings_store import list_binding_role_catalog, load_defaults_file

REPO = Path(__file__).resolve().parents[2]


def test_load_defaults_file() -> None:
    doc = load_defaults_file(REPO)
    assert doc.get("version") == 1
    assert "planner" in (doc.get("roles") or {})


def test_role_catalog_includes_planner() -> None:
    roles = list_binding_role_catalog(REPO)
    assert any(r["agent_role"] == "planner" for r in roles)

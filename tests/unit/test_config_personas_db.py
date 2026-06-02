"""Persona API + orchestrator paths in Postgres config mode (in-memory store)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
import yaml
from fastapi.testclient import TestClient

from hermes_orchestrator.persona_shelf_promotion import try_auto_promote_probation_persona
from hermes_store.memory import InMemoryEventStore
from nimbusware_api.app import app
from nimbusware_api.deps import get_orchestrator, get_store
from nimbusware_config.keys import KEY_PERSONA_SHELVES, NS_PERSONAS
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.store import InMemoryConfigStore


@pytest.fixture
def persona_db_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, ConfigMaterializer]:
    shelves = {
        "version": 1,
        "business_area": [
            {
                "id": "commerce",
                "display_name": "Commerce",
                "version": 1,
                "probation_status": "probation",
            },
        ],
        "development_role": [{"id": "be", "display_name": "BE", "version": 1}],
    }
    personas_dir = tmp_path / "configs" / "personas"
    personas_dir.mkdir(parents=True)
    shelves_path = personas_dir / "shelves.yaml"
    shelves_path.write_text(yaml.safe_dump(shelves, sort_keys=False), encoding="utf-8")

    store = InMemoryConfigStore()
    store.upsert(NS_PERSONAS, KEY_PERSONA_SHELVES, shelves)
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    monkeypatch.setenv("NIMBUSWARE_CONFIG_FROM_DB", "1")
    monkeypatch.setenv(
        "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
    )
    monkeypatch.delenv("NIMBUSWARE_CONFIG_FROM_FILES", raising=False)
    return tmp_path, mat


def test_persona_patch_db_mode_no_yaml_write(
    persona_db_env: tuple[Path, ConfigMaterializer],
) -> None:
    tmp_path, mat = persona_db_env
    shelves_path = tmp_path / "configs" / "personas" / "shelves.yaml"
    mtime_before = shelves_path.stat().st_mtime

    class _Orch:
        def __init__(self) -> None:
            self.repo_root = tmp_path
            self.config_materializer = mat

    mem = InMemoryEventStore()
    app.dependency_overrides[get_orchestrator] = lambda: _Orch()
    app.dependency_overrides[get_store] = lambda: mem
    try:
        with patch("nimbusware_config.persist.atomic_write_yaml") as mock_write:
            with TestClient(app) as c:
                r = c.patch(
                    "/v1/personas/business_area/commerce",
                    json={
                        "expected_version": 1,
                        "instructions": "DB mode patch.",
                        "actor": "tester",
                    },
                    headers={
                        "X-Nimbusware-Admin-Token": os.environ.get(
                            "NIMBUSWARE_ADMIN_TOKEN",
                            "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD",
                        ),
                    },
                )
                assert r.status_code == 200, r.text
                mock_write.assert_not_called()

            assert shelves_path.stat().st_mtime == mtime_before
            row = mat.store.get(NS_PERSONAS, KEY_PERSONA_SHELVES)
            assert row is not None
            entry = next(e for e in row.content["business_area"] if e["id"] == "commerce")
            assert entry["instructions"] == "DB mode patch."
            assert entry["version"] == 2
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)


def test_auto_promote_uses_db_not_yaml(persona_db_env: tuple[Path, ConfigMaterializer]) -> None:
    tmp_path, mat = persona_db_env
    shelves_path = tmp_path / "configs" / "personas" / "shelves.yaml"
    mtime_before = shelves_path.stat().st_mtime
    mem = InMemoryEventStore()
    run_id = uuid4()

    with patch("nimbusware_config.persist.atomic_write_yaml") as mock_write:
        meta = try_auto_promote_probation_persona(
            tmp_path,
            mem,
            persona_id="commerce",
            run_id=run_id,
            config_materializer=mat,
        )
        mock_write.assert_not_called()

    assert meta.get("auto_promote_probation_applied") is True
    assert shelves_path.stat().st_mtime == mtime_before
    row = mat.store.get(NS_PERSONAS, KEY_PERSONA_SHELVES)
    assert row is not None
    entry = next(e for e in row.content["business_area"] if e["id"] == "commerce")
    assert entry.get("probation_status") == "promoted"

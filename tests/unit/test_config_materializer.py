"""Unit tests for ``ConfigMaterializer``."""

from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path

import pytest

from nimbusware_config.keys import KEY_PERSONA_SHELVES, NS_PERSONAS
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.store import InMemoryConfigStore
from hermes_orchestrator.merge import load_yaml


def test_materializer_file_fallback_matches_disk(repo_root: Path) -> None:
    mat = ConfigMaterializer(repo_root, use_db=False)
    shelf = mat.get_persona_shelf()
    disk = load_yaml(repo_root / "configs" / "personas" / "shelves.yaml")
    assert shelf.raw == disk


def test_materializer_cache_stable_until_refresh(repo_root: Path) -> None:
    store = InMemoryConfigStore()
    store.upsert(
        NS_PERSONAS,
        KEY_PERSONA_SHELVES,
        {
            "version": 1,
            "business_area": [{"id": "a", "display_name": "A", "version": 1}],
            "development_role": [{"id": "b", "display_name": "B", "version": 1}],
        },
    )
    mat = ConfigMaterializer(repo_root, store=store, use_db=True)
    gen0 = mat.generation
    a = mat.get_persona_shelf()
    b = mat.get_persona_shelf()
    assert mat.generation == gen0
    assert a.raw == b.raw

    store.upsert(
        NS_PERSONAS,
        KEY_PERSONA_SHELVES,
        {
            "version": 1,
            "business_area": [{"id": "x", "display_name": "X", "version": 1}],
            "development_role": [{"id": "b", "display_name": "B", "version": 1}],
        },
    )
    mat.refresh(NS_PERSONAS)
    c = mat.get_persona_shelf()
    assert "x" in c.all_persona_ids()


def test_materializer_upsert_content_updates_cache(repo_root: Path) -> None:
    store = InMemoryConfigStore()
    mat = ConfigMaterializer(repo_root, store=store, use_db=True)
    content = {
        "version": 1,
        "business_area": [{"id": "db_only", "display_name": "DB", "version": 1}],
        "development_role": [{"id": "b", "display_name": "B", "version": 1}],
    }
    ver = mat.upsert_content(NS_PERSONAS, KEY_PERSONA_SHELVES, content)
    assert ver >= 1
    assert "db_only" in mat.get_persona_shelf().all_persona_ids()


def test_materializer_upsert_requires_db_mode(repo_root: Path) -> None:
    mat = ConfigMaterializer(repo_root, use_db=False)
    with pytest.raises(RuntimeError, match="Postgres"):
        mat.upsert_content(NS_PERSONAS, KEY_PERSONA_SHELVES, {"version": 1})


@pytest.fixture
def repo_root() -> Path:
    return find_repo_root(start=Path(__file__).resolve().parents[1])

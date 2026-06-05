from __future__ import annotations

import os
from pathlib import Path

import pytest

from nimbusware_extensions.personas import PersonaShelf
from nimbusware_config.keys import KEY_PERSONA_SHELVES, NS_PERSONAS
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import PostgresConfigStore
from nimbusware_env import find_repo_root

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_seed_personas_round_trip_matches_file_shape() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[2])
    url = _url()
    store = PostgresConfigStore(url)
    seed_config_from_repo(repo, store)
    row = store.get(NS_PERSONAS, KEY_PERSONA_SHELVES)
    assert row is not None
    file_shelf = PersonaShelf(repo / "configs" / "personas" / "shelves.yaml")
    assert row.content == file_shelf.raw

    mat = ConfigMaterializer(repo, store=store, use_db=True)
    assert mat.get_persona_shelf().raw == file_shelf.raw

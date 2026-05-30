"""Postgres-backed config CLI integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nimbusware_config.export import export_config_to_repo
from nimbusware_config.keys import KEY_PERSONA_SHELVES, NS_PERSONAS
from nimbusware_config.seed import seed_config_from_repo
from hermes_orchestrator.merge import load_yaml
from nimbusware_env import find_repo_root


@pytest.mark.integration
def test_postgres_seed_export_personas_round_trip() -> None:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not url:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")

    from nimbusware_config.store import PostgresConfigStore

    repo = find_repo_root(start=Path(__file__).resolve().parents[2])
    store = PostgresConfigStore(url)
    seed_config_from_repo(repo, store)

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        export_config_to_repo(store, out, namespaces={NS_PERSONAS})
        path = out / "configs" / "personas" / "shelves.yaml"
        assert path.is_file()
        row = store.get(NS_PERSONAS, KEY_PERSONA_SHELVES)
        assert row is not None
        assert load_yaml(path) == row.content

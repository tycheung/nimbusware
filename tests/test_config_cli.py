"""Tests for ``hermes-config`` gitops CLI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hermes_config.cli import main
from hermes_config.export import export_config_to_repo
from hermes_config.keys import KEY_PERSONA_SHELVES, NS_PERSONAS, NS_WORKFLOWS
from hermes_config.seed import preview_seed_from_repo, seed_config_from_repo
from hermes_config.store import InMemoryConfigStore
from hermes_orchestrator.merge import load_yaml

pytestmark_integration = pytest.mark.integration


def test_seed_export_round_trip_in_memory(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    store = InMemoryConfigStore()
    seed_config_from_repo(repo, store)
    export_root = tmp_path / "exported"
    export_root.mkdir()
    counts = export_config_to_repo(store, export_root)
    assert counts.get(NS_PERSONAS, 0) >= 1
    assert counts.get(NS_WORKFLOWS, 0) >= 1

    shelves = load_yaml(export_root / "configs" / "personas" / "shelves.yaml")
    row = store.get(NS_PERSONAS, KEY_PERSONA_SHELVES)
    assert row is not None
    assert shelves == row.content

    default_row = store.get(NS_WORKFLOWS, "default")
    if default_row is not None:
        exported_wf = load_yaml(export_root / "configs" / "workflows" / "default.yaml")
        assert exported_wf == default_row.content


def test_import_dry_run_does_not_mutate_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("HERMES_DATABASE_URL", "postgresql://unused")
    monkeypatch.setenv("HERMES_REPO_ROOT", str(repo))

    preview_before = preview_seed_from_repo(repo)
    assert preview_before

    import hermes_config.cli as cli_mod

    original = cli_mod.PostgresConfigStore

    captured: dict[str, int] = {"upsert_calls": 0}

    class _CapturingStore(InMemoryConfigStore):
        def upsert(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            captured["upsert_calls"] += 1
            return super().upsert(*args, **kwargs)

    monkeypatch.setattr(cli_mod, "PostgresConfigStore", lambda _url: _CapturingStore())

    rc = main(["--repo-root", str(repo), "import", "--dry-run"])
    assert rc == 0
    assert captured["upsert_calls"] == 0

    monkeypatch.setattr(cli_mod, "PostgresConfigStore", original)


def test_preview_seed_lists_workflow_profiles() -> None:
    repo = Path(__file__).resolve().parents[1]
    preview = preview_seed_from_repo(repo, namespaces={NS_WORKFLOWS})
    keys = {p["document_key"] for p in preview}
    assert "default" in keys


@pytest.mark.integration
def test_postgres_seed_export_personas_round_trip() -> None:
    url = os.environ.get("HERMES_DATABASE_URL")
    if not url:
        pytest.skip("HERMES_DATABASE_URL not set")

    from hermes_config.store import PostgresConfigStore

    repo = Path(__file__).resolve().parents[1]
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

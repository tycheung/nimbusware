from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from maker.store import InMemoryProjectStore


def test_create_attach_project_requires_existing_dir(tmp_path: Path) -> None:
    store = InMemoryProjectStore()
    ws = tmp_path / "app"
    ws.mkdir()
    record = store.create(name="Demo", workspace_path=str(ws), template="attach")
    assert record.name == "Demo"
    assert Path(record.workspace_path).is_dir()


def test_create_attach_rejects_missing_dir(tmp_path: Path) -> None:
    store = InMemoryProjectStore()
    with pytest.raises(ValueError, match="not a directory"):
        store.create(name="Demo", workspace_path=str(tmp_path / "missing"), template="attach")


def test_create_greenfield_makes_directory(tmp_path: Path) -> None:
    store = InMemoryProjectStore()
    ws = tmp_path / "new-app"
    record = store.create(name="New", workspace_path=str(ws), template="greenfield")
    assert Path(record.workspace_path).is_dir()
    assert record.template == "greenfield"


def test_get_list_delete_roundtrip(tmp_path: Path) -> None:
    store = InMemoryProjectStore()
    ws = tmp_path / "app"
    ws.mkdir()
    created = store.create(name="One", workspace_path=str(ws))
    assert store.get(created.project_id) is not None
    assert len(store.list()) == 1
    assert store.delete(created.project_id) is True
    assert store.get(created.project_id) is None
    assert store.delete(uuid4()) is False

from __future__ import annotations

from pathlib import Path

from config.collab_settings_store import (
    load_persisted_collab_enabled,
    save_persisted_collab_enabled,
)


def test_collab_settings_persist_round_trip(tmp_path: Path) -> None:
    assert load_persisted_collab_enabled(tmp_path) is None
    save_persisted_collab_enabled(True, repo_root=tmp_path)
    assert load_persisted_collab_enabled(tmp_path) is True
    save_persisted_collab_enabled(False, repo_root=tmp_path)
    assert load_persisted_collab_enabled(tmp_path) is False

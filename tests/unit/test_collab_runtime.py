from __future__ import annotations

import pytest

from env.collab_runtime import (
    clear_runtime_collab_override,
    collab_settings_snapshot,
    runtime_collab_override,
    set_runtime_collab_enabled,
)


def test_collab_runtime_override_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "0")
    clear_runtime_collab_override()
    assert runtime_collab_override() is None
    assert collab_settings_snapshot()["collab_enabled"] is False
    assert collab_settings_snapshot()["source"] == "env"

    set_runtime_collab_enabled(True)
    assert runtime_collab_override() is True
    snap = collab_settings_snapshot()
    assert snap["collab_enabled"] is True
    assert snap["source"] == "runtime"

    clear_runtime_collab_override()
    assert runtime_collab_override() is None

from __future__ import annotations

from pathlib import Path

from nimbusware_config.collab_policy_store import load_collab_policy, save_collab_policy


def test_load_collab_policy_defaults_when_missing(tmp_path: Path) -> None:
    doc = load_collab_policy(tmp_path)
    assert doc["version"] == 1
    assert doc["allow_external_collaborators"] is False
    assert doc["max_session_participants"] == 20


def test_save_and_reload_collab_policy(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "allow_external_collaborators": True,
        "max_session_participants": 8,
        "host_transfer_consent_hours": 12,
        "default_invite_role": "session_write",
        "write_may_start_runs": True,
    }
    save_collab_policy(tmp_path, payload)
    loaded = load_collab_policy(tmp_path)
    assert loaded["max_session_participants"] == 8
    assert loaded["write_may_start_runs"] is True

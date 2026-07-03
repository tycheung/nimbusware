from __future__ import annotations

from uuid import uuid4

import pytest

from maker.collab_policy_enforcement import (
    CollabPolicyViolation,
    assert_link_join_allowed,
    assert_participant_capacity,
    effective_collab_policy,
    external_collaborators_allowed,
    max_session_participants,
)


class _FakeCollab:
    def __init__(self, count: int) -> None:
        self._count = count

    def list_participants(self, _session_id: object) -> list[object]:
        return [object()] * self._count


def test_effective_collab_policy_merges_repo_defaults(tmp_path, monkeypatch) -> None:
    policy = tmp_path / "configs" / "collab_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        "version: 1\nallow_external_collaborators: false\nmax_session_participants: 4\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "maker.collab_policy_enforcement.find_repo_root",
        lambda: tmp_path,
    )
    doc = effective_collab_policy(None)
    assert doc["max_session_participants"] == 4
    assert external_collaborators_allowed(None) is False
    assert max_session_participants(None) == 4


def test_assert_link_join_allowed_blocks_when_disabled(tmp_path, monkeypatch) -> None:
    policy = tmp_path / "configs" / "collab_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("version: 1\nallow_external_collaborators: false\n", encoding="utf-8")
    monkeypatch.setenv("NIMBUSWARE_SETUP_BUNDLE", "enterprise")
    monkeypatch.setattr(
        "maker.collab_policy_enforcement.find_repo_root",
        lambda: tmp_path,
    )
    with pytest.raises(CollabPolicyViolation, match="external collaborators disabled"):
        assert_link_join_allowed(tenant_slug=None)


def test_assert_link_join_allowed_skips_on_individual_bundle(tmp_path, monkeypatch) -> None:
    policy = tmp_path / "configs" / "collab_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("version: 1\nallow_external_collaborators: false\n", encoding="utf-8")
    monkeypatch.setenv("NIMBUSWARE_SETUP_BUNDLE", "default")
    monkeypatch.setattr(
        "maker.collab_policy_enforcement.find_repo_root",
        lambda: tmp_path,
    )
    result = assert_link_join_allowed(tenant_slug=None)
    assert result is None


def test_assert_participant_capacity_enforces_limit(tmp_path, monkeypatch) -> None:
    policy = tmp_path / "configs" / "collab_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("version: 1\nmax_session_participants: 4\n", encoding="utf-8")
    monkeypatch.setattr(
        "maker.collab_policy_enforcement.find_repo_root",
        lambda: tmp_path,
    )
    session_id = uuid4()
    store = _FakeCollab(4)
    with pytest.raises(CollabPolicyViolation, match="participant limit"):
        assert_participant_capacity(store, session_id, tenant_slug=None, user_id=uuid4())

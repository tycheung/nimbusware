from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.collab_binding_resolver import (
    merge_participant_memory_policy,
    participant_memory_policy,
)
from nimbusware_orchestrator.fleet_policies import (
    FleetCommitPolicy,
    load_fleet_commit_policies,
    save_fleet_commit_policies,
    tenant_commit_policy,
)
from nimbusware_orchestrator.user_operator_profiles import (
    load_user_operator_profiles,
    save_user_operator_profiles,
)


def test_participant_memory_policy_merge() -> None:
    meta = merge_participant_memory_policy(
        {},
        user_id="alice",
        policy={"private": True, "project_shared": False},
    )
    pol = participant_memory_policy(meta, "alice")
    assert pol["private"] is True
    assert pol["project_shared"] is False


def test_fleet_commit_policy_round_trip(tmp_path: Path) -> None:
    policies = {
        "ops": FleetCommitPolicy(
            tenant_slug="ops",
            require_auto_commit=True,
            message_regex="^slice:",
        ),
    }
    save_fleet_commit_policies(policies, repo_root=tmp_path)
    loaded = load_fleet_commit_policies(tmp_path)
    assert loaded["ops"].require_auto_commit is True
    assert tenant_commit_policy("ops", repo_root=tmp_path).message_regex == "^slice:"


def test_user_operator_profiles_round_trip(tmp_path: Path) -> None:
    save_user_operator_profiles(
        "alice",
        autopilot_profile_id="guided",
        enforcement_profile_id="balanced",
        repo_root=tmp_path,
    )
    profiles = load_user_operator_profiles("alice", repo_root=tmp_path)
    assert profiles["autopilot_profile_id"] == "guided"
    assert profiles["enforcement_profile_id"] == "balanced"

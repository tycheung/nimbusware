from __future__ import annotations

from orchestrator.fleet_policies import (
    FleetStackPolicy,
    load_fleet_stack_policies,
    save_fleet_stack_policies,
    tenant_stack_policy,
)
from orchestrator.fleet_policy_guards import apply_regulated_stack_guard


def test_fleet_stack_policies_round_trip(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_stack_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("version: 1\ntenants:\n  default:\n    allowed_stacks: {}\n", encoding="utf-8")
    policies = load_fleet_stack_policies(tmp_path)
    policies["regulated"] = FleetStackPolicy(
        tenant_slug="regulated",
        allowed_stacks={"api": "fastapi_python", "web": "react_vite"},
    )
    save_fleet_stack_policies(policies, repo_root=tmp_path)
    reloaded = load_fleet_stack_policies(tmp_path)
    assert reloaded["regulated"].allowed_stacks["api"] == "fastapi_python"


def test_apply_regulated_stack_guard_clamps_disallowed_stack(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_stack_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  regulated:\n    allowed_stacks:\n      api: fastapi_python\n      web: react_vite\n",
        encoding="utf-8",
    )
    manifest = {
        "surfaces": ["api", "web"],
        "stacks": {"api": "node_express", "web": "react_vite"},
    }
    guarded = apply_regulated_stack_guard(manifest, "regulated", repo_root=tmp_path)
    assert guarded["stacks"]["api"] == "fastapi_python"
    assert guarded["regulated_stack_guard"]["clamps"] == ["api:node_express->fastapi_python"]


def test_tenant_stack_policy_unrestricted_by_default(tmp_path) -> None:
    policy = tenant_stack_policy("unknown", repo_root=tmp_path)
    assert policy.restricts_stacks() is False

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from hermes_orchestrator.merge import merge_policy_snapshot, policy_snapshot_from_files


def test_merge_budget_minimum() -> None:
    base = {"network_egress": {"budget_bytes_per_run": 1000}}
    wf = {"network_egress": {"budget_bytes_per_run": 500}}
    snap = merge_policy_snapshot(base, wf, None)
    assert snap.network_egress.budget_bytes_per_run == 500


def test_merge_list_union_dedupe() -> None:
    u1 = "11111111-1111-4111-8111-111111111101"
    u2 = "22222222-2222-4222-8222-222222222202"
    base = {"network_egress": {"scraper_role_allowlist": [u1]}}
    wf = {"network_egress": {"scraper_role_allowlist": [u2, u1]}}
    snap = merge_policy_snapshot(base, wf, None)
    roles = set(snap.network_egress.scraper_role_allowlist)
    assert roles == {UUID(u1), UUID(u2)}


def test_merge_explicit_empty_wipes() -> None:
    u1 = "11111111-1111-4111-8111-111111111101"
    base = {"network_egress": {"scraper_role_allowlist": [u1]}}
    wf = {"network_egress": {"scraper_role_allowlist": []}}
    run = {"network_egress": {"scraper_role_allowlist": [u1]}}
    snap = merge_policy_snapshot(base, wf, run)
    assert snap.network_egress.scraper_role_allowlist == [UUID(u1)]


def test_domain_allowlist_normalized_to_lower() -> None:
    base = {"network_egress": {"domain_allowlist": ["Example.COM", ".PYPI.org"]}}
    snap = merge_policy_snapshot(base, None, None)
    assert snap.network_egress.domain_allowlist == ["example.com", ".pypi.org"]


def test_policy_snapshot_from_files() -> None:
    root = Path(__file__).resolve().parents[1]
    snap = policy_snapshot_from_files(
        root / "configs" / "model-routing.yaml",
        root / "configs" / "workflows" / "default.yaml",
    )
    assert snap.finding_fix_strictness.minimum_severity_requiring_fixes.value == "MEDIUM"

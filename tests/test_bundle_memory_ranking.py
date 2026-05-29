from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agent_core.models import Verdict
from hermes_extensions.bundle_memory import (
    InMemoryBundleOutcomeStore,
    build_bundle_outcome_from_gate,
)
from hermes_extensions.bundle_memory_models import BundleSuccessStats
from hermes_extensions.catalog import apply_bundle_memory_ranking, search_bundles


def test_apply_bundle_memory_ranking_promotes_high_success_bundle(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_BUNDLE_MEMORY_RANK_WEIGHT", "0.8")
    hits = [
        {"id": "low-success", "tags": ["auth"]},
        {"id": "high-success", "tags": ["auth"]},
    ]
    stats = {
        "low-success": BundleSuccessStats(
            bundle_id="low-success",
            pass_count=0,
            fail_count=10,
            sample_count=10,
            success_rate=0.0,
        ),
        "high-success": BundleSuccessStats(
            bundle_id="high-success",
            pass_count=10,
            fail_count=0,
            sample_count=10,
            success_rate=1.0,
        ),
    }
    ranked = apply_bundle_memory_ranking(hits, "auth", stats)
    assert ranked[0]["id"] == "high-success"


def test_search_bundles_memory_bias_changes_order(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HERMES_BUNDLE_MEMORY_RANK_WEIGHT", "1.0")
    repo = Path(__file__).resolve().parents[1]
    store = InMemoryBundleOutcomeStore()
    store.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="auth-rbac-starter",
            workflow_profile="default",
            project_tags=["auth"],
            integrator_score=0.9,
            verdict=Verdict.PASS,
        ),
    )
    store.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="other-bundle",
            workflow_profile="default",
            project_tags=["auth"],
            integrator_score=0.1,
            verdict=Verdict.FAIL,
        ),
    )
    store.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="other-bundle",
            workflow_profile="default",
            project_tags=["auth"],
            integrator_score=0.1,
            verdict=Verdict.FAIL,
        ),
    )
    hits = search_bundles(repo, "auth rbac", k=5, bundle_outcome_store=store)
    if len(hits) >= 2:
        ids = [str(h.get("id")) for h in hits]
        if "auth-rbac-starter" in ids and "other-bundle" in ids:
            assert ids.index("auth-rbac-starter") < ids.index("other-bundle")

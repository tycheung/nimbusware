from __future__ import annotations

from uuid import uuid4

from agent_core.models import Verdict
from hermes_extensions.bundle_memory import (
    InMemoryBundleOutcomeStore,
    build_bundle_outcome_from_gate,
)
from nimbusware_console.bundle_memory_display import (
    bundle_memory_analytics_from_store,
    bundle_memory_caption,
    bundle_success_stats_table_rows,
)


def test_bundle_success_stats_table_rows() -> None:
    store = InMemoryBundleOutcomeStore()
    store.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="bundle-a",
            workflow_profile="default",
            project_tags=["x"],
            integrator_score=0.8,
            verdict=Verdict.PASS,
        ),
    )
    analytics = bundle_memory_analytics_from_store(store)
    assert analytics["available"] is True
    assert analytics["outcome_count"] == 1
    rows = bundle_success_stats_table_rows(analytics["stats"])
    assert rows[0]["bundle_id"] == "bundle-a"
    assert rows[0]["avg_fit_score"] == 0.8
    assert rows[0]["avg_fit_on_pass"] == 0.8
    assert "integrator outcomes" in bundle_memory_caption(analytics)


def test_bundle_memory_caption_when_unavailable() -> None:
    analytics = bundle_memory_analytics_from_store(None)
    assert analytics["available"] is False
    assert "unavailable" in bundle_memory_caption(analytics).lower()

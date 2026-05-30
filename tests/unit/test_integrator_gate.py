"""Integrator gate YAML helpers (bundle id from workflow profile)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_extensions.phase2 import ModuleIntegrator
from hermes_orchestrator.integrator_gate import (
    load_integrator_gate_emit_enabled,
    rank_bundle_compatibility_candidates,
    select_bundle_id_for_workflow,
    workflow_profile_from_run_created_rows,
)


def test_workflow_profile_from_run_created_rows() -> None:
    rows = [
        {"event_type": "run.created", "payload": {"workflow_profile": "custom_wf"}},
    ]
    assert workflow_profile_from_run_created_rows(rows) == "custom_wf"


def test_select_bundle_id_for_workflow_uses_map(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat.write_text(
        """version: 1
workflow_bundle_map:
  custom_wf: billing-stripe
bundles:
  - id: auth-rbac-starter
    tags: [a]
  - id: billing-stripe
    tags: [b]
""",
        encoding="utf-8",
    )
    assert select_bundle_id_for_workflow(tmp_path, "custom_wf") == "billing-stripe"


def test_select_bundle_id_for_workflow_uses_materialized_catalog() -> None:
    class _Mat:
        use_db = True

        @staticmethod
        def get_bundle_catalog() -> dict[str, object]:
            return {
                "version": 1,
                "workflow_bundle_map": {"custom_wf": "db-bundle"},
                "bundles": [{"id": "db-bundle", "tags": ["db"]}],
            }

    assert (
        select_bundle_id_for_workflow(
            Path("."),
            "custom_wf",
            config_materializer=_Mat(),
        )
        == "db-bundle"
    )


def test_select_bundle_id_fallback_first_bundle(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat.write_text(
        """version: 1
bundles:
  - id: first-bundle
    tags: []
  - id: second
    tags: []
""",
        encoding="utf-8",
    )
    assert select_bundle_id_for_workflow(tmp_path, "unknown_profile") == "first-bundle"


def test_load_integrator_gate_emit_enabled_true(tmp_path: Path) -> None:
    (tmp_path / "configs" / "integrator").mkdir(parents=True)
    p = tmp_path / "configs" / "integrator" / "thresholds.yaml"
    p.write_text("version: 1\nenabled: true\nmin_score_to_pass: 0.5\n", encoding="utf-8")
    assert load_integrator_gate_emit_enabled(tmp_path) is True


def test_load_integrator_gate_emit_enabled_false(tmp_path: Path) -> None:
    (tmp_path / "configs" / "integrator").mkdir(parents=True)
    p = tmp_path / "configs" / "integrator" / "thresholds.yaml"
    p.write_text("version: 1\nenabled: false\nmin_score_to_pass: 0.5\n", encoding="utf-8")
    assert load_integrator_gate_emit_enabled(tmp_path) is False


def test_rank_bundle_compatibility_candidates_orders_by_score(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat.write_text(
        """version: 1
bundles:
  - id: low-match
    title: Low
    tags: [x, y, z]
  - id: high-match
    title: High
    tags: [auth, rbac]
  - id: mid-match
    title: Mid
    tags: [auth, extra]
""",
        encoding="utf-8",
    )
    mi = ModuleIntegrator(min_score_to_pass=0.5)
    ranking = rank_bundle_compatibility_candidates(
        tmp_path,
        ["auth", "rbac"],
        integrator=mi,
        limit=10,
    )
    assert len(ranking) == 3
    assert ranking[0]["bundle_id"] == "high-match"
    assert ranking[0]["score"] == 1.0
    assert ranking[0]["passes_gate"] is True
    assert ranking[0]["title"] == "High"
    assert ranking[1]["bundle_id"] == "mid-match"
    assert ranking[1]["score"] == pytest.approx(0.5)
    assert ranking[1]["passes_gate"] is True
    assert ranking[2]["bundle_id"] == "low-match"
    assert ranking[2]["score"] == 0.0
    assert ranking[2]["passes_gate"] is False


def test_rank_bundle_compatibility_candidates_respects_limit(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat.write_text(
        """version: 1
bundles:
  - id: a
    tags: [t]
  - id: b
    tags: [t]
  - id: c
    tags: [t]
""",
        encoding="utf-8",
    )
    mi = ModuleIntegrator(min_score_to_pass=0.0)
    ranking = rank_bundle_compatibility_candidates(
        tmp_path,
        ["t"],
        integrator=mi,
        limit=2,
    )
    assert len(ranking) == 2

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.binding_preflight import (
    active_roles_for_context,
    build_binding_preflight_report,
    cloud_only_roles_satisfied,
)

REPO = Path(__file__).resolve().parents[2]


def test_active_roles_patch_work_type() -> None:
    roles = active_roles_for_context(REPO, work_type="patch")
    assert "planner" in roles
    assert "backend_writer" in roles


def test_active_roles_micro_slice_workflow() -> None:
    roles = active_roles_for_context(REPO, workflow_profile="micro_slice", work_type="slice")
    assert "planner" in roles
    assert "backend_writer" in roles


def test_binding_preflight_report_shape() -> None:
    report = build_binding_preflight_report(REPO, work_type="patch", probe=False)
    assert report["roles_total"] >= 2
    assert "roles_covered" in report
    assert "inference_mode" in report
    assert report["inference_mode_label"]


def test_cloud_only_when_no_local_roles_and_all_reachable() -> None:
    report = {
        "ollama_required": False,
        "roles_without_provider": [],
    }
    assert cloud_only_roles_satisfied(report) is True

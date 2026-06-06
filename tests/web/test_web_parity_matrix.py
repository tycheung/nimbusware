from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.web

MATRIX = Path(__file__).resolve().parent / "parity_matrix.yaml"


def _load() -> dict:
    return yaml.safe_load(MATRIX.read_text(encoding="utf-8"))


def test_parity_matrix_has_maker_rows() -> None:
    data = _load()
    assert len(data.get("maker", [])) >= 30


def test_parity_matrix_web_true_items_exist() -> None:
    data = _load()
    web_true = [r for r in data.get("maker", []) if r.get("web") is True]
    assert any(r["id"] == "shell_loads" for r in web_true)
    assert any(r["id"] == "memory_influence" for r in web_true)
    assert any(r["id"] == "theater_sse_live" for r in web_true)


def test_parity_matrix_maker_web_true_ids_documented() -> None:
    data = _load()
    expected = {
        "shell_loads",
        "bootstrap_json",
        "home_projects",
        "build_intent",
        "slice_approval_apply_skip",
        "plan_approve",
        "theater_poll",
        "theater_sse_live",
        "progress_sse_live",
        "research_approve",
        "research_reject",
        "slice_diff_preview",
        "workspace_revert",
        "models_ranked_table",
        "apply_preset_wizard",
        "models_gpu_filter",
        "ollama_pull",
        "settings_operator",
        "maker_governor_sliders",
        "hardware_panel",
        "deep_link_run_id",
        "memory_influence",
        "readiness_strip",
        "project_create",
        "slice_prepare",
        "progress_simple_mode",
        "quick_mode_banner",
        "git_commit_status",
        "theater_export",
        "settings_catalog_keys",
        "wizard_creates_run",
        "project_delete",
        "admin_unlock_sidebar",
        "mobile_pwa_progress_review",
        "launch_eval_scorecard",
    }
    web_true_ids = {r["id"] for r in data.get("maker", []) if r.get("web") is True}
    assert web_true_ids == expected


def test_parity_matrix_has_no_streamlit_column() -> None:
    data = _load()
    for section in ("maker", "admin"):
        for row in data.get(section, []):
            assert "streamlit" not in row, f"{section}/{row.get('id')} still has streamlit key"

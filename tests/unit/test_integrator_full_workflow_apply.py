"""§14 #13: full-profile workflow YAML paste + merge + disk apply (shallow merge)."""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.slow


import json
from pathlib import Path

import pytest

from nimbusware_console.integrator_workflow_apply import (
    ALLOW_WORKFLOW_YAML_WRITE_ENV,
    apply_full_workflow_yaml,
    merge_full_workflow_into_profile_document,
    prepare_full_workflow_apply,
    workflow_yaml_write_enabled,
)
from nimbusware_console.integrator_workflow_preview import (
    full_workflow_merge_added_top_level_caption,
    full_workflow_merge_attention_export_filename_slug,
    full_workflow_merge_attention_export_json,
    full_workflow_merge_attention_operator_metrics,
    full_workflow_merge_attention_operator_metrics_caption,
    full_workflow_merge_attention_operator_metrics_export_filename_slug,
    full_workflow_merge_attention_operator_metrics_export_json,
    full_workflow_merge_attention_operator_metrics_table_rows,
    full_workflow_merge_attention_operator_metrics_table_rows_csv,
    full_workflow_merge_attention_rows,
    full_workflow_merge_attention_table_rows_csv,
    full_workflow_merge_changed_top_level_caption,
    full_workflow_merge_diff,
    full_workflow_merge_diff_audit_fingerprint_caption,
    full_workflow_merge_diff_export_filename_slug,
    full_workflow_merge_diff_export_json,
    full_workflow_merge_diff_operator_metrics,
    full_workflow_merge_diff_operator_metrics_caption,
    full_workflow_merge_diff_operator_metrics_export_filename_slug,
    full_workflow_merge_diff_operator_metrics_export_json,
    full_workflow_merge_diff_operator_metrics_table_rows,
    full_workflow_merge_diff_operator_metrics_table_rows_csv,
    full_workflow_merge_diff_table_rows,
    full_workflow_merge_diff_table_rows_csv,
    full_workflow_merge_disk_only_top_level_caption,
    full_workflow_merge_overview_caption,
    full_workflow_merge_paste_only_top_level_caption,
    full_workflow_merge_pasted_top_level_caption,
    full_workflow_merge_removed_top_level_caption,
    full_workflow_merge_subtree_added_fields_caption,
    full_workflow_merge_subtree_changed_fields_caption,
    full_workflow_merge_subtree_overview_caption,
    full_workflow_merge_subtree_removed_fields_caption,
    full_workflow_merge_top_level_churn_count_caption,
    full_workflow_merge_unchanged_top_level_caption,
    full_workflow_merge_unchanged_with_churn_caption,
    parse_full_workflow_yaml_paste,
    validate_full_workflow_document,
)
from hermes_orchestrator.merge import load_yaml


@pytest.fixture()
def mini_workflow_repo(tmp_path: Path) -> Path:
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "demo.yaml").write_text(
        "version: 99\n"
        "other_section:\n"
        "  foo: bar\n"
        "integrator_gate:\n"
        "  enabled: true\n"
        "  min_score_to_pass: 0.5\n"
        "  project_tags: [auth]\n"
        "agent_evaluator:\n"
        "  enabled: false\n"
        "  persona_id: legacy-ae\n",
        encoding="utf-8",
    )
    return tmp_path


def test_full_workflow_merge_diff_paste_only_integrator_gate(
    mini_workflow_repo: Path,
) -> None:
    paste = (
        "version: 99\n"
        "integrator_gate:\n"
        "  enabled: false\n"
        "  min_score_to_pass: 0.1\n"
        "  project_tags: [auth]\n"
    )
    merged, before, errs = prepare_full_workflow_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
    )
    assert not errs and merged is not None and before is not None
    d = full_workflow_merge_diff(before, merged)
    assert "error" not in d
    assert "integrator_gate" in d["changed_top_level_keys"]
    # ``merge_full_workflow_into_profile_document`` normalizes ``agent_evaluator`` on the merged
    # document even when the paste omits that key, so it may appear as changed vs raw disk YAML.
    assert "other_section" in d["unchanged_top_level_keys"]
    assert d["added_top_level_keys"] == []
    assert d["removed_top_level_keys"] == []
    ig = d["subtree_field_diffs"]["integrator_gate"]
    assert set(ig["changed_keys"]) == {"enabled", "min_score_to_pass"}


def test_full_workflow_merge_diff_disk_only_top_level_keys(
    mini_workflow_repo: Path,
) -> None:
    paste = (
        "version: 99\n"
        "integrator_gate:\n"
        "  enabled: false\n"
        "  min_score_to_pass: 0.1\n"
        "  project_tags: [auth]\n"
    )
    merged, before, errs = prepare_full_workflow_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
    )
    assert not errs and merged is not None and before is not None
    pasted_doc, p_errs = parse_full_workflow_yaml_paste(paste)
    assert pasted_doc is not None and not p_errs
    d = full_workflow_merge_diff(before, merged, pasted_root=pasted_doc)
    assert "error" not in d
    disk_only = d.get("disk_only_top_level_keys")
    assert isinstance(disk_only, list)
    assert "other_section" in disk_only
    assert "agent_evaluator" in disk_only
    paste_only = d.get("paste_only_top_level_keys")
    assert isinstance(paste_only, list)
    assert paste_only == []
    pasted_keys = d.get("pasted_top_level_keys")
    assert pasted_keys == ["integrator_gate", "version"]


def test_full_workflow_merge_diff_paste_only_top_level_keys() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1},
        {"version": 1, "alpha": 1, "beta": 2},
        pasted_root={"version": 1, "beta": 2, "gamma": 3},
    )
    assert "error" not in d
    paste_only = d.get("paste_only_top_level_keys")
    assert paste_only == ["beta", "gamma"]


def test_full_workflow_merge_pasted_top_level_caption() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1, "zebra": 2},
        {"version": 1, "alpha": 1, "zebra": 2},
        pasted_root={"version": 1, "beta": 2},
    )
    cap = full_workflow_merge_pasted_top_level_caption(d)
    assert cap is not None
    assert "Pasted top-level keys:" in cap
    assert "beta" in cap and "version" in cap


def test_full_workflow_merge_pasted_top_level_caption_none_without_paste() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1},
        {"version": 1, "alpha": 1},
    )
    assert full_workflow_merge_pasted_top_level_caption(d) is None


def test_full_workflow_merge_attention_rows_disk_only_top_level() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1, "zebra": 2},
        {"version": 1, "alpha": 1, "zebra": 2},
        pasted_root={"version": 1},
    )
    rows = full_workflow_merge_attention_rows(d)
    assert any("Disk-only top-level" in r["flag"] for r in rows)
    row = next(r for r in rows if "Disk-only top-level" in r["flag"])
    assert "alpha" in row["keys"] and "zebra" in row["keys"]


def test_full_workflow_merge_attention_rows_pasted_top_level_keys() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1, "zebra": 2},
        {"version": 1, "alpha": 1, "zebra": 2},
        pasted_root={"version": 1},
    )
    rows = full_workflow_merge_attention_rows(d)
    row = next(r for r in rows if "Pasted top-level" in r["flag"])
    assert row["keys"] == "version"


def test_full_workflow_merge_disk_only_top_level_caption() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "zebra": 1, "alpha": 1},
        {"version": 1, "zebra": 1, "alpha": 1},
        pasted_root={"version": 1},
    )
    cap = full_workflow_merge_disk_only_top_level_caption(d)
    assert cap is not None
    assert "Disk-only top-level keys:" in cap
    assert "alpha" in cap and "zebra" in cap


def test_full_workflow_merge_disk_only_top_level_caption_none_without_field() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "a": 1},
        {"version": 1, "a": 1},
    )
    assert full_workflow_merge_disk_only_top_level_caption(d) is None


def test_full_workflow_merge_paste_only_top_level_caption() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1},
        {"version": 1, "alpha": 1, "beta": 2},
        pasted_root={"version": 1, "beta": 2, "gamma": 3},
    )
    cap = full_workflow_merge_paste_only_top_level_caption(d)
    assert cap is not None
    assert "Paste-only top-level keys:" in cap
    assert "beta" in cap and "gamma" in cap


def test_full_workflow_merge_paste_only_top_level_caption_none_without_field() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "a": 1},
        {"version": 1, "a": 1},
        pasted_root={"version": 1, "a": 1},
    )
    assert full_workflow_merge_paste_only_top_level_caption(d) is None


def test_full_workflow_merge_attention_rows_paste_only_top_level() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1},
        {"version": 1, "alpha": 1, "beta": 2},
        pasted_root={"version": 1, "beta": 2},
    )
    rows = full_workflow_merge_attention_rows(d)
    assert any("Paste-only top-level" in r["flag"] for r in rows)
    row = next(r for r in rows if "Paste-only top-level" in r["flag"])
    assert "beta" in row["keys"]


def test_full_workflow_merge_diff_requires_mappings() -> None:
    assert "error" in full_workflow_merge_diff(None, {})
    assert "error" in full_workflow_merge_diff({}, None)


def test_prepare_full_workflow_merge_diff_lists_agent_evaluator_normalization(
    mini_workflow_repo: Path,
) -> None:
    paste = (
        "version: 99\n"
        "agent_evaluator:\n"
        "  enabled: true\n"
        "  persona_id: '  x  '\n"
    )
    merged, before, errs = prepare_full_workflow_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
    )
    assert not errs and merged is not None and before is not None
    d = full_workflow_merge_diff(before, merged)
    assert "agent_evaluator" in d["changed_top_level_keys"]
    ae = d["subtree_field_diffs"]["agent_evaluator"]
    assert "persona_id" in ae["changed_keys"]


def test_full_workflow_merge_attention_rows_removed_top_level() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}, "legacy_key": {}},
        {"version": 1, "integrator_gate": {"enabled": True}},
    )
    rows = full_workflow_merge_attention_rows(d)
    assert len(rows) == 1
    assert "Removed top-level" in rows[0]["flag"]
    assert "legacy_key" in rows[0]["keys"]


def test_full_workflow_merge_attention_rows_gate_and_ae() -> None:
    d = full_workflow_merge_diff(
        {
            "version": 1,
            "integrator_gate": {"enabled": False},
            "agent_evaluator": {"enabled": False},
        },
        {
            "version": 1,
            "integrator_gate": {"enabled": True},
            "agent_evaluator": {"enabled": True},
        },
    )
    rows = full_workflow_merge_attention_rows(d)
    assert any("integrator_gate and agent_evaluator" in r["flag"] for r in rows)


def test_full_workflow_merge_attention_rows_added_top_level() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}},
        {
            "version": 1,
            "integrator_gate": {"enabled": True},
            "escalation": {"suppress_automatic_escalation": False},
        },
    )
    rows = full_workflow_merge_attention_rows(d)
    assert any("Added top-level" in r["flag"] for r in rows)
    assert any("escalation" in r["keys"] for r in rows)


def test_full_workflow_merge_attention_rows_subtree_added_shallow_keys() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {"added_keys": ["min_score_to_pass", "project_tags"]},
            "agent_evaluator": {"added_keys": ["persona_id"]},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    assert any("Added shallow keys" in r["flag"] for r in rows)
    joined = " ".join(r["keys"] for r in rows)
    assert "integrator_gate: added min_score_to_pass, project_tags" in joined
    assert "agent_evaluator: added persona_id" in joined


def test_full_workflow_merge_attention_rows_subtree_added_empty_skips_row() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {"added_keys": []},
            "agent_evaluator": {"added_keys": []},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    assert all("Added shallow keys" not in r["flag"] for r in rows)


def test_full_workflow_merge_attention_rows_added_and_removed_subtree_both_listed() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {
                "removed_keys": ["enabled"],
                "added_keys": ["min_score_to_pass"],
            },
            "agent_evaluator": {},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    flags = [r["flag"] for r in rows]
    assert any("Removed shallow keys" in f for f in flags)
    assert any("Added shallow keys" in f for f in flags)


def test_full_workflow_merge_attention_rows_subtree_removed_shallow_keys() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {"removed_keys": ["enabled", "project_tags"]},
            "agent_evaluator": {"removed_keys": ["persona_id"]},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    assert any("Removed shallow keys" in r["flag"] for r in rows)
    joined = " ".join(r["keys"] for r in rows)
    assert "integrator_gate: removed enabled, project_tags" in joined
    assert "agent_evaluator: removed persona_id" in joined


def test_full_workflow_merge_attention_rows_empty_on_error() -> None:
    assert full_workflow_merge_attention_rows({"error": "x"}) == []
    assert full_workflow_merge_attention_rows(None) == []


def test_full_workflow_merge_attention_rows_subtree_changed_shallow_keys() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {"changed_keys": ["min_score_to_pass", "project_tags"]},
            "agent_evaluator": {"changed_keys": ["persona_id"]},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    assert any("Changed shallow keys" in r["flag"] for r in rows)
    joined = " ".join(r["keys"] for r in rows)
    assert "integrator_gate: changed min_score_to_pass, project_tags" in joined
    assert "agent_evaluator: changed persona_id" in joined


def test_full_workflow_merge_attention_rows_subtree_changed_empty_skips_row() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {"changed_keys": []},
            "agent_evaluator": {"changed_keys": []},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    assert all("Changed shallow keys" not in r["flag"] for r in rows)


def test_full_workflow_merge_attention_rows_subtree_changed_caps_at_twelve() -> None:
    fifteen = [f"k{i:02d}" for i in range(15)]
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {"changed_keys": fifteen},
            "agent_evaluator": {},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    changed = next(r for r in rows if "Changed shallow keys" in r["flag"])
    visible = ", ".join(fifteen[:12])
    assert visible in changed["keys"]
    assert "+3 more" in changed["keys"]
    assert "k12" not in changed["keys"]


def test_full_workflow_merge_attention_rows_added_removed_changed_all_listed() -> None:
    d = {
        "removed_top_level_keys": [],
        "added_top_level_keys": [],
        "changed_top_level_keys": [],
        "subtree_field_diffs": {
            "integrator_gate": {
                "removed_keys": ["enabled"],
                "added_keys": ["min_score_to_pass"],
                "changed_keys": ["project_tags"],
            },
            "agent_evaluator": {},
        },
    }
    rows = full_workflow_merge_attention_rows(d)
    flags = [r["flag"] for r in rows]
    assert any("Removed shallow keys" in f for f in flags)
    assert any("Added shallow keys" in f for f in flags)
    assert any("Changed shallow keys" in f for f in flags)


def test_full_workflow_merge_overview_caption_none_for_bad_input() -> None:
    assert full_workflow_merge_overview_caption(None) is None
    assert full_workflow_merge_overview_caption("x") is None
    assert full_workflow_merge_overview_caption({"error": "boom"}) is None
    assert full_workflow_merge_diff_audit_fingerprint_caption(None) is None
    assert full_workflow_merge_diff_audit_fingerprint_caption({"error": "x"}) is None
    assert full_workflow_merge_top_level_churn_count_caption(None) is None
    assert full_workflow_merge_top_level_churn_count_caption({"error": "x"}) is None


def test_full_workflow_merge_diff_audit_fingerprint_caption_stable() -> None:
    d = {
        "added_top_level_keys": ["a"],
        "removed_top_level_keys": [],
        "changed_top_level_keys": ["b"],
        "unchanged_top_level_keys": ["c"],
    }
    c1 = full_workflow_merge_diff_audit_fingerprint_caption(d)
    c2 = full_workflow_merge_diff_audit_fingerprint_caption(d)
    assert c1 == c2
    assert c1 is not None
    assert "SHA-256 prefix" in c1
    assert "UTF-8 bytes" in c1


def test_full_workflow_merge_diff_audit_fingerprint_changes_when_diff_changes() -> None:
    a = full_workflow_merge_diff_audit_fingerprint_caption(
        {"added_top_level_keys": [], "removed_top_level_keys": [], "changed_top_level_keys": []},
    )
    b = full_workflow_merge_diff_audit_fingerprint_caption(
        {"added_top_level_keys": ["x"], "removed_top_level_keys": [], "changed_top_level_keys": []},
    )
    assert a is not None and b is not None
    assert a != b


def test_full_workflow_merge_overview_caption_all_zero_counts() -> None:
    cap = full_workflow_merge_overview_caption(
        {
            "added_top_level_keys": [],
            "removed_top_level_keys": [],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": [],
        },
    )
    assert cap == "Top-level: +0 / -0 / ~0 / =0"


def test_full_workflow_merge_overview_caption_mixed_counts() -> None:
    cap = full_workflow_merge_overview_caption(
        {
            "added_top_level_keys": ["escalation", "self_refinement"],
            "removed_top_level_keys": ["legacy"],
            "changed_top_level_keys": [
                "integrator_gate",
                "agent_evaluator",
                "universal_critique",
            ],
            "unchanged_top_level_keys": [
                "version",
                "scraper_fetch",
                "preflight",
                "stages",
                "extras",
            ],
        },
    )
    assert cap == "Top-level: +2 / -1 / ~3 / =5"


def test_full_workflow_merge_overview_caption_missing_fields_count_as_zero() -> None:
    cap = full_workflow_merge_overview_caption(
        {"added_top_level_keys": ["a", "b"]},
    )
    assert cap == "Top-level: +2 / -0 / ~0 / =0"


def test_full_workflow_merge_overview_caption_non_list_fields_count_as_zero() -> None:
    cap = full_workflow_merge_overview_caption(
        {
            "added_top_level_keys": None,
            "removed_top_level_keys": "x",
            "changed_top_level_keys": ["only-real-list"],
            "unchanged_top_level_keys": 42,
        },
    )
    assert cap == "Top-level: +0 / -0 / ~1 / =0"


def test_full_workflow_merge_top_level_churn_count_caption_zero() -> None:
    cap = full_workflow_merge_top_level_churn_count_caption(
        {
            "added_top_level_keys": [],
            "removed_top_level_keys": [],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": ["version"],
        },
    )
    assert cap is not None
    assert "**0**" in cap


def test_full_workflow_merge_top_level_churn_count_caption_mixed() -> None:
    cap = full_workflow_merge_top_level_churn_count_caption(
        {
            "added_top_level_keys": ["a", "b"],
            "removed_top_level_keys": ["c"],
            "changed_top_level_keys": ["d"],
            "unchanged_top_level_keys": [],
        },
    )
    assert cap is not None
    assert "**4**" in cap


def test_full_workflow_merge_unchanged_with_churn_caption_none_without_churn() -> None:
    assert (
        full_workflow_merge_unchanged_with_churn_caption(
            {
                "added_top_level_keys": [],
                "removed_top_level_keys": [],
                "changed_top_level_keys": [],
                "unchanged_top_level_keys": ["version"],
            },
        )
        is None
    )


def test_full_workflow_merge_unchanged_with_churn_caption_when_churn_and_unchanged() -> None:
    cap = full_workflow_merge_unchanged_with_churn_caption(
        {
            "added_top_level_keys": ["new_block"],
            "removed_top_level_keys": [],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": ["version", "escalation"],
        },
    )
    assert cap is not None
    assert "1" in cap and "2" in cap


def test_full_workflow_merge_unchanged_with_churn_caption_none_when_no_unchanged() -> None:
    assert (
        full_workflow_merge_unchanged_with_churn_caption(
            {
                "added_top_level_keys": ["a"],
                "unchanged_top_level_keys": [],
            },
        )
        is None
    )


def test_full_workflow_merge_subtree_overview_caption_none_for_bad_input() -> None:
    assert full_workflow_merge_subtree_overview_caption(None) is None
    assert full_workflow_merge_subtree_overview_caption("x") is None
    assert full_workflow_merge_subtree_overview_caption({"error": "boom"}) is None


def test_full_workflow_merge_subtree_overview_caption_none_when_subtree_block_missing() -> None:
    assert full_workflow_merge_subtree_overview_caption({}) is None
    assert (
        full_workflow_merge_subtree_overview_caption({"subtree_field_diffs": None})
        is None
    )
    assert (
        full_workflow_merge_subtree_overview_caption({"subtree_field_diffs": []})
        is None
    )


def test_full_workflow_merge_subtree_overview_caption_all_zero_counts() -> None:
    cap = full_workflow_merge_subtree_overview_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {
                    "added_keys": [],
                    "removed_keys": [],
                    "changed_keys": [],
                    "unchanged_keys": [],
                },
                "agent_evaluator": {
                    "added_keys": [],
                    "removed_keys": [],
                    "changed_keys": [],
                    "unchanged_keys": [],
                },
            },
        },
    )
    assert cap == (
        "Subtree churn: integrator_gate (+0 / -0 / ~0 / =0), "
        "agent_evaluator (+0 / -0 / ~0 / =0)"
    )


def test_full_workflow_merge_subtree_overview_caption_mixed_counts() -> None:
    cap = full_workflow_merge_subtree_overview_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {
                    "added_keys": ["a"],
                    "removed_keys": ["b", "c"],
                    "changed_keys": ["d", "e", "f"],
                    "unchanged_keys": ["g", "h", "i", "j"],
                },
                "agent_evaluator": {
                    "added_keys": ["x", "y"],
                    "removed_keys": [],
                    "changed_keys": ["z"],
                    "unchanged_keys": ["w", "v"],
                },
            },
        },
    )
    assert cap == (
        "Subtree churn: integrator_gate (+1 / -2 / ~3 / =4), "
        "agent_evaluator (+2 / -0 / ~1 / =2)"
    )


def test_full_workflow_merge_subtree_overview_caption_only_integrator_gate_present() -> None:
    cap = full_workflow_merge_subtree_overview_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {
                    "added_keys": ["a"],
                    "removed_keys": [],
                    "changed_keys": [],
                    "unchanged_keys": [],
                },
            },
        },
    )
    assert cap == (
        "Subtree churn: integrator_gate (+1 / -0 / ~0 / =0), "
        "agent_evaluator (+0 / -0 / ~0 / =0)"
    )


def test_full_workflow_merge_subtree_overview_caption_non_list_fields_count_as_zero() -> None:
    cap = full_workflow_merge_subtree_overview_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {
                    "added_keys": None,
                    "removed_keys": "x",
                    "changed_keys": 42,
                    "unchanged_keys": ["real-only"],
                },
                "agent_evaluator": "not-a-mapping",
            },
        },
    )
    assert cap == (
        "Subtree churn: integrator_gate (+0 / -0 / ~0 / =1), "
        "agent_evaluator (+0 / -0 / ~0 / =0)"
    )


def test_full_workflow_merge_unchanged_top_level_caption_none_for_bad_input() -> None:
    assert full_workflow_merge_unchanged_top_level_caption(None) is None
    assert full_workflow_merge_unchanged_top_level_caption("x") is None
    assert full_workflow_merge_unchanged_top_level_caption({"error": "boom"}) is None


def test_full_workflow_merge_unchanged_top_level_caption_none_when_zero_unchanged() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {
            "added_top_level_keys": [],
            "removed_top_level_keys": [],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": [],
        },
    )
    assert cap is None


def test_full_workflow_merge_unchanged_top_level_caption_caption_when_all_unchanged() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {
            "added_top_level_keys": [],
            "removed_top_level_keys": [],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": [
                "version",
                "scraper_fetch",
                "preflight",
                "stages",
                "extras",
                "integrator_gate",
                "agent_evaluator",
                "self_refinement",
                "escalation",
                "universal_critique",
            ],
        },
    )
    assert cap == "All top-level keys unchanged (10 keys; paste reproduces disk)."


def test_full_workflow_merge_unchanged_top_level_caption_none_when_any_added() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {
            "added_top_level_keys": ["new_section"],
            "removed_top_level_keys": [],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": ["version"],
        },
    )
    assert cap is None


def test_full_workflow_merge_unchanged_top_level_caption_none_when_any_removed() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {
            "added_top_level_keys": [],
            "removed_top_level_keys": ["old_section"],
            "changed_top_level_keys": [],
            "unchanged_top_level_keys": ["version"],
        },
    )
    assert cap is None


def test_full_workflow_merge_unchanged_top_level_caption_none_when_any_changed() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {
            "added_top_level_keys": [],
            "removed_top_level_keys": [],
            "changed_top_level_keys": ["integrator_gate"],
            "unchanged_top_level_keys": ["version"],
        },
    )
    assert cap is None


def test_full_workflow_merge_unchanged_top_level_caption_non_list_churn_treated_as_zero() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {
            "added_top_level_keys": None,
            "removed_top_level_keys": "x",
            "changed_top_level_keys": 42,
            "unchanged_top_level_keys": ["version", "stages"],
        },
    )
    assert cap == "All top-level keys unchanged (2 keys; paste reproduces disk)."


def test_full_workflow_merge_unchanged_top_level_caption_missing_churn_fields_caption() -> None:
    cap = full_workflow_merge_unchanged_top_level_caption(
        {"unchanged_top_level_keys": ["version"]},
    )
    assert cap == "All top-level keys unchanged (1 keys; paste reproduces disk)."


def test_full_workflow_merge_changed_top_level_caption_none_for_bad_input() -> None:
    assert full_workflow_merge_changed_top_level_caption(None) is None
    assert full_workflow_merge_changed_top_level_caption("x") is None
    assert full_workflow_merge_changed_top_level_caption({"error": "boom"}) is None


def test_full_workflow_merge_changed_top_level_caption_none_when_missing_or_non_list() -> None:
    assert full_workflow_merge_changed_top_level_caption({}) is None
    assert (
        full_workflow_merge_changed_top_level_caption({"changed_top_level_keys": None})
        is None
    )
    assert (
        full_workflow_merge_changed_top_level_caption({"changed_top_level_keys": "x"})
        is None
    )
    assert (
        full_workflow_merge_changed_top_level_caption({"changed_top_level_keys": 42})
        is None
    )


def test_full_workflow_merge_changed_top_level_caption_none_when_empty_list() -> None:
    cap = full_workflow_merge_changed_top_level_caption(
        {"changed_top_level_keys": []},
    )
    assert cap is None


def test_full_workflow_merge_changed_top_level_caption_single_entry() -> None:
    cap = full_workflow_merge_changed_top_level_caption(
        {"changed_top_level_keys": ["integrator_gate"]},
    )
    assert cap == "Changed top-level keys: integrator_gate."


def test_full_workflow_merge_changed_top_level_caption_sorted_alphabetically() -> None:
    cap = full_workflow_merge_changed_top_level_caption(
        {
            "changed_top_level_keys": [
                "integrator_gate",
                "agent_evaluator",
                "self_refinement",
            ],
        },
    )
    assert cap == (
        "Changed top-level keys: agent_evaluator, integrator_gate, self_refinement."
    )


def test_full_workflow_merge_changed_top_level_caption_dedupes_and_strips() -> None:
    cap = full_workflow_merge_changed_top_level_caption(
        {
            "changed_top_level_keys": [
                "integrator_gate",
                "integrator_gate",
                "  integrator_gate  ",
                "agent_evaluator",
            ],
        },
    )
    assert cap == "Changed top-level keys: agent_evaluator, integrator_gate."


def test_full_workflow_merge_changed_top_level_caption_skips_non_string_entries() -> None:
    cap = full_workflow_merge_changed_top_level_caption(
        {
            "changed_top_level_keys": [
                None,
                42,
                "agent_evaluator",
                True,
                "",
                "   ",
            ],
        },
    )
    assert cap == "Changed top-level keys: agent_evaluator."


def test_full_workflow_merge_changed_top_level_caption_none_when_all_non_string() -> None:
    cap = full_workflow_merge_changed_top_level_caption(
        {"changed_top_level_keys": [None, 42, True, "", "   "]},
    )
    assert cap is None


def test_full_workflow_merge_added_top_level_caption_none_for_bad_input() -> None:
    assert full_workflow_merge_added_top_level_caption(None) is None
    assert full_workflow_merge_added_top_level_caption("x") is None
    assert full_workflow_merge_added_top_level_caption({"error": "boom"}) is None


def test_full_workflow_merge_added_top_level_caption_none_when_missing_or_non_list() -> None:
    assert full_workflow_merge_added_top_level_caption({}) is None
    assert (
        full_workflow_merge_added_top_level_caption({"added_top_level_keys": None})
        is None
    )
    assert (
        full_workflow_merge_added_top_level_caption({"added_top_level_keys": "x"})
        is None
    )
    assert (
        full_workflow_merge_added_top_level_caption({"added_top_level_keys": 42})
        is None
    )


def test_full_workflow_merge_added_top_level_caption_none_when_empty_list() -> None:
    cap = full_workflow_merge_added_top_level_caption(
        {"added_top_level_keys": []},
    )
    assert cap is None


def test_full_workflow_merge_added_top_level_caption_single_entry() -> None:
    cap = full_workflow_merge_added_top_level_caption(
        {"added_top_level_keys": ["self_refinement"]},
    )
    assert cap == "Added top-level keys: self_refinement."


def test_full_workflow_merge_added_top_level_caption_sorted_alphabetically() -> None:
    cap = full_workflow_merge_added_top_level_caption(
        {
            "added_top_level_keys": [
                "self_refinement",
                "agent_evaluator",
                "escalation",
            ],
        },
    )
    assert cap == (
        "Added top-level keys: agent_evaluator, escalation, self_refinement."
    )


def test_full_workflow_merge_added_top_level_caption_dedupes_and_strips() -> None:
    cap = full_workflow_merge_added_top_level_caption(
        {
            "added_top_level_keys": [
                "self_refinement",
                "self_refinement",
                "  self_refinement  ",
                "agent_evaluator",
            ],
        },
    )
    assert cap == "Added top-level keys: agent_evaluator, self_refinement."


def test_full_workflow_merge_added_top_level_caption_skips_non_string_entries() -> None:
    cap = full_workflow_merge_added_top_level_caption(
        {
            "added_top_level_keys": [
                None,
                42,
                "agent_evaluator",
                True,
                "",
                "   ",
            ],
        },
    )
    assert cap == "Added top-level keys: agent_evaluator."


def test_full_workflow_merge_added_top_level_caption_none_when_all_non_string() -> None:
    cap = full_workflow_merge_added_top_level_caption(
        {"added_top_level_keys": [None, 42, True, "", "   "]},
    )
    assert cap is None


def test_full_workflow_merge_removed_top_level_caption_none_for_bad_input() -> None:
    assert full_workflow_merge_removed_top_level_caption(None) is None
    assert full_workflow_merge_removed_top_level_caption("x") is None
    assert full_workflow_merge_removed_top_level_caption({"error": "boom"}) is None


def test_full_workflow_merge_removed_top_level_caption_none_when_missing_or_non_list() -> None:
    assert full_workflow_merge_removed_top_level_caption({}) is None
    assert (
        full_workflow_merge_removed_top_level_caption({"removed_top_level_keys": None})
        is None
    )
    assert (
        full_workflow_merge_removed_top_level_caption({"removed_top_level_keys": "x"})
        is None
    )
    assert (
        full_workflow_merge_removed_top_level_caption({"removed_top_level_keys": 42})
        is None
    )


def test_full_workflow_merge_removed_top_level_caption_none_when_empty_list() -> None:
    cap = full_workflow_merge_removed_top_level_caption(
        {"removed_top_level_keys": []},
    )
    assert cap is None


def test_full_workflow_merge_removed_top_level_caption_single_entry() -> None:
    cap = full_workflow_merge_removed_top_level_caption(
        {"removed_top_level_keys": ["self_refinement"]},
    )
    assert cap == "Removed top-level keys: self_refinement."


def test_full_workflow_merge_removed_top_level_caption_sorted_alphabetically() -> None:
    cap = full_workflow_merge_removed_top_level_caption(
        {
            "removed_top_level_keys": [
                "self_refinement",
                "agent_evaluator",
                "escalation",
            ],
        },
    )
    assert cap == (
        "Removed top-level keys: agent_evaluator, escalation, self_refinement."
    )


def test_full_workflow_merge_removed_top_level_caption_dedupes_and_strips() -> None:
    cap = full_workflow_merge_removed_top_level_caption(
        {
            "removed_top_level_keys": [
                "self_refinement",
                "self_refinement",
                "  self_refinement  ",
                "agent_evaluator",
            ],
        },
    )
    assert cap == "Removed top-level keys: agent_evaluator, self_refinement."


def test_full_workflow_merge_removed_top_level_caption_skips_non_string_entries() -> None:
    cap = full_workflow_merge_removed_top_level_caption(
        {
            "removed_top_level_keys": [
                None,
                42,
                "agent_evaluator",
                True,
                "",
                "   ",
            ],
        },
    )
    assert cap == "Removed top-level keys: agent_evaluator."


def test_full_workflow_merge_removed_top_level_caption_none_when_all_non_string() -> None:
    cap = full_workflow_merge_removed_top_level_caption(
        {"removed_top_level_keys": [None, 42, True, "", "   "]},
    )
    assert cap is None


def test_full_workflow_merge_subtree_changed_fields_caption_none_for_bad_diff() -> None:
    assert full_workflow_merge_subtree_changed_fields_caption(None) is None
    assert full_workflow_merge_subtree_changed_fields_caption("x") is None
    assert full_workflow_merge_subtree_changed_fields_caption({"error": "boom"}) is None


def test_full_workflow_merge_subtree_changed_fields_caption_none_when_subtrees_missing() -> (
    None
):
    assert full_workflow_merge_subtree_changed_fields_caption({}) is None


def test_full_workflow_merge_subtree_changed_fields_caption_none_when_subtrees_not_mapping() -> (
    None
):
    assert (
        full_workflow_merge_subtree_changed_fields_caption(
            {"subtree_field_diffs": "not-a-mapping"},
        )
        is None
    )


def test_full_workflow_merge_subtree_changed_fields_caption_none_when_both_empty() -> None:
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {"changed_keys": []},
                "agent_evaluator": {"changed_keys": []},
            },
        },
    )
    assert cap is None


def test_full_workflow_merge_subtree_changed_fields_caption_integrator_gate_only() -> None:
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {"changed_keys": ["zebra", "apple"]},
                "agent_evaluator": {"added_keys": ["x"]},
            },
        },
    )
    assert cap == "Subtree changed fields: integrator_gate (apple, zebra)."


def test_full_workflow_merge_subtree_changed_fields_caption_agent_evaluator_only() -> None:
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {},
                "agent_evaluator": {"changed_keys": ["beta", "alpha"]},
            },
        },
    )
    assert cap == "Subtree changed fields: agent_evaluator (alpha, beta)."


def test_full_workflow_merge_subtree_changed_fields_caption_both_blocks_sorted() -> None:
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {"changed_keys": ["z", "a"]},
                "agent_evaluator": {"changed_keys": ["m", "b"]},
            },
        },
    )
    assert cap == (
        "Subtree changed fields: integrator_gate (a, z), agent_evaluator (b, m)."
    )


def test_full_workflow_merge_subtree_changed_fields_caption_dedupes_and_strips() -> None:
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {
                    "changed_keys": ["foo", "  foo  ", "bar", "bar"],
                },
            },
        },
    )
    assert cap == "Subtree changed fields: integrator_gate (bar, foo)."


def test_full_workflow_merge_subtree_changed_fields_caption_skips_non_string_and_whitespace() -> (
    None
):
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {
                    "changed_keys": [None, 42, "", "   ", "ok"],
                },
                "agent_evaluator": {
                    "changed_keys": [True, "also"],
                },
            },
        },
    )
    assert cap == "Subtree changed fields: integrator_gate (ok), agent_evaluator (also)."


def test_full_workflow_merge_subtree_changed_fields_caption_seven_keys_overflow() -> None:
    keys = ["g", "f", "e", "d", "c", "b", "a"]
    cap = full_workflow_merge_subtree_changed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {"changed_keys": keys},
            },
        },
    )
    assert cap == (
        "Subtree changed fields: integrator_gate (a, b, c, d, e, f (+1 more))."
    )


def test_full_workflow_merge_subtree_removed_fields_caption_none_for_bad_diff() -> None:
    assert full_workflow_merge_subtree_removed_fields_caption(None) is None
    assert full_workflow_merge_subtree_removed_fields_caption({"error": "x"}) is None


def test_full_workflow_merge_subtree_removed_fields_caption_integrator_only() -> None:
    cap = full_workflow_merge_subtree_removed_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {"removed_keys": ["z", "a"]},
                "agent_evaluator": {"changed_keys": ["x"]},
            },
        },
    )
    assert cap == "Subtree removed fields: integrator_gate (a, z)."


def test_full_workflow_merge_subtree_removed_fields_caption_overflow() -> None:
    keys = ["g", "f", "e", "d", "c", "b", "a"]
    cap = full_workflow_merge_subtree_removed_fields_caption(
        {
            "subtree_field_diffs": {
                "agent_evaluator": {"removed_keys": keys},
            },
        },
    )
    assert cap == (
        "Subtree removed fields: agent_evaluator (a, b, c, d, e, f (+1 more))."
    )


def test_full_workflow_merge_subtree_added_fields_caption_none_for_bad_diff() -> None:
    assert full_workflow_merge_subtree_added_fields_caption(None) is None
    assert full_workflow_merge_subtree_added_fields_caption({"error": "x"}) is None


def test_full_workflow_merge_subtree_added_fields_caption_integrator_only() -> None:
    cap = full_workflow_merge_subtree_added_fields_caption(
        {
            "subtree_field_diffs": {
                "integrator_gate": {"added_keys": ["z", "a"]},
                "agent_evaluator": {"removed_keys": ["x"]},
            },
        },
    )
    assert cap == "Subtree added fields: integrator_gate (a, z)."


def test_full_workflow_merge_subtree_added_fields_caption_overflow() -> None:
    keys = ["g", "f", "e", "d", "c", "b", "a"]
    cap = full_workflow_merge_subtree_added_fields_caption(
        {
            "subtree_field_diffs": {
                "agent_evaluator": {"added_keys": keys},
            },
        },
    )
    assert cap == "Subtree added fields: agent_evaluator (a, b, c, d, e, f (+1 more))."


def test_validate_full_workflow_rejects_unknown_top_level_key() -> None:
    doc = {"version": 1, "not_allowed": True}
    errs = validate_full_workflow_document(doc)
    assert any("unknown top-level" in e for e in errs)


def test_validate_full_workflow_rejects_bad_version() -> None:
    errs = validate_full_workflow_document({"version": 0, "integrator_gate": {"enabled": False}})
    assert any("version" in e.lower() for e in errs)


def test_validate_full_workflow_rejects_bad_integrator_gate_score() -> None:
    doc = {
        "version": 1,
        "integrator_gate": {"enabled": True, "min_score_to_pass": 9.0},
    }
    errs = validate_full_workflow_document(doc)
    assert errs


def test_prepare_full_workflow_merge_preserves_unmentioned_keys(
    mini_workflow_repo: Path,
) -> None:
    paste = "version: 99\nintegrator_gate:\n  enabled: false\n  min_score_to_pass: 0.1\n"
    merged, before, errs = prepare_full_workflow_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
    )
    assert not errs
    assert merged is not None and before is not None
    assert merged["other_section"] == {"foo": "bar"}
    assert merged["integrator_gate"]["enabled"] is False
    assert merged["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.1)


def test_prepare_full_workflow_normalizes_agent_evaluator_block(
    mini_workflow_repo: Path,
) -> None:
    paste = (
        "version: 99\n"
        "agent_evaluator:\n"
        "  enabled: true\n"
        "  persona_id: '  x  '\n"
    )
    merged, _b, errs = prepare_full_workflow_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
    )
    assert not errs and merged is not None
    assert merged["agent_evaluator"]["persona_id"] == "x"


def test_merge_full_workflow_overwrites_top_level_subtrees(
    mini_workflow_repo: Path,
) -> None:
    pasted = {"version": 1, "integrator_gate": {"enabled": True, "min_score_to_pass": 0.2}}
    merged, before = merge_full_workflow_into_profile_document(
        mini_workflow_repo,
        "demo",
        pasted,
    )
    assert before["version"] == 99
    assert merged["version"] == 1
    assert merged["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.2)


def test_apply_full_workflow_yaml_requires_env(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, raising=False)
    ok, _doc, errs = apply_full_workflow_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="version: 1\n",
        confirm_profile_stem="demo",
    )
    assert ok is False
    assert any(ALLOW_WORKFLOW_YAML_WRITE_ENV in e for e in errs)


def test_apply_full_workflow_yaml_requires_confirmation_match(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "1")
    ok, _doc, errs = apply_full_workflow_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml="version: 1\n",
        confirm_profile_stem="not-demo",
    )
    assert ok is False
    assert any("confirmation" in e.lower() for e in errs)


def test_apply_full_workflow_yaml_writes_disk(
    mini_workflow_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "1")
    wf_path = mini_workflow_repo / "configs" / "workflows" / "demo.yaml"
    paste = "version: 100\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: 0.33\n"
    ok, merged, errs = apply_full_workflow_yaml(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
        confirm_profile_stem="demo",
    )
    assert ok and not errs and merged is not None
    disk = load_yaml(wf_path)
    assert disk["version"] == 100
    assert disk["integrator_gate"]["min_score_to_pass"] == pytest.approx(0.33)
    assert disk["other_section"] == {"foo": "bar"}


def test_workflow_yaml_write_enabled_truthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ALLOW_WORKFLOW_YAML_WRITE_ENV, "on")
    assert workflow_yaml_write_enabled() is True


def test_full_workflow_merge_diff_table_rows_export_json_and_csv(
    mini_workflow_repo: Path,
) -> None:
    paste = (
        "version: 99\n"
        "integrator_gate:\n"
        "  enabled: false\n"
        "  min_score_to_pass: 0.1\n"
        "  project_tags: [auth]\n"
    )
    merged, before, errs = prepare_full_workflow_apply(
        mini_workflow_repo,
        profile_stem="demo",
        pasted_yaml=paste,
    )
    assert not errs and merged is not None and before is not None
    diff = full_workflow_merge_diff(before, merged)
    rows = full_workflow_merge_diff_table_rows(diff)
    fields = {r["field"] for r in rows}
    assert "changed_top_level_keys" in fields
    changed_row = next(r for r in rows if r["field"] == "changed_top_level_keys")
    assert "integrator_gate" in changed_row["value"]
    assert len(rows) == len(diff)
    parsed = json.loads(full_workflow_merge_diff_export_json(diff))
    assert set(parsed.keys()) == set(diff.keys())
    csv_text = full_workflow_merge_diff_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert full_workflow_merge_diff_table_rows({}) == []  # type: ignore[arg-type]
    assert full_workflow_merge_diff_table_rows_csv([]) == ""
    assert full_workflow_merge_diff_export_filename_slug() == "full_workflow_merge_diff"


def test_full_workflow_merge_diff_table_rows_empty_on_error() -> None:
    err_diff = {"error": "before_disk and merged_preview are required"}
    assert full_workflow_merge_diff_table_rows(err_diff) == []
    parsed = json.loads(full_workflow_merge_diff_export_json(err_diff))
    assert parsed["error"] == err_diff["error"]
    assert full_workflow_merge_diff_table_rows(None) == []  # type: ignore[arg-type]


def test_full_workflow_merge_diff_operator_metrics_disk_only_count() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1, "beta": 2},
        {"version": 1, "alpha": 1},
        pasted_root={"version": 1, "alpha": 1},
    )
    m = full_workflow_merge_diff_operator_metrics(d)
    assert m["disk_only_top_level_count"] == 1
    cap = full_workflow_merge_diff_operator_metrics_caption(m)
    assert cap is not None
    assert "disk-only" in cap


def test_full_workflow_merge_diff_operator_metrics_paste_only_count() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "alpha": 1},
        {"version": 1, "alpha": 1, "beta": 2},
        pasted_root={"version": 1, "beta": 2, "gamma": 3},
    )
    m = full_workflow_merge_diff_operator_metrics(d)
    assert m["paste_only_top_level_count"] == 2
    cap = full_workflow_merge_diff_operator_metrics_caption(m)
    assert cap is not None
    assert "paste-only" in cap


def test_full_workflow_merge_diff_operator_metrics_counts() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}, "legacy_key": {}},
        {
            "version": 2,
            "integrator_gate": {"enabled": False},
            "agent_evaluator": {"enabled": True},
        },
    )
    m = full_workflow_merge_diff_operator_metrics(d)
    assert m["has_error"] is False
    assert m["removed_top_level_count"] == 1
    assert m["changed_top_level_count"] >= 1
    assert m["top_level_churn"] >= 2
    assert m["subtree_diff_count"] >= 1
    cap = full_workflow_merge_diff_operator_metrics_caption(m)
    assert cap is not None
    assert "Top-level:" in cap


def test_full_workflow_merge_diff_operator_metrics_error() -> None:
    m = full_workflow_merge_diff_operator_metrics({"error": "bad"})
    assert m["has_error"] is True
    assert full_workflow_merge_diff_operator_metrics_caption(m) is None
    rows = full_workflow_merge_diff_operator_metrics_table_rows(m)
    assert rows == [{"field": "Error", "value": "yes"}]


def test_full_workflow_merge_diff_operator_metrics_export() -> None:
    d = full_workflow_merge_diff({"a": 1}, {"a": 2, "b": 3})
    m = full_workflow_merge_diff_operator_metrics(d)
    parsed = json.loads(full_workflow_merge_diff_operator_metrics_export_json(m))
    assert parsed["top_level_churn"] == m["top_level_churn"]
    assert json.loads(full_workflow_merge_diff_operator_metrics_export_json(None)) == {}
    rows = full_workflow_merge_diff_operator_metrics_table_rows(m)
    csv_text = full_workflow_merge_diff_operator_metrics_table_rows_csv(rows)
    assert "Top-level churn" in csv_text
    assert (
        full_workflow_merge_diff_operator_metrics_export_filename_slug()
        == "full_workflow_merge_diff_operator_metrics"
    )


def test_full_workflow_merge_attention_export_json_and_csv() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}, "legacy_key": {}},
        {"version": 1, "integrator_gate": {"enabled": True}},
    )
    rows = full_workflow_merge_attention_rows(d)
    assert len(rows) == 1
    parsed = json.loads(full_workflow_merge_attention_export_json(rows))
    assert len(parsed) == len(rows)
    csv_text = full_workflow_merge_attention_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "flag,keys"
    assert "legacy_key" in csv_text
    assert full_workflow_merge_attention_table_rows_csv([]) == ""
    assert (
        full_workflow_merge_attention_export_filename_slug()
        == "full_workflow_merge_attention"
    )


def test_full_workflow_merge_attention_export_empty_when_no_flags() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}},
        {"version": 1, "integrator_gate": {"enabled": True}},
    )
    rows = full_workflow_merge_attention_rows(d)
    assert rows == []
    assert full_workflow_merge_attention_table_rows_csv(rows) == ""
    assert json.loads(full_workflow_merge_attention_export_json(rows)) == []


def test_full_workflow_merge_attention_operator_metrics_counts() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}, "legacy_key": {}},
        {
            "version": 1,
            "integrator_gate": {"enabled": True},
            "agent_evaluator": {"enabled": False},
        },
    )
    m = full_workflow_merge_attention_operator_metrics(d)
    assert m["attention_row_count"] >= 1
    assert m["has_removed_top_level"] is True
    cap = full_workflow_merge_attention_operator_metrics_caption(m)
    assert cap is not None
    assert "attention" in cap.lower()


def test_full_workflow_merge_attention_operator_metrics_empty_diff() -> None:
    d = full_workflow_merge_diff(
        {"version": 1, "integrator_gate": {"enabled": True}},
        {"version": 1, "integrator_gate": {"enabled": True}},
    )
    m = full_workflow_merge_attention_operator_metrics(d)
    assert m["attention_row_count"] == 0
    assert full_workflow_merge_attention_operator_metrics_caption(m) is None


def test_full_workflow_merge_attention_operator_metrics_error() -> None:
    m = full_workflow_merge_attention_operator_metrics({"error": "bad"})
    assert m["has_error"] is True
    assert full_workflow_merge_attention_operator_metrics_caption(m) is None


def test_full_workflow_merge_attention_operator_metrics_export() -> None:
    d = full_workflow_merge_diff({"a": 1}, {"b": 2})
    m = full_workflow_merge_attention_operator_metrics(d)
    parsed = json.loads(full_workflow_merge_attention_operator_metrics_export_json(m))
    assert parsed["attention_row_count"] == m["attention_row_count"]
    assert json.loads(full_workflow_merge_attention_operator_metrics_export_json(None)) == {}
    rows = full_workflow_merge_attention_operator_metrics_table_rows(m)
    csv_text = full_workflow_merge_attention_operator_metrics_table_rows_csv(rows)
    assert "Attention row count" in csv_text
    assert (
        full_workflow_merge_attention_operator_metrics_export_filename_slug()
        == "full_workflow_merge_attention_operator_metrics"
    )

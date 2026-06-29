from __future__ import annotations

import pytest

from nimbusware_env import find_repo_root

pytestmark = pytest.mark.slow


import json
from pathlib import Path

import pytest

import nimbusware_orchestrator.pipeline  # noqa: F401 — break extensions↔orchestrator cycle
from nimbusware_console.persona_catalog import (
    critique_pairings_critic_counts_all_export_json,
    critique_pairings_critic_counts_all_table_rows,
    critique_pairings_critic_counts_all_table_rows_csv,
    critique_pairings_critic_counts_export_json,
    critique_pairings_critic_counts_table_rows,
    critique_pairings_critic_counts_table_rows_csv,
    critique_pairings_export_filename_slug,
    critique_pairings_operator_summary,
    critique_pairings_operator_summary_export_json,
    critique_pairings_operator_summary_operator_metrics,
    critique_pairings_operator_summary_operator_metrics_caption,
    critique_pairings_operator_summary_operator_metrics_export_filename_slug,
    critique_pairings_operator_summary_operator_metrics_export_json,
    critique_pairings_operator_summary_operator_metrics_table_rows,
    critique_pairings_operator_summary_operator_metrics_table_rows_csv,
    critique_pairings_producer_keys_all_export_json,
    critique_pairings_producer_keys_all_table_rows,
    critique_pairings_producer_keys_all_table_rows_csv,
    critique_pairings_producer_keys_export_json,
    critique_pairings_producer_keys_table_rows,
    critique_pairings_producer_keys_table_rows_csv,
    filter_persona_catalog_flat_rows,
    load_persona_shelves_catalog,
    persona_catalog_allowed_tool_filter_caption,
    persona_catalog_critique_pairings_total_caption,
    persona_catalog_display_name_duplicates_operator_caption,
    persona_catalog_display_name_length_caption,
    persona_catalog_distinct_allowed_tools,
    persona_catalog_empty_id_operator_caption,
    persona_catalog_flat_export_filename_slug,
    persona_catalog_flat_rows,
    persona_catalog_flat_rows_csv,
    persona_catalog_flat_rows_export_json,
    persona_catalog_operator_summary,
    persona_catalog_operator_summary_export_json,
    persona_catalog_operator_summary_operator_metrics,
    persona_catalog_operator_summary_operator_metrics_caption,
    persona_catalog_operator_summary_operator_metrics_export_filename_slug,
    persona_catalog_operator_summary_operator_metrics_export_json,
    persona_catalog_operator_summary_operator_metrics_table_rows,
    persona_catalog_operator_summary_table_rows,
    persona_catalog_operator_summary_table_rows_csv,
    persona_catalog_persona_id_duplicates_operator_caption,
    persona_catalog_persona_id_length_caption,
    persona_catalog_probation_breakdown_caption,
    persona_catalog_taxonomy_scope_frozen_caption,
    persona_catalog_without_capability_profile_caption,
    persona_catalog_without_instructions_caption,
    persona_probation_other_by_shelf_export_json,
    persona_probation_other_by_shelf_table_rows_csv,
    persona_probation_other_examples_by_shelf_table_rows,
    persona_probation_other_export_filename_slug,
)


def test_persona_catalog_operator_summary_export_json() -> None:
    cat: dict = {"version": 1, "business_area": [], "development_role": []}
    s = persona_catalog_operator_summary(cat)
    parsed = json.loads(persona_catalog_operator_summary_export_json(s))
    assert parsed == s
    assert json.loads(persona_catalog_operator_summary_export_json(None)) == {}
    assert persona_catalog_operator_summary_export_json("x") == "{}"


def test_persona_catalog_operator_summary_table_rows_csv() -> None:
    cat: dict = {"version": 1, "business_area": [], "development_role": []}
    s = persona_catalog_operator_summary(cat)
    rows = persona_catalog_operator_summary_table_rows(s)
    assert rows
    fields = {r["field"] for r in rows}
    assert "total_entries" in fields
    prob_row = next(r for r in rows if r["field"] == "probation_status_breakdown")
    assert json.loads(prob_row["value"]) == s["probation_status_breakdown"]
    csv_text = persona_catalog_operator_summary_table_rows_csv(s)
    assert csv_text.splitlines()[0] == "field,value"
    assert "total_entries" in csv_text
    assert persona_catalog_operator_summary_table_rows(None) == []
    assert persona_catalog_operator_summary_table_rows_csv(None) == ""


def test_persona_catalog_operator_summary_operator_metrics() -> None:
    cat: dict = {
        "version": 1,
        "business_area": [
            {
                "id": "ba-1",
                "display_name": "BA",
                "instructions": "x",
                "probation_status": "probation",
            },
        ],
        "development_role": [
            {
                "id": "dr-1",
                "display_name": "DR",
                "probation_status": "promoted",
            },
        ],
    }
    s = persona_catalog_operator_summary(cat)
    m = persona_catalog_operator_summary_operator_metrics(s)
    assert m["total_entries"] == 2
    assert m["business_area_count"] == 1
    assert m["development_role_count"] == 1
    assert m["without_instructions"] == 1
    assert m["probation_total"] == 1
    assert m["promoted_total"] == 1
    cap = persona_catalog_operator_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "2" in cap


def test_persona_catalog_operator_summary_operator_metrics_export() -> None:
    m = persona_catalog_operator_summary_operator_metrics(
        {"total_entries": 0, "probation_status_breakdown": {}},
    )
    assert persona_catalog_operator_summary_operator_metrics_caption(m) is None
    parsed = json.loads(persona_catalog_operator_summary_operator_metrics_export_json(m))
    assert parsed["total_entries"] == 0
    rows = persona_catalog_operator_summary_operator_metrics_table_rows(m)
    assert rows[0]["field"] == "Total entries"
    assert (
        persona_catalog_operator_summary_operator_metrics_export_filename_slug()
        == "persona_operator_summary_metrics"
    )


def test_persona_catalog_display_name_length_caption_from_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    cat = load_persona_shelves_catalog(root)
    cap = persona_catalog_display_name_length_caption(cat)
    assert cap is not None
    assert "min **8**" in cap
    assert "max **16**" in cap


def test_persona_catalog_persona_id_length_caption_from_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    cat = load_persona_shelves_catalog(root)
    cap = persona_catalog_persona_id_length_caption(cat)
    assert cap is not None
    assert "min **8**" in cap
    assert "max **16**" in cap


def test_persona_catalog_operator_summary_empty_or_missing_id_count() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "ok", "display_name": "A"},
            {"id": "", "display_name": "B"},
            {"display_name": "C"},
        ],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["empty_or_missing_id_count"] == 2


def test_persona_catalog_operator_summary_nonblank_display_name_duplicate_row_count() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "display_name": "Same"},
            {"id": "b", "display_name": "same"},
        ],
        "development_role": [
            {"id": "c", "display_name": "Unique"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["nonblank_display_name_duplicate_row_count"] == 2


def test_persona_catalog_operator_summary_display_name_duplicates_four_way() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "display_name": "X"},
            {"id": "b", "display_name": " X "},
        ],
        "development_role": [
            {"id": "c", "display_name": "Y"},
            {"id": "d", "display_name": "y"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["nonblank_display_name_duplicate_row_count"] == 4


def test_persona_catalog_operator_summary_display_name_duplicates_none_when_unique() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "display_name": "One"}],
        "development_role": [{"id": "b", "display_name": "Two"}],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["nonblank_display_name_duplicate_row_count"] == 0


def test_persona_catalog_operator_summary_nonblank_persona_id_duplicate_row_count() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "same-id", "display_name": "A"},
            {"id": "same-id", "display_name": "B"},
        ],
        "development_role": [
            {"id": "unique", "display_name": "C"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["nonblank_persona_id_duplicate_row_count"] == 2


def test_persona_catalog_without_instructions_caption() -> None:
    cap = persona_catalog_without_instructions_caption(
        {"without_instructions": 2, "total_entries": 5},
    )
    assert cap is not None
    assert "**2**" in cap
    assert "**5**" in cap
    assert (
        persona_catalog_without_instructions_caption(
            {"without_instructions": 0, "total_entries": 5},
        )
        is None
    )
    assert persona_catalog_without_instructions_caption(None) is None
    assert persona_catalog_without_instructions_caption({}) is None


def test_persona_catalog_without_capability_profile_caption() -> None:
    cap = persona_catalog_without_capability_profile_caption(
        {"without_capability_profile": 1, "total_entries": 4},
    )
    assert cap is not None
    assert "capability_profile" in cap
    assert "**1**" in cap
    assert (
        persona_catalog_without_capability_profile_caption(
            {"without_capability_profile": 0, "total_entries": 4},
        )
        is None
    )
    assert persona_catalog_without_capability_profile_caption(None) is None


def test_persona_catalog_critique_pairings_total_caption() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    cp_sum = critique_pairings_operator_summary(root)
    cap = persona_catalog_critique_pairings_total_caption(cp_sum)
    if cp_sum.get("has_critique_pairings_yaml") is True:
        assert cap is not None
        assert "critic-role entries" in cap
    else:
        assert cap is None
    assert persona_catalog_critique_pairings_total_caption(None) is None
    assert (
        persona_catalog_critique_pairings_total_caption(
            {"has_critique_pairings_yaml": False},
        )
        is None
    )


def test_persona_catalog_probation_breakdown_caption() -> None:
    cap = persona_catalog_probation_breakdown_caption(
        {
            "probation_status_breakdown": {
                "promoted": 2,
                "probation": 1,
                "shelved": 0,
                "unset": 1,
                "other": 0,
            },
            "with_probation_status": 3,
        },
    )
    assert cap is not None
    assert "promoted=2" in cap
    assert "probation=1" in cap
    assert "unset=1" in cap
    assert persona_catalog_probation_breakdown_caption(None) is None
    assert persona_catalog_probation_breakdown_caption({}) is None


def test_persona_catalog_persona_id_duplicates_operator_caption() -> None:
    s = persona_catalog_operator_summary(
        {
            "version": 1,
            "business_area": [
                {"id": "dup", "display_name": "A"},
                {"id": "dup", "display_name": "B"},
            ],
            "development_role": [],
        },
    )
    cap = persona_catalog_persona_id_duplicates_operator_caption(s)
    assert cap is not None
    assert "2" in cap
    assert (
        persona_catalog_persona_id_duplicates_operator_caption(
            {"nonblank_persona_id_duplicate_row_count": 0},
        )
        is None
    )


def test_persona_catalog_display_name_duplicates_operator_caption() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "display_name": "Dup"},
            {"id": "b", "display_name": "dup"},
        ],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    cap = persona_catalog_display_name_duplicates_operator_caption(s)
    assert cap is not None
    assert "2" in cap


def test_persona_catalog_display_name_duplicates_operator_caption_none_when_unique() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "display_name": "Only"}],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    assert persona_catalog_display_name_duplicates_operator_caption(s) is None


def test_persona_catalog_taxonomy_scope_frozen_caption() -> None:
    cap = persona_catalog_taxonomy_scope_frozen_caption()
    assert "business_area" in cap
    assert "development_role" in cap
    assert "frozen" in cap.lower()
    assert "deferred" in cap.lower()


def test_persona_catalog_empty_id_operator_caption() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "", "display_name": "X"}],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    cap = persona_catalog_empty_id_operator_caption(s)
    assert cap is not None
    assert "1" in cap


def test_persona_catalog_empty_id_operator_caption_none_when_all_ids() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "display_name": "X"}],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    assert persona_catalog_empty_id_operator_caption(s) is None


def test_persona_catalog_persona_id_length_caption_none_when_ids_blank() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "  ", "display_name": "X"}],
        "development_role": [],
    }
    assert persona_catalog_persona_id_length_caption(cat) is None


def test_persona_catalog_persona_id_length_caption_mixed() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "ab", "display_name": "A"}],
        "development_role": [{"id": "longer-id", "display_name": "B"}],
    }
    cap = persona_catalog_persona_id_length_caption(cat)
    assert cap is not None
    assert "2" in cap and "9" in cap


def test_persona_catalog_display_name_length_caption_none_when_all_blank() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "display_name": "  "}],
        "development_role": [],
    }
    assert persona_catalog_display_name_length_caption(cat) is None


def test_persona_catalog_display_name_length_caption_mixed_lengths() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "display_name": "Hi"}],
        "development_role": [{"id": "b", "display_name": "Hello"}],
    }
    cap = persona_catalog_display_name_length_caption(cat)
    assert cap is not None
    assert "2" in cap and "5" in cap


def test_critique_pairings_operator_summary_from_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    s = critique_pairings_operator_summary(root)
    assert s["has_critique_pairings_yaml"] is True
    assert s["critique_pairings_yaml_relpath"] == "configs/personas/critique_pairings.yaml"
    assert s["version"] == 1
    assert s["producer_taxonomy_key_count"] == 13
    assert "agent_evaluator" not in (s.get("producer_taxonomy_keys") or [])
    assert set(s["producer_taxonomy_keys_sample"]) <= {
        "architect",
        "backend_writer",
        "code_researcher",
        "domain_researcher",
        "frontend_writer",
        "infra_writer",
        "integration_adapter_writer",
        "launch_test_writer",
        "module_integrator",
        "planner",
        "refactorer",
        "stitcher",
        "test_writer",
    }
    assert s["load_error"] is None
    assert s["critique_pairing_critic_role_entries_total"] == 39
    sample_rows = s["critique_pairing_critic_counts_by_producer_sample"]
    assert isinstance(sample_rows, list) and len(sample_rows) == 12
    by_p = {r["producer"]: int(r["critic_roles"]) for r in sample_rows}
    assert by_p == {
        "architect": 2,
        "backend_writer": 5,
        "code_researcher": 3,
        "domain_researcher": 3,
        "frontend_writer": 5,
        "infra_writer": 3,
        "integration_adapter_writer": 2,
        "launch_test_writer": 3,
        "module_integrator": 4,
        "planner": 2,
        "refactorer": 2,
        "stitcher": 3,
    }


def test_critique_pairings_operator_summary_missing_file(tmp_path: Path) -> None:
    s = critique_pairings_operator_summary(tmp_path)
    assert s["has_critique_pairings_yaml"] is False
    assert s["critique_pairings_yaml_relpath"] is None
    assert s["load_error"] is None
    assert s["critique_pairing_critic_role_entries_total"] == 0
    assert s["critique_pairing_critic_counts_by_producer_sample"] == []


def test_critique_pairings_operator_summary_bad_pairings_mapping(tmp_path: Path) -> None:
    d = tmp_path / "configs" / "personas"
    d.mkdir(parents=True)
    (d / "critique_pairings.yaml").write_text(
        "version: 1\npairings: []\n",
        encoding="utf-8",
    )
    s = critique_pairings_operator_summary(tmp_path)
    assert s["has_critique_pairings_yaml"] is True
    assert isinstance(s["load_error"], str) and "pairings" in s["load_error"]
    assert s["critique_pairing_critic_role_entries_total"] == 0


def test_critique_pairings_operator_summary_per_producer_counts(tmp_path: Path) -> None:
    d = tmp_path / "configs" / "personas"
    d.mkdir(parents=True)
    (d / "critique_pairings.yaml").write_text(
        "version: 1\npairings:\n  a:\n    - x\n  b:\n    - u\n    - v\n    - w\n",
        encoding="utf-8",
    )
    s = critique_pairings_operator_summary(tmp_path)
    assert s["load_error"] is None
    assert s["critique_pairing_critic_role_entries_total"] == 4
    rows = s["critique_pairing_critic_counts_by_producer_sample"]
    assert {r["producer"]: int(r["critic_roles"]) for r in rows} == {"a": 1, "b": 3}


def test_load_persona_shelves_catalog_from_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    cat = load_persona_shelves_catalog(root)
    assert cat.get("version") == 1
    ba = cat.get("business_area") or []
    dr = cat.get("development_role") or []
    assert any(isinstance(x, dict) and x.get("id") == "commerce" for x in ba)
    assert any(isinstance(x, dict) and x.get("id") == "backend_engineer" for x in dr)


def test_load_persona_shelves_catalog_operator_summary_matches_flat_count() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    cat = load_persona_shelves_catalog(root)
    summary = persona_catalog_operator_summary(cat)
    rows = persona_catalog_flat_rows(cat)
    assert summary["total_entries"] == len(rows)
    assert summary["business_area_count"] + summary["development_role_count"] == len(rows)
    bd = summary["probation_status_breakdown"]
    assert sum(bd.values()) == summary["total_entries"]
    by_shelf = summary["probation_status_breakdown_by_shelf"]
    assert set(by_shelf.keys()) == {"business_area", "development_role"}
    assert sum(by_shelf["business_area"].values()) == summary["business_area_count"]
    assert sum(by_shelf["development_role"].values()) == summary["development_role_count"]
    aggregated = {k: by_shelf["business_area"][k] + by_shelf["development_role"][k] for k in bd}
    assert aggregated == bd
    wi_by_shelf = summary["with_instructions_by_shelf"]
    assert set(wi_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wi_by_shelf["business_area"] + wi_by_shelf["development_role"]
        == summary["with_instructions"]
    )
    assert wi_by_shelf["business_area"] <= summary["business_area_count"]
    assert wi_by_shelf["development_role"] <= summary["development_role_count"]
    wcp_by_shelf = summary["with_capability_profile_by_shelf"]
    assert set(wcp_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wcp_by_shelf["business_area"] + wcp_by_shelf["development_role"]
        == summary["with_capability_profile"]
    )
    assert wcp_by_shelf["business_area"] <= summary["business_area_count"]
    assert wcp_by_shelf["development_role"] <= summary["development_role_count"]
    wbs_by_shelf = summary["with_boundary_statement_by_shelf"]
    assert set(wbs_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wbs_by_shelf["business_area"] + wbs_by_shelf["development_role"]
        == summary["with_boundary_statement"]
    )
    assert wbs_by_shelf["business_area"] <= summary["business_area_count"]
    assert wbs_by_shelf["development_role"] <= summary["development_role_count"]
    wat_by_shelf = summary["with_allowed_tools_by_shelf"]
    assert set(wat_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wat_by_shelf["business_area"] + wat_by_shelf["development_role"]
        == summary["with_allowed_tools"]
    )
    assert wat_by_shelf["business_area"] <= summary["business_area_count"]
    assert wat_by_shelf["development_role"] <= summary["development_role_count"]
    wsm_by_shelf = summary["with_success_metrics_by_shelf"]
    assert set(wsm_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wsm_by_shelf["business_area"] + wsm_by_shelf["development_role"]
        == summary["with_success_metrics"]
    )
    assert wsm_by_shelf["business_area"] <= summary["business_area_count"]
    assert wsm_by_shelf["development_role"] <= summary["development_role_count"]
    wvf_by_shelf = summary["with_version_field_by_shelf"]
    assert set(wvf_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wvf_by_shelf["business_area"] + wvf_by_shelf["development_role"]
        == summary["with_version_field"]
    )
    assert wvf_by_shelf["business_area"] <= summary["business_area_count"]
    assert wvf_by_shelf["development_role"] <= summary["development_role_count"]
    wps_by_shelf = summary["with_probation_status_by_shelf"]
    assert set(wps_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wps_by_shelf["business_area"] + wps_by_shelf["development_role"]
        == summary["with_probation_status"]
    )
    assert wps_by_shelf["business_area"] <= summary["business_area_count"]
    assert wps_by_shelf["development_role"] <= summary["development_role_count"]
    assert (
        summary["with_instructions"] + summary["without_instructions"] == summary["total_entries"]
    )
    woi_by_shelf = summary["without_instructions_by_shelf"]
    assert set(woi_by_shelf.keys()) == {"business_area", "development_role"}
    assert woi_by_shelf["business_area"] >= 0 and woi_by_shelf["development_role"] >= 0
    assert (
        wi_by_shelf["business_area"] + woi_by_shelf["business_area"]
        == summary["business_area_count"]
    )
    assert (
        wi_by_shelf["development_role"] + woi_by_shelf["development_role"]
        == summary["development_role_count"]
    )
    assert (
        woi_by_shelf["business_area"] + woi_by_shelf["development_role"]
        == summary["without_instructions"]
    )
    wocp_by_shelf = summary["without_capability_profile_by_shelf"]
    assert set(wocp_by_shelf.keys()) == {"business_area", "development_role"}
    assert (
        wcp_by_shelf["business_area"] + wocp_by_shelf["business_area"]
        == summary["business_area_count"]
    )
    assert (
        wcp_by_shelf["development_role"] + wocp_by_shelf["development_role"]
        == summary["development_role_count"]
    )
    assert (
        wocp_by_shelf["business_area"] + wocp_by_shelf["development_role"]
        == summary["without_capability_profile"]
    )
    assert (
        summary["with_capability_profile"] + summary["without_capability_profile"]
        == summary["total_entries"]
    )
    other_examples = summary["probation_status_breakdown_other_examples"]
    assert isinstance(other_examples, list)
    assert all(isinstance(e, str) and e.strip() == e and e for e in other_examples)
    assert len(other_examples) == len(set(other_examples))
    assert other_examples == sorted(other_examples)
    assert len(other_examples) <= 10
    assert len(other_examples) <= bd["other"]
    by_shelf_ox = summary["probation_status_breakdown_other_examples_by_shelf"]
    assert set(by_shelf_ox.keys()) == {"business_area", "development_role"}
    for sk in ("business_area", "development_role"):
        exs = by_shelf_ox[sk]
        assert isinstance(exs, list)
        assert len(exs) <= 10
        assert exs == sorted(exs)
        assert len(exs) == len(set(exs))
        shelf_other = summary["probation_status_breakdown_by_shelf"][sk]["other"]
        assert len(exs) <= shelf_other


def test_persona_catalog_operator_summary_optional_fields() -> None:
    cat = {
        "version": 2,
        "business_area": [
            {
                "id": "a",
                "instructions": "x",
                "allowed_tools": ["t"],
                "version": 1,
                "probation_status": "probation",
            },
            {"id": "b", "capability_profile": "p", "probation_status": "Beta"},
        ],
        "development_role": [
            {"id": "c", "success_metrics": ["m"], "probation_status": "promoted"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["catalog_version"] == 2
    assert s["total_entries"] == 3
    assert s["with_instructions"] == 1
    assert s["without_instructions"] == 2
    assert s["with_instructions"] + s["without_instructions"] == s["total_entries"]
    assert s["with_instructions_by_shelf"]["business_area"] == 1
    assert s["with_instructions_by_shelf"]["development_role"] == 0
    assert s["without_instructions_by_shelf"]["business_area"] == 1
    assert s["without_instructions_by_shelf"]["development_role"] == 1
    assert s["with_allowed_tools"] == 1
    assert s["with_capability_profile"] == 1
    assert s["without_capability_profile"] == 2
    assert s["with_capability_profile"] + s["without_capability_profile"] == s["total_entries"]
    assert s["without_capability_profile_by_shelf"]["business_area"] == 1
    assert s["without_capability_profile_by_shelf"]["development_role"] == 1
    assert s["with_success_metrics"] == 1
    assert s["with_version_field"] == 1
    assert s["with_probation_status"] == 3
    bd = s["probation_status_breakdown"]
    assert bd["probation"] == 1
    assert bd["promoted"] == 1
    assert bd["other"] == 1
    assert bd["unset"] == 0
    assert bd["shelved"] == 0
    by_shelf = s["probation_status_breakdown_by_shelf"]
    assert by_shelf["business_area"]["probation"] == 1
    assert by_shelf["business_area"]["other"] == 1
    assert by_shelf["business_area"]["promoted"] == 0
    assert by_shelf["development_role"]["promoted"] == 1
    assert by_shelf["development_role"]["probation"] == 0
    assert sum(by_shelf["business_area"].values()) == 2
    assert sum(by_shelf["development_role"].values()) == 1


def test_persona_catalog_operator_summary_legacy_entries_count_as_unset_per_shelf() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a"}, {"id": "b"}],
        "development_role": [{"id": "c"}],
    }
    s = persona_catalog_operator_summary(cat)
    by_shelf = s["probation_status_breakdown_by_shelf"]
    assert by_shelf["business_area"]["unset"] == 2
    assert by_shelf["development_role"]["unset"] == 1
    assert s["probation_status_breakdown"]["unset"] == 3
    assert s["with_probation_status"] == 0
    wi_by_shelf = s["with_instructions_by_shelf"]
    assert wi_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_instructions"] == 0
    woi_by_shelf = s["without_instructions_by_shelf"]
    assert woi_by_shelf == {"business_area": 2, "development_role": 1}
    assert s["without_instructions"] == 3
    assert s["with_instructions"] + s["without_instructions"] == s["total_entries"]
    wcp_by_shelf = s["with_capability_profile_by_shelf"]
    assert wcp_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_capability_profile"] == 0
    wocp_by_shelf = s["without_capability_profile_by_shelf"]
    assert wocp_by_shelf == {"business_area": 2, "development_role": 1}
    assert s["without_capability_profile"] == 3
    assert s["with_capability_profile"] + s["without_capability_profile"] == s["total_entries"]
    wbs_by_shelf = s["with_boundary_statement_by_shelf"]
    assert wbs_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_boundary_statement"] == 0
    wat_by_shelf = s["with_allowed_tools_by_shelf"]
    assert wat_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_allowed_tools"] == 0
    wsm_by_shelf = s["with_success_metrics_by_shelf"]
    assert wsm_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_success_metrics"] == 0
    wvf_by_shelf = s["with_version_field_by_shelf"]
    assert wvf_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_version_field"] == 0
    wps_by_shelf = s["with_probation_status_by_shelf"]
    assert wps_by_shelf == {"business_area": 0, "development_role": 0}
    assert s["with_probation_status"] == 0


def test_persona_catalog_operator_summary_with_capability_profile_by_shelf_mixed() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "capability_profile": "trusted advisor"},
            {"id": "b", "capability_profile": "   "},
        ],
        "development_role": [
            {"id": "c", "capability_profile": "engineer"},
            {"id": "d", "capability_profile": "ops"},
            {"id": "e"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wcp_by_shelf = s["with_capability_profile_by_shelf"]
    assert wcp_by_shelf["business_area"] == 1
    assert wcp_by_shelf["development_role"] == 2
    assert (
        wcp_by_shelf["business_area"] + wcp_by_shelf["development_role"]
        == s["with_capability_profile"]
        == 3
    )
    wocp_by_shelf = s["without_capability_profile_by_shelf"]
    assert wocp_by_shelf["business_area"] == 1
    assert wocp_by_shelf["development_role"] == 1
    assert s["without_capability_profile"] == 2
    assert s["with_capability_profile"] + s["without_capability_profile"] == s["total_entries"]


def test_persona_catalog_operator_summary_non_string_capability_counts_without() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "capability_profile": 99}],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_capability_profile"] == 0
    assert s["without_capability_profile"] == 1
    assert s["without_capability_profile_by_shelf"] == {"business_area": 1, "development_role": 0}


def test_persona_catalog_operator_summary_with_instructions_by_shelf_mixed_shelves() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "instructions": "do the thing"},
            {"id": "b", "instructions": "   "},
            {"id": "c", "instructions": "another"},
        ],
        "development_role": [
            {"id": "d", "instructions": "engineer note"},
            {"id": "e"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wi_by_shelf = s["with_instructions_by_shelf"]
    assert wi_by_shelf["business_area"] == 2
    assert wi_by_shelf["development_role"] == 1
    assert (
        wi_by_shelf["business_area"] + wi_by_shelf["development_role"]
        == s["with_instructions"]
        == 3
    )
    woi_by_shelf = s["without_instructions_by_shelf"]
    assert woi_by_shelf["business_area"] == 1
    assert woi_by_shelf["development_role"] == 1
    assert s["without_instructions"] == 2
    assert s["with_instructions"] + s["without_instructions"] == s["total_entries"]


def test_persona_catalog_operator_summary_all_instructions_populated_zero_without() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "instructions": "one"},
            {"id": "b", "instructions": "two"},
        ],
        "development_role": [
            {"id": "c", "instructions": "three"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_instructions"] == 3
    assert s["without_instructions"] == 0
    assert s["without_instructions_by_shelf"] == {
        "business_area": 0,
        "development_role": 0,
    }


def test_persona_catalog_operator_summary_without_instructions_by_shelf_split() -> None:
    """business_area: 2 with / 1 without; development_role: 0 with / 1 without."""
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "instructions": "x"},
            {"id": "b", "instructions": "y"},
            {"id": "c"},
        ],
        "development_role": [
            {"id": "d"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_instructions_by_shelf"] == {"business_area": 2, "development_role": 0}
    assert s["without_instructions_by_shelf"] == {"business_area": 1, "development_role": 1}
    assert s["with_instructions"] == 2
    assert s["without_instructions"] == 2


def test_persona_catalog_operator_summary_whitespace_none_instructions_count_without() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "instructions": "   "},
            {"id": "b", "instructions": None},
        ],
        "development_role": [{"id": "c"}],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_instructions"] == 0
    assert s["without_instructions"] == 3
    assert s["without_instructions_by_shelf"] == {
        "business_area": 2,
        "development_role": 1,
    }


def test_persona_catalog_operator_summary_non_string_instructions_count_without() -> None:
    cat = {
        "version": 1,
        "business_area": [{"id": "a", "instructions": 99}],
        "development_role": [],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_instructions"] == 0
    assert s["without_instructions"] == 1
    assert s["without_instructions_by_shelf"] == {"business_area": 1, "development_role": 0}


def test_persona_catalog_operator_summary_with_boundary_statement_by_shelf_mixed() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "boundary_statement": "never exceed scope"},
            {"id": "b", "boundary_statement": "   "},
            {"id": "c"},
        ],
        "development_role": [
            {"id": "d", "boundary_statement": "no production data"},
            {"id": "e", "boundary_statement": "no destructive ops"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wbs_by_shelf = s["with_boundary_statement_by_shelf"]
    assert wbs_by_shelf["business_area"] == 1
    assert wbs_by_shelf["development_role"] == 2
    assert (
        wbs_by_shelf["business_area"] + wbs_by_shelf["development_role"]
        == s["with_boundary_statement"]
        == 3
    )


def test_persona_catalog_operator_summary_with_allowed_tools_and_success_metrics_by_shelf_mixed() -> (
    None
):
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "allowed_tools": ["t1"], "success_metrics": ["m1"]},
            {
                "id": "b",
                "allowed_tools": [],
                "success_metrics": ["m2", "m3"],
            },
            {"id": "c"},
        ],
        "development_role": [
            {"id": "d", "allowed_tools": ["t2"], "success_metrics": ["m4"]},
            {
                "id": "e",
                "allowed_tools": ["t3", "t4"],
                "success_metrics": [],
            },
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wat_by_shelf = s["with_allowed_tools_by_shelf"]
    assert wat_by_shelf["business_area"] == 1
    assert wat_by_shelf["development_role"] == 2
    assert (
        wat_by_shelf["business_area"] + wat_by_shelf["development_role"]
        == s["with_allowed_tools"]
        == 3
    )
    wsm_by_shelf = s["with_success_metrics_by_shelf"]
    assert wsm_by_shelf["business_area"] == 2
    assert wsm_by_shelf["development_role"] == 1
    assert (
        wsm_by_shelf["business_area"] + wsm_by_shelf["development_role"]
        == s["with_success_metrics"]
        == 3
    )


def test_persona_catalog_operator_summary_non_list_allowed_tools_success_metrics_skip_per_shelf() -> (
    None
):
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "allowed_tools": "not-a-list", "success_metrics": None},
            {"id": "b", "allowed_tools": [], "success_metrics": []},
            {"id": "c", "allowed_tools": {"x": 1}, "success_metrics": 5},
        ],
        "development_role": [
            {"id": "d", "allowed_tools": None, "success_metrics": "metric"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_allowed_tools"] == 0
    assert s["with_success_metrics"] == 0
    assert s["with_allowed_tools_by_shelf"] == {
        "business_area": 0,
        "development_role": 0,
    }
    assert s["with_success_metrics_by_shelf"] == {
        "business_area": 0,
        "development_role": 0,
    }


def test_persona_catalog_operator_summary_with_version_field_by_shelf_mixed() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "version": 1},
            {"id": "b", "version": "2.0"},
            {"id": "c"},
        ],
        "development_role": [
            {"id": "d"},
            {"id": "e", "version": 3},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wvf_by_shelf = s["with_version_field_by_shelf"]
    assert wvf_by_shelf["business_area"] == 2
    assert wvf_by_shelf["development_role"] == 1
    assert (
        wvf_by_shelf["business_area"] + wvf_by_shelf["development_role"]
        == s["with_version_field"]
        == 3
    )


def test_persona_catalog_operator_summary_with_version_field_by_shelf_blank_values_skip() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "version": None},
            {"id": "b", "version": ""},
            {"id": "c", "version": "   "},
        ],
        "development_role": [
            {"id": "d", "version": None},
            {"id": "e", "version": ""},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_version_field"] == 0
    assert s["with_version_field_by_shelf"] == {
        "business_area": 0,
        "development_role": 0,
    }


def test_persona_catalog_operator_summary_with_version_field_by_shelf_one_zero_split() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "version": 1},
            {"id": "b"},
            {"id": "c"},
        ],
        "development_role": [
            {"id": "d", "version": 7},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wvf_by_shelf = s["with_version_field_by_shelf"]
    assert wvf_by_shelf["business_area"] == 1
    assert wvf_by_shelf["development_role"] == 1
    assert s["with_version_field"] == 2


def test_persona_catalog_operator_summary_with_probation_status_by_shelf_mixed() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "probation_status": "probation"},
            {"id": "b", "probation_status": "Beta"},
            {"id": "c"},
        ],
        "development_role": [
            {"id": "d"},
            {"id": "e", "probation_status": "promoted"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wps_by_shelf = s["with_probation_status_by_shelf"]
    assert wps_by_shelf["business_area"] == 2
    assert wps_by_shelf["development_role"] == 1
    assert (
        wps_by_shelf["business_area"] + wps_by_shelf["development_role"]
        == s["with_probation_status"]
        == 3
    )


def test_persona_catalog_operator_summary_with_probation_status_by_shelf_blank_skip() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "probation_status": None},
            {"id": "b", "probation_status": ""},
            {"id": "c", "probation_status": "   "},
        ],
        "development_role": [
            {"id": "d", "probation_status": None},
            {"id": "e", "probation_status": ""},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["with_probation_status"] == 0
    assert s["with_probation_status_by_shelf"] == {
        "business_area": 0,
        "development_role": 0,
    }


def test_persona_catalog_operator_summary_with_probation_status_by_shelf_zero_one_split() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a"},
            {"id": "b", "probation_status": "   "},
        ],
        "development_role": [
            {"id": "c", "probation_status": "promoted"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    wps_by_shelf = s["with_probation_status_by_shelf"]
    assert wps_by_shelf["business_area"] == 0
    assert wps_by_shelf["development_role"] == 1
    assert s["with_probation_status"] == 1


def test_filter_persona_catalog_flat_rows_query_and_shelf() -> None:
    rows = [
        {"shelf": "business_area", "id": "commerce", "display_name": "Commerce"},
        {"shelf": "development_role", "id": "backend_engineer", "display_name": "BE"},
    ]
    assert len(filter_persona_catalog_flat_rows(rows, query="comm")) == 1
    assert filter_persona_catalog_flat_rows(rows, query="comm")[0]["id"] == "commerce"
    assert len(filter_persona_catalog_flat_rows(rows, shelf="development_role")) == 1
    assert len(filter_persona_catalog_flat_rows(rows, query="xx")) == 0


def test_persona_catalog_distinct_allowed_tools() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "allowed_tools": ["Read", "write"]},
            {"id": "b", "allowed_tools": ["write", "  "]},
        ],
        "development_role": [{"id": "c", "allowed_tools": "not-a-list"}],
    }
    tools = persona_catalog_distinct_allowed_tools(cat)
    assert tools == ["Read", "write"]


def test_filter_persona_catalog_flat_rows_allowed_tool() -> None:
    rows = [
        {"id": "a", "allowed_tools": ["grep", "Read"]},
        {"id": "b", "allowed_tools": ["Write"]},
        {"id": "c"},
    ]
    assert len(filter_persona_catalog_flat_rows(rows, allowed_tool="grep")) == 1
    assert filter_persona_catalog_flat_rows(rows, allowed_tool="grep")[0]["id"] == "a"
    assert len(filter_persona_catalog_flat_rows(rows, allowed_tool="all")) == 3
    assert len(filter_persona_catalog_flat_rows(rows, allowed_tool="")) == 3
    assert len(filter_persona_catalog_flat_rows(rows, allowed_tool="Write")) == 1


def test_filter_persona_catalog_flat_rows_allowed_tool_with_probation() -> None:
    rows = [
        {"id": "a", "probation_status": "probation", "allowed_tools": ["grep"]},
        {"id": "b", "probation_status": "promoted", "allowed_tools": ["grep"]},
    ]
    out = filter_persona_catalog_flat_rows(
        rows,
        probation_status="probation",
        allowed_tool="grep",
    )
    assert len(out) == 1
    assert out[0]["id"] == "a"


def test_persona_catalog_allowed_tool_filter_caption() -> None:
    assert persona_catalog_allowed_tool_filter_caption("all", match_count=1, total_count=2) is None
    cap = persona_catalog_allowed_tool_filter_caption("grep", match_count=1, total_count=3)
    assert cap is not None
    assert "**grep**" in cap
    assert "**1**" in cap
    assert "**3**" in cap


def test_filter_persona_catalog_flat_rows_probation_status() -> None:
    rows = [
        {
            "shelf": "business_area",
            "id": "a",
            "display_name": "A",
            "probation_status": "probation",
        },
        {"shelf": "business_area", "id": "b", "display_name": "B", "probation_status": "promoted"},
        {"shelf": "business_area", "id": "c", "display_name": "C"},
    ]
    assert len(filter_persona_catalog_flat_rows(rows, probation_status="probation")) == 1
    assert filter_persona_catalog_flat_rows(rows, probation_status="probation")[0]["id"] == "a"
    assert len(filter_persona_catalog_flat_rows(rows, probation_status="(unset)")) == 1
    assert filter_persona_catalog_flat_rows(rows, probation_status="(unset)")[0]["id"] == "c"
    assert len(filter_persona_catalog_flat_rows(rows, probation_status="all")) == 3


def test_persona_catalog_flat_rows_csv_round_trip_header() -> None:
    rows = [{"shelf": "business_area", "id": "x", "display_name": "X", "extra": 1}]
    csv_text = persona_catalog_flat_rows_csv(rows)
    assert "shelf" in csv_text and "business_area" in csv_text
    assert csv_text.splitlines()[0].startswith("shelf,")


def test_persona_catalog_flat_rows_csv_empty() -> None:
    assert persona_catalog_flat_rows_csv([]) == ""


def test_persona_catalog_operator_summary_other_examples_legacy_only_empty() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a"},
            {"id": "b"},
        ],
        "development_role": [
            {"id": "c"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["probation_status_breakdown_other_examples"] == []
    assert s["probation_status_breakdown"]["other"] == 0
    assert s["probation_status_breakdown_other_examples_by_shelf"]["business_area"] == []
    assert s["probation_status_breakdown_other_examples_by_shelf"]["development_role"] == []


def test_persona_catalog_operator_summary_other_examples_canonical_only_empty() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "probation_status": "probation"},
            {"id": "b", "probation_status": "PROMOTED"},
            {"id": "c", "probation_status": "Shelved"},
        ],
        "development_role": [
            {"id": "d", "probation_status": "probation"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["probation_status_breakdown_other_examples"] == []
    assert s["probation_status_breakdown"]["other"] == 0
    assert s["probation_status_breakdown_other_examples_by_shelf"]["business_area"] == []
    assert s["probation_status_breakdown_other_examples_by_shelf"]["development_role"] == []


def test_persona_catalog_operator_summary_other_examples_mixed_sorts_and_dedupes() -> None:
    cat = {
        "version": 1,
        "business_area": [
            {"id": "a", "probation_status": "Beta"},
            {"id": "b", "probation_status": "needs review"},
            {"id": "c", "probation_status": "Beta"},
            {"id": "d", "probation_status": "   "},
            {"id": "e", "probation_status": "probation"},
        ],
        "development_role": [
            {"id": "f", "probation_status": "Awaiting"},
        ],
    }
    s = persona_catalog_operator_summary(cat)
    assert s["probation_status_breakdown_other_examples"] == [
        "Awaiting",
        "Beta",
        "needs review",
    ]
    assert s["probation_status_breakdown"]["other"] == 4
    assert s["probation_status_breakdown_other_examples_by_shelf"]["business_area"] == [
        "Beta",
        "needs review",
    ]
    assert s["probation_status_breakdown_other_examples_by_shelf"]["development_role"] == [
        "Awaiting",
    ]


def test_persona_catalog_operator_summary_other_examples_caps_at_ten() -> None:
    raw_values = [
        "Alpha",
        "Beta",
        "Gamma",
        "Delta",
        "Epsilon",
        "Zeta",
        "Eta",
        "Theta",
        "Iota",
        "Kappa",
        "Lambda",
        "Mu",
    ]
    cat = {
        "version": 1,
        "business_area": [
            {"id": f"ba_{i}", "probation_status": v} for i, v in enumerate(raw_values[:6])
        ],
        "development_role": [
            {"id": f"dr_{i}", "probation_status": v} for i, v in enumerate(raw_values[6:])
        ],
    }
    s = persona_catalog_operator_summary(cat)
    examples = s["probation_status_breakdown_other_examples"]
    assert isinstance(examples, list)
    assert len(examples) == 10
    assert examples == sorted(examples)
    assert set(examples) <= set(raw_values)
    assert all(e in raw_values for e in examples)
    assert s["probation_status_breakdown"]["other"] == 12
    ba_ex = s["probation_status_breakdown_other_examples_by_shelf"]["business_area"]
    dr_ex = s["probation_status_breakdown_other_examples_by_shelf"]["development_role"]
    assert len(ba_ex) == 6 and ba_ex == sorted(ba_ex)
    assert len(dr_ex) == 6 and dr_ex == sorted(dr_ex)
    assert set(ba_ex) | set(dr_ex) == set(raw_values)


def test_persona_catalog_operator_summary_other_examples_by_shelf_one_shelf_caps_at_ten() -> None:
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    cat = {
        "version": 1,
        "business_area": [{"id": f"p{i}", "probation_status": letters[i]} for i in range(12)],
        "development_role": [{"id": "x", "probation_status": "probation"}],
    }
    s = persona_catalog_operator_summary(cat)
    ba_ex = s["probation_status_breakdown_other_examples_by_shelf"]["business_area"]
    assert len(ba_ex) == 10
    assert ba_ex == sorted(letters[:12])[:10]
    assert s["probation_status_breakdown_other_examples_by_shelf"]["development_role"] == []


def test_persona_probation_other_examples_by_shelf_table_rows() -> None:
    summary = {
        "probation_status_breakdown_other_examples_by_shelf": {
            "development_role": ["Beta", "needs review"],
            "business_area": ["Custom"],
        },
    }
    rows = persona_probation_other_examples_by_shelf_table_rows(summary)
    assert rows == [
        {"shelf": "business_area", "other_probation_status_examples": "Custom"},
        {
            "shelf": "development_role",
            "other_probation_status_examples": "Beta, needs review",
        },
    ]


def test_persona_probation_other_examples_by_shelf_table_rows_empty() -> None:
    assert persona_probation_other_examples_by_shelf_table_rows({}) == []
    assert persona_probation_other_examples_by_shelf_table_rows({"x": 1}) == []


def test_persona_probation_other_by_shelf_export_json_and_csv() -> None:
    summary = {
        "probation_status_breakdown_other_examples_by_shelf": {
            "development_role": ["Beta", "needs review"],
            "business_area": ["Custom"],
        },
    }
    rows = persona_probation_other_examples_by_shelf_table_rows(summary)
    parsed = json.loads(persona_probation_other_by_shelf_export_json(rows))
    assert parsed == rows
    csv_text = persona_probation_other_by_shelf_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "shelf,other_probation_status_examples"
    assert "development_role" in csv_text
    assert "Beta, needs review" in csv_text or '"Beta, needs review"' in csv_text
    assert persona_probation_other_by_shelf_export_json([]) == "[]"
    assert persona_probation_other_by_shelf_table_rows_csv([]) == ""


def test_persona_probation_other_export_filename_slug() -> None:
    assert persona_probation_other_export_filename_slug() == "persona_probation_other"


def test_critique_pairings_producer_keys_export_json_and_csv() -> None:
    summary = {
        "producer_taxonomy_keys_sample": ["planner", "implementation"],
    }
    rows = critique_pairings_producer_keys_table_rows(summary)
    assert rows == [
        {"producer_key": "planner"},
        {"producer_key": "implementation"},
    ]
    parsed = json.loads(critique_pairings_producer_keys_export_json(rows))
    assert parsed == rows
    csv_text = critique_pairings_producer_keys_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "producer_key"
    assert "planner" in csv_text
    assert critique_pairings_producer_keys_table_rows({}) == []
    assert critique_pairings_producer_keys_export_json([]) == "[]"
    assert critique_pairings_producer_keys_table_rows_csv([]) == ""


def test_critique_pairings_producer_keys_table_rows_real_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    s = critique_pairings_operator_summary(root)
    if not s.get("has_critique_pairings_yaml"):
        return
    rows = critique_pairings_producer_keys_table_rows(s)
    sample = s.get("producer_taxonomy_keys_sample")
    assert isinstance(sample, list)
    if sample:
        assert rows == [
            {"producer_key": str(k).strip()}
            for k in sample
            if isinstance(k, str) and str(k).strip()
        ]
    all_rows = critique_pairings_producer_keys_all_table_rows(s)
    full = s.get("producer_taxonomy_keys")
    assert isinstance(full, list)
    if full:
        assert len(all_rows) == len(full)
        assert all_rows == [
            {"producer_key": str(k).strip()} for k in full if isinstance(k, str) and str(k).strip()
        ]


def test_critique_pairings_producer_keys_all_table_rows_thirteen_keys() -> None:
    keys = [f"producer_{i}" for i in range(13)]
    summary = {
        "producer_taxonomy_keys": keys,
        "producer_taxonomy_keys_sample": keys[:12],
    }
    all_rows = critique_pairings_producer_keys_all_table_rows(summary)
    sample_rows = critique_pairings_producer_keys_table_rows(summary)
    assert len(all_rows) == 13
    assert len(sample_rows) == 12
    parsed = json.loads(critique_pairings_producer_keys_all_export_json(all_rows))
    assert parsed == all_rows
    csv_text = critique_pairings_producer_keys_all_table_rows_csv(all_rows)
    assert csv_text.splitlines()[0] == "producer_key"
    assert "producer_12" in csv_text


def test_critique_pairings_producer_keys_all_table_rows_two_keys() -> None:
    summary = {
        "producer_taxonomy_keys": ["planner", "implementation"],
        "producer_taxonomy_keys_sample": ["planner", "implementation"],
    }
    all_rows = critique_pairings_producer_keys_all_table_rows(summary)
    sample_rows = critique_pairings_producer_keys_table_rows(summary)
    assert all_rows == sample_rows
    assert len(all_rows) == 2


def test_critique_pairings_critic_counts_export_json_and_csv() -> None:
    summary = {
        "critique_pairing_critic_counts_by_producer_sample": [
            {"producer": "implementation", "critic_roles": "2"},
            {"producer": "planner", "critic_roles": "1"},
        ],
    }
    rows = critique_pairings_critic_counts_table_rows(summary)
    assert len(rows) == 2
    assert rows[0]["producer"] == "implementation"
    parsed = json.loads(critique_pairings_critic_counts_export_json(rows))
    assert parsed == rows
    csv_text = critique_pairings_critic_counts_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "producer,critic_roles"
    assert "implementation,2" in csv_text
    assert critique_pairings_critic_counts_table_rows({}) == []
    assert critique_pairings_critic_counts_table_rows({"x": 1}) == []
    assert critique_pairings_critic_counts_export_json([]) == "[]"
    assert critique_pairings_critic_counts_table_rows_csv([]) == ""


def test_critique_pairings_critic_counts_table_rows_real_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    s = critique_pairings_operator_summary(root)
    if not s.get("has_critique_pairings_yaml"):
        return
    rows = critique_pairings_critic_counts_table_rows(s)
    sample = s.get("critique_pairing_critic_counts_by_producer_sample")
    assert isinstance(sample, list)
    if sample:
        assert rows == [
            {
                "producer": str(item["producer"]).strip(),
                "critic_roles": str(item["critic_roles"]),
            }
            for item in sample
            if isinstance(item, dict) and isinstance(item.get("producer"), str)
        ]
    all_rows = critique_pairings_critic_counts_all_table_rows(s)
    full = s.get("critique_pairing_critic_counts_by_producer")
    count = s.get("producer_taxonomy_key_count")
    assert isinstance(full, list)
    if isinstance(count, int) and count > 0:
        assert len(all_rows) == count


def test_critique_pairings_critic_counts_all_table_rows_thirteen_producers(
    tmp_path: Path,
) -> None:
    pairings = {f"producer_{i}": ["critic_a"] for i in range(13)}
    yaml_text = "version: 1\npairings:\n"
    for pk in sorted(pairings):
        yaml_text += f"  {pk}:\n    - critic_a\n"
    path = tmp_path / "configs" / "personas"
    path.mkdir(parents=True)
    (path / "critique_pairings.yaml").write_text(yaml_text, encoding="utf-8")
    s = critique_pairings_operator_summary(tmp_path)
    assert s["producer_taxonomy_key_count"] == 13
    full = s["critique_pairing_critic_counts_by_producer"]
    sample = s["critique_pairing_critic_counts_by_producer_sample"]
    assert len(full) == 13
    assert len(sample) == 12
    all_rows = critique_pairings_critic_counts_all_table_rows(s)
    sample_rows = critique_pairings_critic_counts_table_rows(s)
    assert len(all_rows) == 13
    assert len(sample_rows) == 12
    assert {r["producer"] for r in all_rows} == {f"producer_{i}" for i in range(13)}
    assert all(r["critic_roles"] == "1" for r in all_rows)
    parsed = json.loads(critique_pairings_critic_counts_all_export_json(all_rows))
    assert len(parsed) == 13
    csv_text = critique_pairings_critic_counts_all_table_rows_csv(all_rows)
    assert csv_text.splitlines()[0] == "producer,critic_roles"


def test_critique_pairings_critic_counts_all_table_rows_at_most_twelve() -> None:
    summary = {
        "critique_pairing_critic_counts_by_producer": [
            {"producer": "planner", "critic_roles": "1"},
        ],
        "critique_pairing_critic_counts_by_producer_sample": [
            {"producer": "planner", "critic_roles": "1"},
        ],
    }
    all_rows = critique_pairings_critic_counts_all_table_rows(summary)
    sample_rows = critique_pairings_critic_counts_table_rows(summary)
    assert all_rows == sample_rows


def test_critique_pairings_operator_summary_export_json(tmp_path: Path) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    s = critique_pairings_operator_summary(root)
    parsed = json.loads(critique_pairings_operator_summary_export_json(s))
    assert parsed == s
    if s.get("has_critique_pairings_yaml"):
        assert "producer_taxonomy_key_count" in parsed

    missing = critique_pairings_operator_summary(tmp_path)
    assert missing["has_critique_pairings_yaml"] is False
    assert (
        json.loads(critique_pairings_operator_summary_export_json(missing))[
            "has_critique_pairings_yaml"
        ]
        is False
    )

    cp_dir = tmp_path / "configs" / "personas"
    cp_dir.mkdir(parents=True)
    (cp_dir / "critique_pairings.yaml").write_text("not: [valid", encoding="utf-8")
    bad = critique_pairings_operator_summary(tmp_path)
    assert bad["has_critique_pairings_yaml"] is True
    bad_parsed = json.loads(critique_pairings_operator_summary_export_json(bad))
    assert isinstance(bad_parsed.get("load_error"), str)
    assert bad_parsed["load_error"]

    assert critique_pairings_export_filename_slug() == "critique_pairings"
    assert critique_pairings_operator_summary_export_json(None) == "{}"


def test_critique_pairings_operator_summary_operator_metrics_from_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    s = critique_pairings_operator_summary(root)
    m = critique_pairings_operator_summary_operator_metrics(s)
    if s.get("has_critique_pairings_yaml") and not s.get("load_error"):
        assert m["has_critique_pairings_yaml"] is True
        cap = critique_pairings_operator_summary_operator_metrics_caption(m)
        assert cap is not None


def test_critique_pairings_operator_summary_operator_metrics_missing_yaml(
    tmp_path: Path,
) -> None:
    s = critique_pairings_operator_summary(tmp_path)
    m = critique_pairings_operator_summary_operator_metrics(s)
    assert m["has_critique_pairings_yaml"] is False
    assert critique_pairings_operator_summary_operator_metrics_caption(m) is None


def test_critique_pairings_operator_summary_operator_metrics_load_error(
    tmp_path: Path,
) -> None:
    cp_dir = tmp_path / "configs" / "personas"
    cp_dir.mkdir(parents=True)
    (cp_dir / "critique_pairings.yaml").write_text("not: [valid", encoding="utf-8")
    s = critique_pairings_operator_summary(tmp_path)
    m = critique_pairings_operator_summary_operator_metrics(s)
    assert m["load_error_present"] is True
    cap = critique_pairings_operator_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "load error" in cap.lower()


def test_critique_pairings_operator_summary_operator_metrics_export() -> None:
    m = critique_pairings_operator_summary_operator_metrics(
        {
            "has_critique_pairings_yaml": True,
            "producer_taxonomy_key_count": 2,
            "critique_pairing_critic_role_entries_total": 5,
        },
    )
    parsed = json.loads(critique_pairings_operator_summary_operator_metrics_export_json(m))
    assert parsed["critic_role_entries_total"] == 5
    rows = critique_pairings_operator_summary_operator_metrics_table_rows(m)
    csv_text = critique_pairings_operator_summary_operator_metrics_table_rows_csv(rows)
    assert "Producer taxonomy keys" in csv_text
    assert (
        critique_pairings_operator_summary_operator_metrics_export_filename_slug()
        == "critique_pairings_operator_summary_operator_metrics"
    )


def test_persona_catalog_flat_rows_export_json_roundtrip() -> None:
    rows = [
        {
            "shelf": "business_area",
            "id": "a1",
            "display_name": "Alpha",
            "allowed_tools": ["lint"],
        },
        {
            "shelf": "development_role",
            "id": "b2",
            "display_name": "Beta",
            "success_metrics": ["coverage"],
        },
    ]
    parsed = json.loads(persona_catalog_flat_rows_export_json(rows))
    assert len(parsed) == 2
    assert parsed[0]["allowed_tools"] == ["lint"]
    assert parsed[1]["success_metrics"] == ["coverage"]


def test_persona_catalog_flat_rows_export_json_empty() -> None:
    assert json.loads(persona_catalog_flat_rows_export_json([])) == []
    assert json.loads(persona_catalog_flat_rows_export_json(None)) == []  # type: ignore[arg-type]


def test_persona_catalog_flat_export_filename_slug() -> None:
    assert persona_catalog_flat_export_filename_slug() == "persona_flat"


def test_load_persona_shelves_catalog_db_mode_freshness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Console reads Postgres shelves when DB mode is on (no stale YAML)."""
    import yaml

    from nimbusware_config.keys import KEY_PERSONA_SHELVES, NS_PERSONAS
    from nimbusware_config.materializer import ConfigMaterializer
    from nimbusware_config.store import InMemoryConfigStore

    shelves = {
        "version": 1,
        "business_area": [{"id": "commerce", "display_name": "C", "version": 1}],
        "development_role": [{"id": "be", "display_name": "BE", "version": 1}],
    }
    personas_dir = tmp_path / "configs" / "personas"
    personas_dir.mkdir(parents=True)
    shelves_path = personas_dir / "shelves.yaml"
    shelves_path.write_text(yaml.safe_dump(shelves, sort_keys=False), encoding="utf-8")
    mtime_before = shelves_path.stat().st_mtime

    store = InMemoryConfigStore()
    store.upsert(NS_PERSONAS, KEY_PERSONA_SHELVES, shelves)
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)

    monkeypatch.setenv("NIMBUSWARE_CONFIG_FROM_DB", "1")
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://test")

    import nimbusware_console.config_materializer as cm

    monkeypatch.setattr(cm, "ConfigMaterializer", lambda repo: mat)

    updated = dict(shelves)
    updated["business_area"] = [
        {
            "id": "commerce",
            "display_name": "C",
            "version": 1,
            "instructions": "From DB only.",
        },
    ]
    store.upsert(NS_PERSONAS, KEY_PERSONA_SHELVES, updated)

    catalog = load_persona_shelves_catalog(tmp_path)
    entry = next(e for e in catalog["business_area"] if e["id"] == "commerce")
    assert entry.get("instructions") == "From DB only."
    assert shelves_path.stat().st_mtime == mtime_before

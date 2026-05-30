"""Console bundle catalog helper (follow-on 24 §14 #12)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

from nimbusware_console.bundle_catalog import (
    BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH,
    bundle_catalog_bundle_count_caption,
    bundle_catalog_bundle_ids_sample,
    bundle_catalog_bundles_without_id_caption,
    bundle_catalog_bundles_without_id_count,
    bundle_catalog_bundles_without_id_rollup,
    bundle_catalog_bundles_without_id_rollup_export_filename_slug,
    bundle_catalog_bundles_without_id_rollup_export_json,
    bundle_catalog_bundles_without_id_rollup_operator_metrics,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_caption,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv,
    bundle_catalog_bundles_without_id_rollup_table_rows,
    bundle_catalog_bundles_without_id_rollup_table_rows_csv,
    bundle_catalog_bundles_without_tags_caption,
    bundle_catalog_bundles_without_tags_count,
    bundle_catalog_bundles_without_tags_rollup,
    bundle_catalog_bundles_without_tags_rollup_export_filename_slug,
    bundle_catalog_bundles_without_tags_rollup_export_json,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_filename_slug,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_json,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows_csv,
    bundle_catalog_bundles_without_tags_rollup_table_rows,
    bundle_catalog_bundles_without_tags_rollup_table_rows_csv,
    bundle_catalog_distinct_tag_count_caption,
    bundle_catalog_distinct_tags_sample,
    bundle_catalog_local_bundles,
    bundle_catalog_local_bundles_export_json,
    bundle_catalog_local_bundles_table_rows,
    bundle_catalog_local_bundles_table_rows_csv,
    bundle_catalog_local_summary,
    bundle_catalog_local_summary_export_filename_slug,
    bundle_catalog_local_summary_export_json,
    bundle_catalog_local_summary_operator_metrics,
    bundle_catalog_local_summary_operator_metrics_caption,
    bundle_catalog_local_summary_operator_metrics_export_filename_slug,
    bundle_catalog_local_summary_operator_metrics_export_json,
    bundle_catalog_local_summary_operator_metrics_table_rows,
    bundle_catalog_local_summary_operator_metrics_table_rows_csv,
    bundle_catalog_local_summary_table_rows,
    bundle_catalog_local_summary_table_rows_csv,
    bundle_catalog_top_tag_caption,
    bundle_catalog_top_tag_counts,
    bundle_catalog_top_tag_counts_export_json,
    bundle_catalog_top_tag_counts_table_rows_csv,
    bundle_faiss_build_command_snippet,
    bundle_faiss_build_command_snippet_explicit,
    bundle_faiss_build_powershell_snippet_explicit,
    bundle_faiss_bundle_order_duplicate_ids_caption,
    bundle_faiss_bundle_order_json_file_bytes_caption,
    bundle_faiss_catalog_index_mtime_delta_caption,
    bundle_faiss_catalog_order_count_parity_caption,
    bundle_faiss_catalog_order_id_set_mismatch_caption,
    bundle_faiss_catalog_yaml_version_caption,
    bundle_faiss_duplicate_id_export_json,
    bundle_faiss_duplicate_id_table_rows,
    bundle_faiss_duplicate_id_table_rows_csv,
    bundle_faiss_id_set_mismatch_export_json,
    bundle_faiss_id_set_mismatch_table_rows,
    bundle_faiss_id_set_mismatch_table_rows_csv,
    bundle_faiss_index_dir_file_count_caption,
    bundle_faiss_index_dir_listing_export_json,
    bundle_faiss_index_dir_listing_table_rows,
    bundle_faiss_index_dir_listing_table_rows_csv,
    bundle_faiss_index_dir_listing_truncated_caption,
    bundle_faiss_index_dir_subdirectory_count_caption,
    bundle_faiss_index_large_file_caption,
    bundle_faiss_index_operator_drilldown,
    bundle_faiss_index_operator_drilldown_export_json,
    bundle_faiss_index_stale_caption,
    bundle_faiss_index_status,
    bundle_faiss_index_status_export_json,
    bundle_faiss_index_status_operator_metrics,
    bundle_faiss_index_status_operator_metrics_caption,
    bundle_faiss_index_status_table_rows,
    bundle_faiss_index_status_table_rows_csv,
    bundle_faiss_index_workflow_caption_note,
    bundle_faiss_invoke_ps1_snippet_explicit,
    bundle_faiss_operator_drilldown_export_filename_slug,
    bundle_faiss_readiness_code_caption,
    bundle_faiss_readiness_export_filename_slug,
    bundle_faiss_readiness_headline_caption,
    bundle_faiss_readiness_missing_caption,
    bundle_faiss_readiness_missing_paths_export_json,
    bundle_faiss_readiness_missing_paths_table_rows,
    bundle_faiss_readiness_missing_paths_table_rows_csv,
    bundle_faiss_readiness_summary,
    bundle_faiss_readiness_summary_export_json,
    bundle_faiss_readiness_summary_operator_metrics,
    bundle_faiss_readiness_summary_operator_metrics_caption,
    bundle_faiss_readiness_summary_operator_metrics_export_filename_slug,
    bundle_faiss_readiness_summary_operator_metrics_export_json,
    bundle_faiss_readiness_summary_operator_metrics_table_rows,
    bundle_faiss_readiness_summary_table_rows,
    bundle_faiss_readiness_summary_table_rows_csv,
    bundle_search_after_hits_stale_caption,
    bundle_search_empty_hits_readiness_caption,
    bundle_search_faiss_ready_caption,
    bundle_search_filename_slug,
    bundle_search_hit_count_caption,
    bundle_search_hits_export_json,
    bundle_search_hits_from_blob,
    bundle_search_hits_summary_caption,
    bundle_search_hits_table_rows_csv,
    bundle_search_k_caption,
    bundle_search_operator_metrics,
    bundle_search_operator_metrics_caption,
    bundle_search_operator_metrics_export_filename_slug,
    bundle_search_operator_metrics_export_json,
    bundle_search_operator_metrics_table_rows,
    bundle_search_operator_metrics_table_rows_csv,
    bundle_search_query_length_caption,
    bundle_search_top_hit_preview_caption,
    run_bundle_catalog_search,
)


def test_bundle_search_empty_hits_readiness_caption_when_index_not_ready() -> None:
    cap = bundle_search_empty_hits_readiness_caption(
        {"query": "auth", "hits": [], "faiss_index_ready": False},
    )
    assert cap is not None
    assert "not ready" in cap.lower()
    assert BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH in cap


def test_bundle_search_empty_hits_readiness_caption_when_index_ready() -> None:
    cap = bundle_search_empty_hits_readiness_caption(
        {"query": "auth", "hits": [], "faiss_index_ready": True},
    )
    assert cap is not None
    assert "zero hits" in cap.lower()


def test_bundle_search_empty_hits_readiness_caption_none_when_hits_present() -> None:
    assert (
        bundle_search_empty_hits_readiness_caption(
            {"query": "auth", "hits": [{"id": "x"}], "faiss_index_ready": False},
        )
        is None
    )


def test_bundle_search_empty_hits_readiness_caption_none_for_bad_payload() -> None:
    assert bundle_search_empty_hits_readiness_caption(None) is None
    assert bundle_search_empty_hits_readiness_caption("x") is None
    assert (
        bundle_search_empty_hits_readiness_caption(
            {"query": "", "hits": [], "faiss_index_ready": False},
        )
        is None
    )


def test_bundle_search_k_caption() -> None:
    cap = bundle_search_k_caption({"query": "auth", "k": 5})
    assert cap is not None
    assert "**5**" in cap
    assert bundle_search_k_caption(None) is None
    assert bundle_search_k_caption({}) is None
    assert bundle_search_k_caption({"query": "auth"}) is None
    assert bundle_search_k_caption({"query": "  ", "k": 3}) is None
    assert bundle_search_k_caption({"query": "auth", "k": 0}) is None
    assert bundle_search_k_caption({"query": "auth", "k": True}) is None


def test_bundle_search_query_length_caption() -> None:
    assert bundle_search_query_length_caption("   ") is None
    cap = bundle_search_query_length_caption("  auth rbac  ")
    assert cap is not None
    assert "**9**" in cap
    cap_hits = bundle_search_query_length_caption("q", hit_count=2)
    assert cap_hits is not None
    assert "**2** hits" in cap_hits
    cap_bad_hits = bundle_search_query_length_caption("q", hit_count=True)
    assert cap_bad_hits is not None
    assert "hits" not in cap_bad_hits


def test_bundle_search_hit_count_caption() -> None:
    cap = bundle_search_hit_count_caption(
        {"query": "auth", "hits": [{"id": "a"}, {"id": "b"}]},
    )
    assert cap is not None
    assert "**2**" in cap
    assert "hits" in cap
    cap1 = bundle_search_hit_count_caption(
        {"query": "x", "hits": [{"id": "only"}]},
    )
    assert cap1 is not None
    assert "**1**" in cap1
    assert "hit." in cap1
    assert bundle_search_hit_count_caption({"query": "x", "hits": []}) is None
    assert bundle_search_hit_count_caption(None) is None


def test_bundle_search_top_hit_preview_caption() -> None:
    cap = bundle_search_top_hit_preview_caption(
        {
            "query": "auth",
            "hits": [{"id": "auth-rbac", "score": 0.91}],
        },
    )
    assert cap is not None
    assert "auth-rbac" in cap
    assert "0.91" in cap
    assert bundle_search_top_hit_preview_caption({"query": "x", "hits": []}) is None
    assert bundle_search_top_hit_preview_caption(None) is None


def test_bundle_search_hits_summary_caption_after_search() -> None:
    cap = bundle_search_hits_summary_caption(
        {
            "query": "auth",
            "k": 5,
            "hits": [{"id": "a"}, {"id": "b"}],
            "faiss_index_ready": True,
            "faiss_index_stale": False,
        },
    )
    assert cap is not None
    assert "q='auth'" in cap
    assert "k=5" in cap
    assert "hits=2" in cap
    assert "faiss_index_ready=yes" in cap
    assert "faiss_index_stale=no" in cap


def test_bundle_search_hits_summary_caption_none_for_bad_payload() -> None:
    assert bundle_search_hits_summary_caption(None) is None
    assert bundle_search_hits_summary_caption({"query": "", "k": 5, "hits": []}) is None


def test_bundle_search_after_hits_stale_caption_when_stale_and_hits() -> None:
    cap = bundle_search_after_hits_stale_caption(
        {
            "faiss_index_stale": True,
            "hits": [{"id": "x"}],
        },
    )
    assert cap is not None
    assert "stale" in cap.lower()
    assert BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH in cap


def test_bundle_search_after_hits_stale_caption_none_when_not_stale() -> None:
    assert (
        bundle_search_after_hits_stale_caption(
            {"faiss_index_stale": False, "hits": [{"id": "x"}]},
        )
        is None
    )


def test_bundle_search_after_hits_stale_caption_none_when_stale_but_no_hits() -> None:
    assert (
        bundle_search_after_hits_stale_caption(
            {"faiss_index_stale": True, "hits": []},
        )
        is None
    )


def test_bundle_search_after_hits_stale_caption_none_for_bad_payload() -> None:
    assert bundle_search_after_hits_stale_caption(None) is None
    assert bundle_search_after_hits_stale_caption("x") is None


def test_run_bundle_catalog_search_finds_auth_bundle() -> None:
    root = Path(__file__).resolve().parents[2]
    out = run_bundle_catalog_search(root, "auth", k=5)
    assert out["query"] == "auth"
    assert out["k"] == 5
    assert "faiss_index_ready" in out and isinstance(out["faiss_index_ready"], bool)
    assert "faiss_index_stale" in out
    ids = {str(h.get("id")) for h in out["hits"] if isinstance(h, dict)}
    assert "auth-rbac-starter" in ids


def test_run_bundle_catalog_search_empty_query_returns_no_hits() -> None:
    root = Path(__file__).resolve().parents[2]
    out = run_bundle_catalog_search(root, "   ", k=3)
    assert out["hits"] == []
    assert out["query"] == ""
    assert out["k"] == 3
    assert "faiss_index_ready" in out


def test_run_bundle_catalog_search_clamps_k() -> None:
    root = Path(__file__).resolve().parents[2]
    out = run_bundle_catalog_search(root, "billing", k=99)
    assert out["k"] == 20


def test_bundle_search_filename_slug_sanitizes() -> None:
    assert bundle_search_filename_slug("auth rbac!") == "auth_rbac"


def test_bundle_search_filename_slug_empty_fallback() -> None:
    assert bundle_search_filename_slug("   @@  ") == "query"



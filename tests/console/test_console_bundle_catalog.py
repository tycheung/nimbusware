"""Console bundle catalog helper (follow-on 24 §14 #12)."""

from __future__ import annotations
from nimbusware_env import find_repo_root
import pytest

pytestmark = pytest.mark.slow


import json
import os
import time
from pathlib import Path

import pytest

import hermes_orchestrator.pipeline  # noqa: F401 — break extensions↔orchestrator cycle
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
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    out = run_bundle_catalog_search(root, "auth", k=5)
    assert out["query"] == "auth"
    assert out["k"] == 5
    assert "faiss_index_ready" in out and isinstance(out["faiss_index_ready"], bool)
    assert "faiss_index_stale" in out
    ids = {str(h.get("id")) for h in out["hits"] if isinstance(h, dict)}
    assert "auth-rbac-starter" in ids


def test_run_bundle_catalog_search_empty_query_returns_no_hits() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    out = run_bundle_catalog_search(root, "   ", k=3)
    assert out["hits"] == []
    assert out["query"] == ""
    assert out["k"] == 3
    assert "faiss_index_ready" in out


def test_run_bundle_catalog_search_clamps_k() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    out = run_bundle_catalog_search(root, "billing", k=99)
    assert out["k"] == 20


def test_bundle_search_filename_slug_sanitizes() -> None:
    assert bundle_search_filename_slug("auth rbac!") == "auth_rbac"


def test_bundle_search_filename_slug_empty_fallback() -> None:
    assert bundle_search_filename_slug("   @@  ") == "query"


def test_bundle_faiss_build_command_snippet() -> None:
    s = bundle_faiss_build_command_snippet()
    assert "poetry install --with faiss" in s
    assert "build_bundle_faiss_index" in s
    assert "--help" in s


def test_bundle_faiss_index_workflow_relpath_and_caption_note() -> None:
    assert BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH.endswith("bundle_faiss_index.yml")
    assert ".github/workflows/" in BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH
    note = bundle_faiss_index_workflow_caption_note()
    assert "bundle_faiss_index" in note
    assert BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH in note


def test_bundle_faiss_index_status_paths_under_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    info = bundle_faiss_index_status(root)
    norm = info["index_dir"].replace("\\", "/")
    assert "configs/bundles/index" in norm
    assert info["ready"] == (info["faiss_index_exists"] and info["bundle_order_exists"])
    assert isinstance(info["faiss_index_exists"], bool)
    assert isinstance(info["bundle_order_exists"], bool)
    assert "catalog_path" in info
    assert "catalog_exists" in info
    assert "stale" in info
    assert "catalog_mtime_ns" in info
    assert "index_max_mtime_ns" in info


def test_bundle_faiss_build_command_snippet_explicit_contains_repo(tmp_path: Path) -> None:
    s = bundle_faiss_build_command_snippet_explicit(tmp_path)
    assert "--repo-root" in s
    assert str(tmp_path.resolve()) in s


def test_bundle_faiss_operator_drilldown_export_json_and_slug(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    text = bundle_faiss_index_operator_drilldown_export_json(tmp_path)
    parsed = json.loads(text)
    assert isinstance(parsed, dict)
    assert parsed["index_dir_listing"] == []
    assert bundle_faiss_operator_drilldown_export_filename_slug(tmp_path) == tmp_path.name.lower()
    weird = tmp_path / "My Repo!"
    weird.mkdir()
    assert bundle_faiss_operator_drilldown_export_filename_slug(weird) == "my_repo"


def test_bundle_faiss_readiness_summary_export_json_and_slug(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    summ = bundle_faiss_readiness_summary(tmp_path)
    parsed = json.loads(bundle_faiss_readiness_summary_export_json(tmp_path))
    assert parsed == summ
    assert parsed["code"] == "incomplete"
    assert bundle_faiss_readiness_export_filename_slug(tmp_path) == tmp_path.name.lower()


def test_bundle_faiss_readiness_summary_table_rows_csv_incomplete(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    summ = bundle_faiss_readiness_summary(tmp_path)
    rows = bundle_faiss_readiness_summary_table_rows(summ)
    fields = {r["field"] for r in rows}
    assert "code" in fields
    assert "missing" in fields
    miss_row = next(r for r in rows if r["field"] == "missing")
    assert "faiss.index" in miss_row["value"]
    csv_text = bundle_faiss_readiness_summary_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert bundle_faiss_readiness_summary_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_faiss_readiness_summary_table_rows_csv([]) == ""


def test_bundle_faiss_readiness_summary_table_rows_ready_and_no_catalog(
    tmp_path: Path,
) -> None:
    summ_nc = bundle_faiss_readiness_summary(tmp_path)
    rows_nc = bundle_faiss_readiness_summary_table_rows(summ_nc)
    assert any(r["field"] == "code" and r["value"] == "no_catalog" for r in rows_nc)

    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir()
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    summ_ready = bundle_faiss_readiness_summary(tmp_path)
    assert summ_ready["code"] == "ready"
    rows_ready = bundle_faiss_readiness_summary_table_rows(summ_ready)
    assert any(r["field"] == "code" for r in rows_ready)
    assert bundle_faiss_readiness_summary_table_rows_csv(rows_ready)


def test_bundle_faiss_readiness_missing_paths_export_incomplete(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    summ = bundle_faiss_readiness_summary(tmp_path)
    rows = bundle_faiss_readiness_missing_paths_table_rows(summ)
    paths = {r["path"] for r in rows}
    assert "configs/bundles/index/faiss.index" in paths
    assert "configs/bundles/index/bundle_order.json" in paths
    parsed = json.loads(bundle_faiss_readiness_missing_paths_export_json(rows))
    assert parsed == rows
    csv_text = bundle_faiss_readiness_missing_paths_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "path"


def test_bundle_faiss_readiness_missing_paths_empty_when_ready_or_stale(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir()
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    summ_ready = bundle_faiss_readiness_summary(tmp_path)
    assert summ_ready["code"] == "ready"
    assert bundle_faiss_readiness_missing_paths_table_rows(summ_ready) == []
    assert bundle_faiss_readiness_missing_paths_table_rows_csv([]) == ""


def test_bundle_faiss_readiness_missing_paths_no_catalog(tmp_path: Path) -> None:
    summ = bundle_faiss_readiness_summary(tmp_path)
    rows = bundle_faiss_readiness_missing_paths_table_rows(summ)
    assert len(rows) == 1
    assert rows[0]["path"] == "configs/bundles/catalog.yaml"
    assert bundle_faiss_readiness_missing_paths_table_rows({}) == []  # type: ignore[arg-type]


def test_bundle_faiss_index_status_export_incomplete(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    status = bundle_faiss_index_status(tmp_path)
    rows = bundle_faiss_index_status_table_rows(status)
    fields = {r["field"] for r in rows}
    assert "ready" in fields
    assert "stale" in fields
    assert "faiss_index_exists" in fields
    ready_row = next(r for r in rows if r["field"] == "ready")
    assert ready_row["value"] == "False"
    parsed = json.loads(bundle_faiss_index_status_export_json(status))
    assert parsed == status
    csv_text = bundle_faiss_index_status_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"


def test_bundle_faiss_index_status_export_ready(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir()
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    status = bundle_faiss_index_status(tmp_path)
    assert status["ready"] is True
    assert status["stale"] is False
    rows = bundle_faiss_index_status_table_rows(status)
    assert any(r["field"] == "faiss_index_exists" and r["value"] == "True" for r in rows)
    assert bundle_faiss_index_status_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_faiss_index_status_table_rows_csv([]) == ""


def test_bundle_faiss_index_status_operator_metrics_ready(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir()
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    status = bundle_faiss_index_status(tmp_path)
    m = bundle_faiss_index_status_operator_metrics(status)
    assert m["ready"] is True
    assert m["stale"] is False
    cap = bundle_faiss_index_status_operator_metrics_caption(m)
    assert cap is not None
    assert "in sync" in cap


def test_bundle_faiss_index_operator_drilldown_empty_index_dir(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["faiss_index_file"]["bytes"] is None
    assert d["bundle_order_file"]["bytes"] is None
    assert d.get("bundle_order_json_file_bytes") is None
    assert d["index_dir_listing"] == []
    assert d["catalog_bundle_dict_count"] == 0
    assert d["catalog_bundle_nonempty_id_count"] == 0
    assert d["catalog_bundle_counts_load_error"] is None
    assert d["bundle_order_list_length"] is None
    assert d["bundle_order_parse_error"] is None
    assert d["bundle_order_catalog_nonempty_id_parity"] is None
    assert d.get("bundle_order_catalog_id_set_parity") is None
    assert d.get("catalog_ids_missing_from_bundle_order_sample") == []
    assert d.get("bundle_order_ids_missing_from_catalog_sample") == []
    assert d.get("bundle_order_catalog_id_set_load_error") is None
    assert d.get("index_dir_subdirectory_count") is None
    assert d.get("catalog_yaml_top_level_version_int") == 1
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    bo = idx / "bundle_order.json"
    bo.write_text("[]", encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["faiss_index_file"]["bytes"] == 1
    assert d["faiss_index_file"]["mtime_iso"] is not None
    names = {e["name"] for e in d["index_dir_listing"]}
    assert names >= {"faiss.index", "bundle_order.json"}
    assert d["catalog_bundle_dict_count"] == 0
    assert d["catalog_bundle_nonempty_id_count"] == 0
    assert d["bundle_order_list_length"] == 0
    assert d["bundle_order_catalog_nonempty_id_parity"] is True
    assert d.get("bundle_order_json_file_bytes") == 2
    assert d.get("bundle_order_catalog_id_set_parity") is True
    assert d.get("catalog_ids_missing_from_bundle_order_sample") == []
    assert d.get("bundle_order_ids_missing_from_catalog_sample") == []
    assert d.get("index_dir_regular_file_count") == 2
    assert d.get("index_dir_subdirectory_count") == 0
    assert d.get("index_dir_listing_truncated") is False
    assert d.get("catalog_yaml_top_level_version_int") == 1


def test_bundle_faiss_index_operator_drilldown_index_dir_listing_truncated(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir(parents=True)
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    for i in range(24):
        (idx / f"extra_{i:02d}.txt").write_text("x", encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d.get("index_dir_regular_file_count") == 26
    assert d.get("index_dir_listing_truncated") is True
    assert len(d["index_dir_listing"]) == 25
    cap = bundle_faiss_index_dir_listing_truncated_caption(tmp_path)
    assert cap is not None
    assert "25" in cap


def test_bundle_faiss_index_dir_listing_truncated_caption_none_when_small_dir(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir(parents=True)
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    assert bundle_faiss_index_dir_listing_truncated_caption(tmp_path) is None


def test_bundle_faiss_index_operator_drilldown_catalog_yaml_version_non_int(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        'version: "1"\nbundles: []\n',
        encoding="utf-8",
    )
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d.get("catalog_yaml_top_level_version_int") is None


def test_bundle_faiss_bundle_order_json_file_bytes_caption(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    cap = bundle_faiss_bundle_order_json_file_bytes_caption(tmp_path)
    assert cap is not None
    assert "2" in cap
    assert "bundle_order.json" in cap


def test_bundle_faiss_index_operator_drilldown_index_dir_has_subdirectory(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    (idx / "extra_subdir").mkdir()
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d.get("index_dir_regular_file_count") == 2
    assert d.get("index_dir_subdirectory_count") == 1


def test_bundle_faiss_index_dir_file_count_caption(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    cap = bundle_faiss_index_dir_file_count_caption(tmp_path)
    assert cap is not None
    assert "2" in cap
    assert "index_dir_regular_file_count" in cap
    sub = bundle_faiss_index_dir_subdirectory_count_caption(tmp_path)
    assert sub is not None
    assert "0" in sub
    assert "index_dir_subdirectory_count" in sub


def test_bundle_faiss_index_dir_subdirectory_count_caption_with_nested_dir(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    (idx / "nested").mkdir()
    cap = bundle_faiss_index_dir_subdirectory_count_caption(tmp_path)
    assert cap is not None
    assert "**1**" in cap
    assert "index_dir_subdirectory_count" in cap


def test_bundle_faiss_index_large_file_caption_none_below_threshold(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    assert bundle_faiss_index_large_file_caption(tmp_path) is None


def test_bundle_faiss_index_large_file_caption_when_over_threshold(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    big = b"z" * (4 * 1024 * 1024 + 1)
    (idx / "faiss.index").write_bytes(big)
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    cap = bundle_faiss_index_large_file_caption(tmp_path)
    assert cap is not None
    assert "4 MiB" in cap
    assert str(len(big)) in cap


def test_bundle_faiss_index_operator_drilldown_count_mismatch(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["catalog_bundle_nonempty_id_count"] == 2
    assert d["bundle_order_list_length"] == 1
    assert d["bundle_order_catalog_nonempty_id_parity"] is False
    assert d.get("bundle_order_catalog_id_set_parity") is None


def test_bundle_faiss_index_operator_drilldown_id_set_parity_order_insensitive(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["b", "a"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["bundle_order_catalog_nonempty_id_parity"] is True
    assert d.get("bundle_order_catalog_id_set_parity") is True


def test_bundle_faiss_index_operator_drilldown_id_set_mismatch_same_count(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["b", "c"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["bundle_order_catalog_nonempty_id_parity"] is True
    assert d.get("bundle_order_catalog_id_set_parity") is False
    miss = d.get("catalog_ids_missing_from_bundle_order_sample")
    extra = d.get("bundle_order_ids_missing_from_catalog_sample")
    assert miss == ["a"]
    assert extra == ["c"]


def test_bundle_faiss_id_set_mismatch_export_json_and_csv(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["b", "c"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    rows = bundle_faiss_id_set_mismatch_table_rows(d)
    assert rows == [
        {"direction": "missing_from_bundle_order", "bundle_id": "a"},
        {"direction": "extra_in_bundle_order", "bundle_id": "c"},
    ]
    parsed = json.loads(bundle_faiss_id_set_mismatch_export_json(rows))
    assert parsed == rows
    csv_text = bundle_faiss_id_set_mismatch_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "direction,bundle_id"
    assert "missing_from_bundle_order,a" in csv_text
    assert "extra_in_bundle_order,c" in csv_text


def test_bundle_faiss_id_set_mismatch_table_rows_empty_when_parity_true(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert bundle_faiss_id_set_mismatch_table_rows(d) == []
    assert bundle_faiss_id_set_mismatch_export_json([]) == "[]"
    assert bundle_faiss_id_set_mismatch_table_rows_csv([]) == ""


def test_bundle_faiss_id_set_mismatch_table_rows_non_mapping() -> None:
    assert bundle_faiss_id_set_mismatch_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_faiss_id_set_mismatch_table_rows(None) == []  # type: ignore[arg-type]


def test_bundle_faiss_catalog_order_id_set_mismatch_caption(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["b", "c"]', encoding="utf-8")
    cap = bundle_faiss_catalog_order_id_set_mismatch_caption(tmp_path)
    assert cap is not None
    assert "id set mismatch" in cap.lower()


def test_bundle_faiss_duplicate_id_export_json_and_csv(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a", "a", "b"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    rows = bundle_faiss_duplicate_id_table_rows(d)
    assert rows == [{"bundle_id": "a"}]
    parsed = json.loads(bundle_faiss_duplicate_id_export_json(rows))
    assert parsed == rows
    csv_text = bundle_faiss_duplicate_id_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "bundle_id"
    assert "a" in csv_text


def test_bundle_faiss_duplicate_id_table_rows_empty_when_no_duplicates(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert bundle_faiss_duplicate_id_table_rows(d) == []
    assert bundle_faiss_duplicate_id_table_rows_csv([]) == ""


def test_bundle_faiss_index_dir_listing_export_json_and_csv(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"index-bytes")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    rows = bundle_faiss_index_dir_listing_table_rows(d)
    names = {r["name"] for r in rows}
    assert "faiss.index" in names
    assert "bundle_order.json" in names
    parsed = json.loads(bundle_faiss_index_dir_listing_export_json(rows))
    assert len(parsed) == len(rows)
    csv_text = bundle_faiss_index_dir_listing_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "name,bytes,mtime_iso"
    assert bundle_faiss_index_dir_listing_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_faiss_index_dir_listing_table_rows_csv([]) == ""


def test_bundle_faiss_index_operator_drilldown_duplicate_bundle_order_ids(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a", "a", "b"]', encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["bundle_order_list_length"] == 3
    assert d["bundle_order_json_distinct_id_count"] == 2
    assert d["bundle_order_json_has_duplicate_ids"] is True
    assert d["bundle_order_json_duplicate_ids_sample"] == ["a"]


def test_bundle_faiss_bundle_order_duplicate_ids_caption(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: x, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["x", "x"]', encoding="utf-8")
    cap = bundle_faiss_bundle_order_duplicate_ids_caption(tmp_path)
    assert cap is not None
    assert "duplicate" in cap.lower()
    assert "x" in cap


def test_bundle_faiss_bundle_order_duplicate_ids_caption_none_when_unique(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: x, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["x"]', encoding="utf-8")
    assert bundle_faiss_bundle_order_duplicate_ids_caption(tmp_path) is None


def test_bundle_faiss_index_operator_drilldown_catalog_index_mtime_delta_ns_catalog_newer(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    cat_p = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat_p.write_text("version: 1\nbundles: []\n", encoding="utf-8")
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    t_old = time.time() - 200.0
    os.utime(idx / "faiss.index", (t_old, t_old))
    os.utime(idx / "bundle_order.json", (t_old, t_old))
    t_new = time.time()
    os.utime(cat_p, (t_new, t_new))
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    delta = d.get("catalog_index_mtime_delta_ns")
    assert type(delta) is int and delta > 0
    cap = bundle_faiss_catalog_index_mtime_delta_caption(tmp_path)
    assert cap is not None
    assert "newer" in cap.lower()


def test_bundle_faiss_catalog_index_mtime_delta_caption_index_newer(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    cat_p = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat_p.write_text("version: 1\nbundles: []\n", encoding="utf-8")
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    t_old = time.time() - 400.0
    os.utime(cat_p, (t_old, t_old))
    t_new = time.time()
    os.utime(idx / "faiss.index", (t_new, t_new))
    os.utime(idx / "bundle_order.json", (t_new, t_new))
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert type(d.get("catalog_index_mtime_delta_ns")) is int
    assert d["catalog_index_mtime_delta_ns"] < 0
    cap = bundle_faiss_catalog_index_mtime_delta_caption(tmp_path)
    assert cap is not None
    assert "newer" in cap.lower() and "catalog.yaml" in cap.lower()


def test_bundle_faiss_catalog_index_mtime_delta_caption_none_when_index_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    assert bundle_faiss_catalog_index_mtime_delta_caption(tmp_path) is None


def test_bundle_faiss_catalog_order_id_set_mismatch_caption_none_when_sets_match(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: x, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["x"]', encoding="utf-8")
    assert bundle_faiss_catalog_order_id_set_mismatch_caption(tmp_path) is None


def test_bundle_faiss_index_operator_drilldown_bundle_order_not_list(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("{}", encoding="utf-8")
    d = bundle_faiss_index_operator_drilldown(tmp_path)
    assert d["bundle_order_list_length"] is None
    assert d["bundle_order_parse_error"] is not None
    assert d["bundle_order_catalog_nonempty_id_parity"] is None


def test_bundle_faiss_catalog_order_count_parity_caption_match(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: x, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["x"]', encoding="utf-8")
    cap = bundle_faiss_catalog_order_count_parity_caption(tmp_path)
    assert cap is not None
    assert "parity" in cap.lower()
    assert "1" in cap


def test_bundle_faiss_catalog_order_count_parity_caption_mismatch(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b, tags: [t]}\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text('["a"]', encoding="utf-8")
    cap = bundle_faiss_catalog_order_count_parity_caption(tmp_path)
    assert cap is not None
    assert "mismatch" in cap.lower()
    assert "2" in cap and "1" in cap


def test_bundle_faiss_catalog_order_count_parity_caption_none_without_order_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    assert bundle_faiss_catalog_order_count_parity_caption(tmp_path) is None


def test_bundle_faiss_catalog_order_count_parity_caption_none_on_bad_json(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("{not json", encoding="utf-8")
    assert bundle_faiss_catalog_order_count_parity_caption(tmp_path) is None


def test_bundle_faiss_readiness_no_catalog(tmp_path: Path) -> None:
    s = bundle_faiss_readiness_summary(tmp_path)
    assert s["code"] == "no_catalog"
    assert "catalog" in s["headline"].lower()


def test_bundle_faiss_readiness_incomplete(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    s = bundle_faiss_readiness_summary(tmp_path)
    assert s["code"] == "incomplete"
    assert len(s["missing"]) >= 1


def test_bundle_faiss_readiness_ready(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat.write_text("version: 1\nbundles: []\n", encoding="utf-8")
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    s = bundle_faiss_readiness_summary(tmp_path)
    assert s["code"] == "ready"


def test_bundle_faiss_readiness_stale(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    cat.write_text("version: 1\nbundles: []\n", encoding="utf-8")
    idx = tmp_path / "configs" / "bundles" / "index"
    faiss_p = idx / "faiss.index"
    meta_p = idx / "bundle_order.json"
    faiss_p.write_bytes(b"x")
    meta_p.write_text("[]", encoding="utf-8")
    t_old = 1_640_995_200
    t_new = t_old + 10_000
    os.utime(faiss_p, (t_old, t_old))
    os.utime(meta_p, (t_old, t_old))
    os.utime(cat, (t_new, t_new))
    s = bundle_faiss_readiness_summary(tmp_path)
    assert s["code"] == "stale"


def test_bundle_faiss_index_stale_caption(tmp_path: Path) -> None:
    cap_missing = bundle_faiss_index_stale_caption(tmp_path)
    assert cap_missing is not None
    assert "not ready" in cap_missing
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    cap_inc = bundle_faiss_index_stale_caption(tmp_path)
    assert cap_inc is not None
    assert "not ready" in cap_inc
    idx = tmp_path / "configs" / "bundles" / "index"
    idx.mkdir(parents=True)
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    cap_fresh = bundle_faiss_index_stale_caption(tmp_path)
    assert cap_fresh is not None
    assert "**no**" in cap_fresh


def test_bundle_faiss_readiness_headline_caption_matches_summary(tmp_path: Path) -> None:
    cap = bundle_faiss_readiness_headline_caption(tmp_path)
    assert cap is not None
    assert "FAISS readiness:" in cap
    summ = bundle_faiss_readiness_summary(tmp_path)
    assert summ["headline"] in cap

    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    cap_inc = bundle_faiss_readiness_headline_caption(tmp_path)
    assert cap_inc is not None
    assert "incomplete" in cap_inc.lower() or "FAISS" in cap_inc


def test_bundle_faiss_readiness_missing_caption(tmp_path: Path) -> None:
    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    cap = bundle_faiss_readiness_missing_caption(tmp_path)
    assert cap is not None
    assert "FAISS index missing:" in cap
    assert "faiss.index" in cap
    assert "bundle_order.json" in cap

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    summ = bundle_faiss_readiness_summary(root)
    if summ.get("code") == "ready":
        assert bundle_faiss_readiness_missing_caption(root) is None


def test_bundle_faiss_readiness_code_caption_matches_summary_codes(tmp_path: Path) -> None:
    assert bundle_faiss_readiness_code_caption(tmp_path) == "FAISS readiness bucket: no_catalog."

    (tmp_path / "configs" / "bundles").mkdir(parents=True)
    (tmp_path / "configs" / "bundles" / "catalog.yaml").write_text(
        "version: 1\nbundles: []\n",
        encoding="utf-8",
    )
    assert bundle_faiss_readiness_code_caption(tmp_path) == "FAISS readiness bucket: incomplete."

    (tmp_path / "configs" / "bundles" / "index").mkdir(parents=True)
    idx = tmp_path / "configs" / "bundles" / "index"
    (idx / "faiss.index").write_bytes(b"x")
    (idx / "bundle_order.json").write_text("[]", encoding="utf-8")
    assert bundle_faiss_readiness_code_caption(tmp_path) == "FAISS readiness bucket: ready."


def test_bundle_faiss_build_powershell_snippet_explicit(tmp_path: Path) -> None:
    s = bundle_faiss_build_powershell_snippet_explicit(tmp_path)
    assert "poetry install --with faiss" in s
    assert "build_bundle_faiss_index" in s
    assert "build_bundle_faiss_index.ps1" in s


def test_bundle_faiss_invoke_ps1_snippet_explicit(tmp_path: Path) -> None:
    s = bundle_faiss_invoke_ps1_snippet_explicit(tmp_path)
    assert "powershell" in s.lower()
    assert "build_bundle_faiss_index.ps1" in s
    assert str(tmp_path.resolve()) in s


def test_bundle_catalog_local_summary_real_repo_has_counts() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    s = bundle_catalog_local_summary(root)
    assert s["has_catalog_yaml"] is True
    assert s["catalog_yaml_relpath"] == "configs/bundles/catalog.yaml"
    assert s["bundle_count"] >= 1
    assert s["distinct_tag_count"] >= 1


def test_bundle_catalog_local_summary_missing_catalog_yields_zeros(tmp_path: Path) -> None:
    s = bundle_catalog_local_summary(tmp_path)
    assert s == {
        "has_catalog_yaml": False,
        "catalog_yaml_relpath": None,
        "bundle_count": 0,
        "distinct_tag_count": 0,
    }


def test_bundle_catalog_local_summary_malformed_yaml_collapses_to_zero(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": not valid yaml :\n", encoding="utf-8")
    s = bundle_catalog_local_summary(tmp_path)
    assert s["has_catalog_yaml"] is True
    assert s["catalog_yaml_relpath"] == "configs/bundles/catalog.yaml"
    assert s["bundle_count"] == 0
    assert s["distinct_tag_count"] == 0


def test_bundle_catalog_local_summary_counts_distinct_tags(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth, rbac, rbac]\n"
        "  - id: b\n"
        "    tags: [auth, billing]\n"
        "  - id: c\n"
        "    title: no tags\n",
        encoding="utf-8",
    )
    s = bundle_catalog_local_summary(tmp_path)
    assert s["bundle_count"] == 3
    assert s["distinct_tag_count"] == 3


def test_bundle_catalog_local_summary_export_json_and_csv(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - {id: a, tags: [t]}\n",
        encoding="utf-8",
    )
    summary = bundle_catalog_local_summary(tmp_path)
    rows = bundle_catalog_local_summary_table_rows(summary)
    fields = {r["field"] for r in rows}
    assert "has_catalog_yaml" in fields
    assert "bundle_count" in fields
    assert "distinct_tag_count" in fields
    parsed = json.loads(bundle_catalog_local_summary_export_json(summary))
    assert parsed == summary
    csv_text = bundle_catalog_local_summary_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert bundle_catalog_local_summary_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_catalog_local_summary_table_rows_csv([]) == ""
    assert (
        bundle_catalog_local_summary_export_filename_slug()
        == "bundle_catalog_local_summary"
    )


def test_bundle_catalog_local_summary_export_missing_catalog(tmp_path: Path) -> None:
    summary = bundle_catalog_local_summary(tmp_path)
    assert summary["has_catalog_yaml"] is False
    rows = bundle_catalog_local_summary_table_rows(summary)
    assert len(rows) == len(summary)
    assert any(r["field"] == "has_catalog_yaml" and r["value"] == "False" for r in rows)


def test_bundle_catalog_bundles_without_tags_rollup_mixed_fixture(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {id: b}\n",
        encoding="utf-8",
    )
    rollup = bundle_catalog_bundles_without_tags_rollup(tmp_path)
    assert rollup["bundle_count"] == 2
    assert rollup["bundles_without_tags_count"] == 1
    assert rollup["bundles_with_tags_count"] == 1
    assert rollup["has_catalog_yaml"] is True
    rows = bundle_catalog_bundles_without_tags_rollup_table_rows(rollup)
    by = {r["field"]: r["value"] for r in rows}
    assert by["bundles_without_tags_count"] == "1"
    assert by["bundles_with_tags_count"] == "1"
    parsed = json.loads(bundle_catalog_bundles_without_tags_rollup_export_json(rollup))
    assert parsed["bundles_without_tags_count"] == 1
    csv_text = bundle_catalog_bundles_without_tags_rollup_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert (
        bundle_catalog_bundles_without_tags_rollup_export_filename_slug()
        == "bundle_catalog_bundles_without_tags"
    )


def test_bundle_catalog_bundles_without_tags_rollup_missing_catalog(tmp_path: Path) -> None:
    rollup = bundle_catalog_bundles_without_tags_rollup(tmp_path)
    assert rollup["has_catalog_yaml"] is False
    assert rollup["bundle_count"] == 0
    assert rollup["bundles_without_tags_count"] == 0
    assert rollup["bundles_with_tags_count"] == 0
    rows = bundle_catalog_bundles_without_tags_rollup_table_rows(rollup)
    assert any(r["field"] == "has_catalog_yaml" and r["value"] == "False" for r in rows)
    assert bundle_catalog_bundles_without_tags_rollup_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_catalog_bundles_without_tags_rollup_table_rows_csv([]) == ""


def test_bundle_catalog_bundles_without_tags_rollup_operator_metrics(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "configs" / "bundles"
    catalog.mkdir(parents=True)
    (catalog / "catalog.yaml").write_text(
        "bundles:\n"
        "  - id: a\n    tags: [x]\n"
        "  - id: b\n",
        encoding="utf-8",
    )
    rollup = bundle_catalog_bundles_without_tags_rollup(tmp_path)
    m = bundle_catalog_bundles_without_tags_rollup_operator_metrics(rollup)
    assert m["has_catalog_yaml"] is True
    assert m["bundle_count"] == 2
    assert m["bundles_without_tags_count"] == 1
    assert m["untagged_ratio"] == 0.5
    cap = bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption(m)
    assert cap is not None


def test_bundle_catalog_bundles_without_tags_rollup_operator_metrics_missing_catalog(
    tmp_path: Path,
) -> None:
    rollup = bundle_catalog_bundles_without_tags_rollup(tmp_path)
    m = bundle_catalog_bundles_without_tags_rollup_operator_metrics(rollup)
    assert m["bundle_count"] == 0
    assert bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption(m) is None


def test_bundle_catalog_bundles_without_tags_rollup_operator_metrics_export() -> None:
    m = bundle_catalog_bundles_without_tags_rollup_operator_metrics(
        {
            "has_catalog_yaml": True,
            "bundle_count": 4,
            "bundles_without_tags_count": 1,
            "bundles_with_tags_count": 3,
        },
    )
    parsed = json.loads(
        bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_json(m),
    )
    assert parsed["bundle_count"] == 4
    rows = bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows(m)
    csv_text = bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows_csv(
        rows,
    )
    assert "Bundle count" in csv_text
    assert (
        bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_filename_slug()
        == "bundle_catalog_bundles_without_tags_rollup_operator_metrics"
    )


def test_bundle_catalog_bundles_without_id_rollup_mixed_fixture(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles:\n"
        "  - {id: a, tags: [t]}\n"
        "  - {title: no id}\n",
        encoding="utf-8",
    )
    rollup = bundle_catalog_bundles_without_id_rollup(tmp_path)
    assert rollup["bundle_count"] == 2
    assert rollup["bundles_without_id_count"] == 1
    assert rollup["bundles_with_id_count"] == 1
    assert rollup["has_catalog_yaml"] is True
    rows = bundle_catalog_bundles_without_id_rollup_table_rows(rollup)
    by = {r["field"]: r["value"] for r in rows}
    assert by["bundles_without_id_count"] == "1"
    assert by["bundles_with_id_count"] == "1"
    parsed = json.loads(bundle_catalog_bundles_without_id_rollup_export_json(rollup))
    assert parsed["bundles_without_id_count"] == 1
    csv_text = bundle_catalog_bundles_without_id_rollup_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert (
        bundle_catalog_bundles_without_id_rollup_export_filename_slug()
        == "bundle_catalog_bundles_without_id"
    )


def test_bundle_catalog_bundles_without_id_rollup_missing_catalog(tmp_path: Path) -> None:
    rollup = bundle_catalog_bundles_without_id_rollup(tmp_path)
    assert rollup["has_catalog_yaml"] is False
    assert rollup["bundle_count"] == 0
    assert rollup["bundles_without_id_count"] == 0
    assert rollup["bundles_with_id_count"] == 0
    rows = bundle_catalog_bundles_without_id_rollup_table_rows(rollup)
    assert any(r["field"] == "has_catalog_yaml" and r["value"] == "False" for r in rows)
    assert bundle_catalog_bundles_without_id_rollup_table_rows({}) == []  # type: ignore[arg-type]
    assert bundle_catalog_bundles_without_id_rollup_table_rows_csv([]) == ""


def test_bundle_catalog_bundles_without_id_rollup_operator_metrics(tmp_path: Path) -> None:
    catalog = tmp_path / "configs" / "bundles"
    catalog.mkdir(parents=True)
    (catalog / "catalog.yaml").write_text(
        "bundles:\n"
        "  - id: a\n    tags: [x]\n"
        "  - {title: no id}\n",
        encoding="utf-8",
    )
    rollup = bundle_catalog_bundles_without_id_rollup(tmp_path)
    m = bundle_catalog_bundles_without_id_rollup_operator_metrics(rollup)
    assert m["has_catalog_yaml"] is True
    assert m["bundles_without_id_count"] == 1
    cap = bundle_catalog_bundles_without_id_rollup_operator_metrics_caption(m)
    assert cap is not None


def test_bundle_catalog_bundles_without_id_rollup_operator_metrics_missing_catalog(
    tmp_path: Path,
) -> None:
    rollup = bundle_catalog_bundles_without_id_rollup(tmp_path)
    m = bundle_catalog_bundles_without_id_rollup_operator_metrics(rollup)
    assert m["bundle_count"] == 0
    assert bundle_catalog_bundles_without_id_rollup_operator_metrics_caption(m) is None


def test_bundle_catalog_bundles_without_id_rollup_operator_metrics_export() -> None:
    m = bundle_catalog_bundles_without_id_rollup_operator_metrics(
        {
            "has_catalog_yaml": True,
            "bundle_count": 3,
            "bundles_without_id_count": 2,
            "bundles_with_id_count": 1,
        },
    )
    parsed = json.loads(
        bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json(m),
    )
    assert parsed["bundles_without_id_count"] == 2
    rows = bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows(m)
    csv_text = bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv(rows)
    assert "Bundles without id" in csv_text
    assert (
        bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug()
        == "bundle_catalog_bundles_without_id_rollup_operator_metrics"
    )


def test_bundle_catalog_distinct_tags_sample_real_repo_sorted_and_contains_expected() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    tags = bundle_catalog_distinct_tags_sample(root)
    assert tags == sorted(tags)
    assert len(tags) == len(set(tags))
    expected = {"auth", "rbac", "billing", "stripe"}
    assert expected.issubset(set(tags))


def test_bundle_catalog_distinct_tags_sample_missing_catalog_returns_empty(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_distinct_tags_sample(tmp_path) == []


def test_bundle_catalog_distinct_tags_sample_malformed_yaml_returns_empty(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": not valid yaml :\n", encoding="utf-8")
    assert bundle_catalog_distinct_tags_sample(tmp_path) == []


def test_bundle_catalog_distinct_tags_sample_dedup_sort_and_strip(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [zebra, auth, rbac]\n"
        "  - id: b\n"
        "    tags: ['  auth  ', billing, '']\n"
        "  - id: c\n"
        "    tags: [123, true, billing]\n",
        encoding="utf-8",
    )
    tags = bundle_catalog_distinct_tags_sample(tmp_path)
    assert tags == ["auth", "billing", "rbac", "zebra"]


def test_bundle_catalog_distinct_tags_sample_truncates_at_max_n(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth, billing, cdn, dns, ecom]\n",
        encoding="utf-8",
    )
    truncated = bundle_catalog_distinct_tags_sample(tmp_path, max_n=2)
    assert truncated == ["auth", "billing"]
    assert bundle_catalog_distinct_tags_sample(tmp_path, max_n=0) == []


def test_bundle_catalog_top_tag_counts_real_repo_descending_with_counts() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    rows = bundle_catalog_top_tag_counts(root)
    assert rows
    counts = [r["count"] for r in rows]
    assert counts == sorted(counts, reverse=True)
    for r in rows:
        assert isinstance(r["tag"], str) and r["tag"]
        assert isinstance(r["count"], int) and r["count"] >= 1
    seen_tags = {r["tag"] for r in rows}
    assert "auth" in seen_tags


def test_bundle_catalog_top_tag_counts_missing_catalog_returns_empty(tmp_path: Path) -> None:
    assert bundle_catalog_top_tag_counts(tmp_path) == []


def test_bundle_catalog_top_tag_counts_malformed_yaml_returns_empty(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": not valid yaml :\n", encoding="utf-8")
    assert bundle_catalog_top_tag_counts(tmp_path) == []


def test_bundle_catalog_top_tag_counts_descending_with_alpha_tiebreak(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth, rbac, billing]\n"
        "  - id: b\n"
        "    tags: [auth, billing]\n"
        "  - id: c\n"
        "    tags: [auth]\n"
        "  - id: d\n"
        "    tags: [zebra, rbac]\n",
        encoding="utf-8",
    )
    rows = bundle_catalog_top_tag_counts(tmp_path)
    assert rows == [
        {"tag": "auth", "count": 3},
        {"tag": "billing", "count": 2},
        {"tag": "rbac", "count": 2},
        {"tag": "zebra", "count": 1},
    ]


def test_bundle_catalog_top_tag_counts_truncates_at_top_n(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth, billing, cdn, dns, ecom]\n",
        encoding="utf-8",
    )
    truncated = bundle_catalog_top_tag_counts(tmp_path, top_n=2)
    assert truncated == [
        {"tag": "auth", "count": 1},
        {"tag": "billing", "count": 1},
    ]
    assert bundle_catalog_top_tag_counts(tmp_path, top_n=0) == []
    assert bundle_catalog_top_tag_counts(tmp_path, top_n=-3) == []


def test_bundle_catalog_top_tag_counts_ignores_non_string_entries(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth, 123, true, '   ', billing]\n",
        encoding="utf-8",
    )
    rows = bundle_catalog_top_tag_counts(tmp_path)
    tags = [r["tag"] for r in rows]
    assert set(tags) == {"auth", "billing"}


def test_bundle_catalog_bundles_without_tags_count_real_repo_consistent_with_summary() -> None:
    repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    summary = bundle_catalog_local_summary(repo_root)
    without = bundle_catalog_bundles_without_tags_count(repo_root)
    assert isinstance(without, int)
    assert without >= 0
    assert without <= int(summary.get("bundle_count") or 0)


def test_bundle_catalog_bundles_without_tags_count_missing_catalog_yields_zero(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_bundles_without_tags_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_tags_count_malformed_yaml_yields_zero(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": : not yaml\n", encoding="utf-8")
    assert bundle_catalog_bundles_without_tags_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_tags_count_non_dict_root_yields_zero(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert bundle_catalog_bundles_without_tags_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_tags_count_counts_missing_and_non_list(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: with_tags\n"
        "    tags: [auth]\n"
        "  - id: missing\n"
        "  - id: not_a_list\n"
        "    tags: auth\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundles_without_tags_count(tmp_path) == 2


def test_bundle_catalog_bundles_without_tags_count_counts_whitespace_only_tags(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: empty_list\n"
        "    tags: []\n"
        "  - id: whitespace_only\n"
        "    tags: ['   ', '']\n"
        "  - id: non_string_only\n"
        "    tags: [123, true]\n"
        "  - id: usable\n"
        "    tags: [auth]\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundles_without_tags_count(tmp_path) == 3


def test_bundle_catalog_bundles_without_tags_count_mixed_boundary(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth]\n"
        "  - id: b\n"
        "    tags: ['   billing  ']\n"
        "  - id: c\n"
        "  - id: d\n"
        "    tags: [123, '']\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundles_without_tags_count(tmp_path) == 2


def test_bundle_catalog_bundle_ids_sample_real_repo_sorted() -> None:
    repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    ids = bundle_catalog_bundle_ids_sample(repo_root)
    assert isinstance(ids, list)
    assert ids == sorted(ids)
    assert "auth-rbac-starter" in ids
    assert "billing-stripe" in ids


def test_bundle_catalog_bundle_ids_sample_missing_catalog_returns_empty(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_bundle_ids_sample(tmp_path) == []


def test_bundle_catalog_bundle_ids_sample_malformed_yaml_returns_empty(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": : not yaml\n", encoding="utf-8")
    assert bundle_catalog_bundle_ids_sample(tmp_path) == []


def test_bundle_catalog_bundle_ids_sample_non_dict_root_returns_empty(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert bundle_catalog_bundle_ids_sample(tmp_path) == []


def test_bundle_catalog_bundle_ids_sample_dedup_strip_and_sort(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: '  charlie  '\n"
        "  - id: alpha\n"
        "  - id: bravo\n"
        "  - id: alpha\n",
        encoding="utf-8",
    )
    ids = bundle_catalog_bundle_ids_sample(tmp_path)
    assert ids == ["alpha", "bravo", "charlie"]


def test_bundle_catalog_bundle_ids_sample_truncates_at_max_n(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: aaa\n"
        "  - id: bbb\n"
        "  - id: ccc\n"
        "  - id: ddd\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundle_ids_sample(tmp_path, max_n=2) == ["aaa", "bbb"]


def test_bundle_catalog_bundle_ids_sample_non_positive_max_n_returns_empty(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - id: a\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundle_ids_sample(tmp_path, max_n=0) == []
    assert bundle_catalog_bundle_ids_sample(tmp_path, max_n=-3) == []


def test_bundle_catalog_bundle_ids_sample_ignores_non_string_and_empty(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: 123\n"
        "  - id: ''\n"
        "  - id: '   '\n"
        "  - id: true\n"
        "  - id: real-id\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundle_ids_sample(tmp_path) == ["real-id"]


def test_bundle_catalog_bundle_count_caption_real_repo_matches_local_summary() -> None:
    repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    cap = bundle_catalog_bundle_count_caption(repo_root)
    summary = bundle_catalog_local_summary(repo_root)
    untagged = bundle_catalog_bundles_without_tags_count(repo_root)
    total = int(summary.get("bundle_count") or 0)
    tagged = max(total - untagged, 0)
    assert cap == f"Bundles: {total} ({tagged} tagged, {untagged} untagged)."


def test_bundle_catalog_bundle_count_caption_missing_catalog_returns_none(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_bundle_count_caption(tmp_path) is None


def test_bundle_catalog_bundle_count_caption_malformed_yaml_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": : not yaml\n", encoding="utf-8")
    assert bundle_catalog_bundle_count_caption(tmp_path) is None


def test_bundle_catalog_bundle_count_caption_non_dict_root_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert bundle_catalog_bundle_count_caption(tmp_path) is None


def test_bundle_catalog_bundle_count_caption_zero_bundles_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("version: 1\nbundles: []\n", encoding="utf-8")
    assert bundle_catalog_bundle_count_caption(tmp_path) is None


def test_bundle_catalog_bundle_count_caption_mixed_tagged_untagged(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth]\n"
        "  - id: b\n"
        "  - id: c\n"
        "    tags: []\n",
        encoding="utf-8",
    )
    assert (
        bundle_catalog_bundle_count_caption(tmp_path)
        == "Bundles: 3 (1 tagged, 2 untagged)."
    )


def test_bundle_catalog_bundle_count_caption_all_tagged(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [auth]\n"
        "  - id: b\n"
        "    tags: [billing]\n",
        encoding="utf-8",
    )
    assert (
        bundle_catalog_bundle_count_caption(tmp_path)
        == "Bundles: 2 (2 tagged, 0 untagged)."
    )


def test_bundle_catalog_top_tag_caption_real_repo_non_empty_when_rows() -> None:
    repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    rows = bundle_catalog_top_tag_counts(repo_root, top_n=3)
    cap = bundle_catalog_top_tag_caption(repo_root)
    if rows:
        expected = "Top tags: " + ", ".join(
            f"{r['tag']} ({r['count']})" for r in rows
        ) + "."
        assert cap == expected
    else:
        assert cap is None


def test_bundle_catalog_top_tag_caption_missing_catalog_returns_none(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_top_tag_caption(tmp_path) is None


def test_bundle_catalog_top_tag_caption_malformed_yaml_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": : not yaml\n", encoding="utf-8")
    assert bundle_catalog_top_tag_caption(tmp_path) is None


def test_bundle_catalog_top_tag_caption_non_dict_root_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert bundle_catalog_top_tag_caption(tmp_path) is None


def test_bundle_catalog_top_tag_caption_zero_usable_tags_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "  - id: b\n"
        "    tags: []\n"
        "  - id: c\n"
        "    tags: ['   ']\n",
        encoding="utf-8",
    )
    assert bundle_catalog_top_tag_caption(tmp_path) is None


def test_bundle_catalog_top_tag_caption_three_tag_fixture_exact_caption(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [foo]\n"
        "  - id: b\n"
        "    tags: [foo, bar]\n"
        "  - id: c\n"
        "    tags: [foo, bar, baz]\n",
        encoding="utf-8",
    )
    assert (
        bundle_catalog_top_tag_caption(tmp_path)
        == "Top tags: foo (3), bar (2), baz (1)."
    )


def test_bundle_catalog_top_tag_caption_default_top_n_truncates_to_three(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [t1, t2, t3, t4, t5]\n"
        "  - id: b\n"
        "    tags: [t1, t2, t3, t4]\n"
        "  - id: c\n"
        "    tags: [t1, t2, t3]\n"
        "  - id: d\n"
        "    tags: [t1, t2]\n"
        "  - id: e\n"
        "    tags: [t1]\n",
        encoding="utf-8",
    )
    cap = bundle_catalog_top_tag_caption(tmp_path)
    assert cap is not None
    assert cap.count(",") == 2
    assert cap.startswith("Top tags: t1 (5), t2 (4), t3 (3)")


def test_bundle_catalog_top_tag_caption_explicit_top_n_two(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [foo]\n"
        "  - id: b\n"
        "    tags: [foo, bar]\n"
        "  - id: c\n"
        "    tags: [foo, bar, baz]\n",
        encoding="utf-8",
    )
    assert (
        bundle_catalog_top_tag_caption(tmp_path, top_n=2)
        == "Top tags: foo (3), bar (2)."
    )


def test_bundle_catalog_top_tag_caption_non_positive_top_n_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - id: a\n    tags: [foo]\n",
        encoding="utf-8",
    )
    assert bundle_catalog_top_tag_caption(tmp_path, top_n=0) is None
    assert bundle_catalog_top_tag_caption(tmp_path, top_n=-2) is None


def test_bundle_catalog_distinct_tag_count_caption_real_repo_matches_local_summary() -> None:
    repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    summary = bundle_catalog_local_summary(repo_root)
    cap = bundle_catalog_distinct_tag_count_caption(repo_root)
    expected_n = summary["distinct_tag_count"]
    if isinstance(expected_n, int) and not isinstance(expected_n, bool) and expected_n > 0:
        assert cap == f"Distinct tags: {expected_n}."
    else:
        assert cap is None


def test_bundle_catalog_distinct_tag_count_caption_missing_catalog_returns_none(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_distinct_tag_count_caption(tmp_path) is None


def test_bundle_catalog_distinct_tag_count_caption_malformed_yaml_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": : not yaml\n", encoding="utf-8")
    assert bundle_catalog_distinct_tag_count_caption(tmp_path) is None


def test_bundle_catalog_distinct_tag_count_caption_non_dict_root_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert bundle_catalog_distinct_tag_count_caption(tmp_path) is None


def test_bundle_catalog_distinct_tag_count_caption_zero_usable_tags_returns_none(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles:\n  - id: a\n  - id: b\n    tags: []\n",
        encoding="utf-8",
    )
    assert bundle_catalog_distinct_tag_count_caption(tmp_path) is None


def test_bundle_catalog_distinct_tag_count_caption_three_tag_fixture(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n"
        "    tags: [foo, bar]\n"
        "  - id: b\n"
        "    tags: [foo, baz]\n",
        encoding="utf-8",
    )
    assert bundle_catalog_distinct_tag_count_caption(tmp_path) == "Distinct tags: 3."


def test_bundle_catalog_distinct_tag_count_caption_bool_value_treated_as_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "nimbusware_console.bundle_catalog.bundle_catalog_local_summary",
        lambda _root: {"distinct_tag_count": True},
    )
    assert bundle_catalog_distinct_tag_count_caption(tmp_path) is None


def test_bundle_catalog_bundles_without_id_count_real_repo_bounded_by_bundle_count() -> None:
    repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    summary = bundle_catalog_local_summary(repo_root)
    total = int(summary.get("bundle_count") or 0)
    wid = bundle_catalog_bundles_without_id_count(repo_root)
    assert wid >= 0
    assert wid <= total


def test_bundle_catalog_bundles_without_id_count_missing_catalog_yields_zero(
    tmp_path: Path,
) -> None:
    assert bundle_catalog_bundles_without_id_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_id_count_malformed_yaml_yields_zero(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(": : not yaml\n", encoding="utf-8")
    assert bundle_catalog_bundles_without_id_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_id_count_non_dict_root_yields_zero(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert bundle_catalog_bundles_without_id_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_id_count_non_list_bundles_yields_zero(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\nbundles: not-a-list\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundles_without_id_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_id_caption_mixed_fixture(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: good-id\n"
        "    tags: [x]\n"
        "  - tags: [y]\n"
        "  - id: '   '\n"
        "    tags: [z]\n"
        "  - id: 42\n"
        "    tags: [w]\n",
        encoding="utf-8",
    )
    cap = bundle_catalog_bundles_without_id_caption(tmp_path)
    assert cap is not None
    assert "**3**" in cap
    assert "**4**" in cap
    assert bundle_catalog_bundles_without_id_caption(tmp_path / "missing") is None


def test_bundle_catalog_bundles_without_id_count_mixed_fixture_three_without(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: good-id\n"
        "    tags: [x]\n"
        "  - tags: [y]\n"
        "  - id: '   '\n"
        "    tags: [z]\n"
        "  - id: 42\n"
        "    tags: [w]\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundles_without_id_count(tmp_path) == 3


def test_bundle_catalog_bundles_without_id_count_all_good_ids_yields_zero(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: a\n    tags: [t]\n"
        "  - id: b\n    tags: [t]\n",
        encoding="utf-8",
    )
    assert bundle_catalog_bundles_without_id_count(tmp_path) == 0


def test_bundle_catalog_bundles_without_id_count_plus_sample_equals_total_unique_fixture(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: alpha\n"
        "    tags: [t]\n"
        "  - tags: [t]\n"
        "  - id: '   '\n"
        "    tags: [t]\n"
        "  - id: beta\n"
        "    tags: [t]\n",
        encoding="utf-8",
    )
    summary = bundle_catalog_local_summary(tmp_path)
    total = int(summary.get("bundle_count") or 0)
    wid = bundle_catalog_bundles_without_id_count(tmp_path)
    sample = bundle_catalog_bundle_ids_sample(tmp_path, max_n=99)
    assert wid + len(sample) == total


def test_bundle_catalog_bundles_without_tags_caption_mixed_fixture(
    tmp_path: Path,
) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "version: 1\n"
        "bundles:\n"
        "  - id: tagged\n"
        "    tags: [x]\n"
        "  - id: untagged\n",
        encoding="utf-8",
    )
    cap = bundle_catalog_bundles_without_tags_caption(tmp_path)
    assert cap is not None
    assert "**1**" in cap
    assert "**2**" in cap
    assert bundle_catalog_bundles_without_tags_caption(tmp_path / "missing") is None


def test_bundle_faiss_catalog_yaml_version_caption_from_repo() -> None:
    repo_root = find_repo_root(start=Path(__file__).resolve().parents[1])
    cap = bundle_faiss_catalog_yaml_version_caption(repo_root)
    assert cap is not None
    assert "top-level version" in cap.lower()


def test_bundle_search_faiss_ready_caption() -> None:
    cap_ready = bundle_search_faiss_ready_caption({"faiss_index_ready": True})
    assert cap_ready is not None
    assert "**ready**" in cap_ready
    cap_not = bundle_search_faiss_ready_caption({"faiss_index_ready": False})
    assert cap_not is not None
    assert "**not ready**" in cap_not
    assert bundle_search_faiss_ready_caption(None) is None
    assert bundle_search_faiss_ready_caption({}) is None


def test_bundle_search_operator_metrics_multi_hit() -> None:
    payload = {
        "query": "api",
        "hits": [
            {"id": "b1", "tags": ["python", "api"]},
            {"id": "b2", "tags": ["python"]},
            {"id": "", "tags": []},
            {"tags": ["orphan"]},
        ],
    }
    m = bundle_search_operator_metrics(payload)
    assert m["hit_count"] == 4
    assert m["distinct_tag_count"] == 3
    assert m["hits_without_tags"] == 1
    assert m["hits_without_id"] == 2
    assert m["top_hit_id"] == "b1"


def test_bundle_search_operator_metrics_empty_query() -> None:
    m = bundle_search_operator_metrics({"query": "", "hits": []})
    assert m["hit_count"] == 0
    assert bundle_search_operator_metrics_caption(m) is None


def test_bundle_search_operator_metrics_table_rows_and_caption() -> None:
    m = bundle_search_operator_metrics(
        {"hits": [{"id": "only", "tags": ["x"]}]},
    )
    cap = bundle_search_operator_metrics_caption(m)
    assert cap is not None
    assert "1" in cap
    rows = bundle_search_operator_metrics_table_rows(m)
    assert rows[0]["field"] == "Hit count"
    assert rows[0]["value"] == "1"
    assert any(r["field"] == "Top hit id" for r in rows)


def test_bundle_search_operator_metrics_export_filename_slug() -> None:
    slug = bundle_search_operator_metrics_export_filename_slug()
    assert slug == "bundle_search_operator_metrics"
    query_slug = bundle_search_filename_slug("auth rbac")
    assert f"hermes_{slug}_{query_slug}_20260101T000000Z.json".startswith(
        "hermes_bundle_search_operator_metrics_",
    )


def test_bundle_search_operator_metrics_export_json_and_csv() -> None:
    m = bundle_search_operator_metrics(
        {"hits": [{"id": "only", "tags": ["x"]}]},
    )
    parsed = json.loads(bundle_search_operator_metrics_export_json(m))
    assert parsed == m
    assert json.loads(bundle_search_operator_metrics_export_json(None)) == {}
    assert bundle_search_operator_metrics_export_json("x") == "{}"
    rows = bundle_search_operator_metrics_table_rows(m)
    csv_text = bundle_search_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert "Hit count" in csv_text
    assert bundle_search_operator_metrics_table_rows_csv([]) == ""


def test_bundle_catalog_local_summary_operator_metrics_from_summary(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "configs" / "bundles"
    catalog.mkdir(parents=True)
    (catalog / "catalog.yaml").write_text(
        "bundles:\n"
        "  - id: a\n    tags: [x, y]\n"
        "  - id: b\n    tags: [y]\n",
        encoding="utf-8",
    )
    summary = bundle_catalog_local_summary(tmp_path)
    m = bundle_catalog_local_summary_operator_metrics(summary)
    assert m["catalog_yaml_present"] is True
    assert m["bundle_count"] == 2
    assert m["distinct_tag_count"] == 2
    assert m["avg_tags_per_bundle"] == 1.0
    cap = bundle_catalog_local_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "2" in cap


def test_bundle_catalog_local_summary_operator_metrics_missing_catalog(
    tmp_path: Path,
) -> None:
    summary = bundle_catalog_local_summary(tmp_path)
    m = bundle_catalog_local_summary_operator_metrics(summary)
    assert m["catalog_yaml_present"] is False
    assert bundle_catalog_local_summary_operator_metrics_caption(m) is None
    assert m["bundle_count"] == 0


def test_bundle_catalog_local_summary_operator_metrics_export() -> None:
    m = bundle_catalog_local_summary_operator_metrics(
        {
            "has_catalog_yaml": True,
            "bundle_count": 3,
            "distinct_tag_count": 5,
        },
    )
    parsed = json.loads(bundle_catalog_local_summary_operator_metrics_export_json(m))
    assert parsed["bundle_count"] == 3
    assert json.loads(bundle_catalog_local_summary_operator_metrics_export_json(None)) == {}
    rows = bundle_catalog_local_summary_operator_metrics_table_rows(m)
    assert rows[1]["field"] == "Bundle count"
    csv_text = bundle_catalog_local_summary_operator_metrics_table_rows_csv(rows)
    assert "Bundle count" in csv_text
    assert (
        bundle_catalog_local_summary_operator_metrics_export_filename_slug()
        == "bundle_catalog_local_summary_operator_metrics"
    )


@pytest.mark.parametrize(
    ("code", "missing", "is_ready", "is_stale"),
    [
        ("ready", [], True, False),
        ("stale", [], False, True),
        ("incomplete", ["configs/bundles/index/faiss.index"], False, False),
        ("no_catalog", ["configs/bundles/catalog.yaml"], False, False),
    ],
)
def test_bundle_faiss_readiness_summary_operator_metrics_codes(
    code: str,
    missing: list[str],
    is_ready: bool,
    is_stale: bool,
) -> None:
    summary = {"code": code, "missing": missing}
    m = bundle_faiss_readiness_summary_operator_metrics(summary)
    assert m["code"] == code
    assert m["missing_path_count"] == len(missing)
    assert m["is_ready"] is is_ready
    assert m["is_stale"] is is_stale
    assert m[f"is_{code}"] is True or (code == "no_catalog" and m["is_no_catalog"])


def test_bundle_faiss_readiness_summary_operator_metrics_headline_present() -> None:
    m = bundle_faiss_readiness_summary_operator_metrics(
        {"code": "ready", "missing": [], "headline": "FAISS index ready"},
    )
    assert m["headline_present"] is True
    cap = bundle_faiss_readiness_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "headline" in cap


def test_bundle_faiss_readiness_summary_operator_metrics_mtime_observable() -> None:
    m = bundle_faiss_readiness_summary_operator_metrics(
        {
            "code": "ready",
            "missing": [],
            "catalog_mtime_observable": True,
            "index_mtime_observable": True,
        },
    )
    assert m["catalog_mtime_observable"] is True
    assert m["index_mtime_observable"] is True
    assert m["mtime_both_observable"] is True
    cap = bundle_faiss_readiness_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "catalog mtime observable" in cap
    assert "index mtime observable" in cap
    assert "both observable" in cap
    rows = bundle_faiss_readiness_summary_operator_metrics_table_rows(m)
    assert any(r["field"] == "Catalog mtime observable" for r in rows)
    assert any(r["field"] == "Index mtime observable" for r in rows)


def test_bundle_faiss_readiness_summary_operator_metrics_caption_stale() -> None:
    m = bundle_faiss_readiness_summary_operator_metrics({"code": "stale", "missing": []})
    cap = bundle_faiss_readiness_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "stale" in cap
    assert "catalog newer than index" in cap


def test_bundle_faiss_readiness_summary_operator_metrics_caption_no_catalog() -> None:
    m = bundle_faiss_readiness_summary_operator_metrics({"code": "no_catalog", "missing": []})
    assert m["is_no_catalog"] is True
    cap = bundle_faiss_readiness_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "no catalog" in cap


def test_bundle_faiss_readiness_summary_operator_metrics_caption_and_export() -> None:
    m = bundle_faiss_readiness_summary_operator_metrics(
        {"code": "incomplete", "missing": ["a", "b"]},
    )
    cap = bundle_faiss_readiness_summary_operator_metrics_caption(m)
    assert cap is not None
    assert "incomplete" in cap
    assert "index **incomplete**" in cap
    assert "2" in cap
    rows = bundle_faiss_readiness_summary_operator_metrics_table_rows(m)
    assert any(r["field"] == "Readiness code" for r in rows)
    assert json.loads(bundle_faiss_readiness_summary_operator_metrics_export_json(None)) == {}
    assert (
        bundle_faiss_readiness_summary_operator_metrics_export_filename_slug()
        == "bundle_faiss_readiness_summary_operator_metrics"
    )


def test_bundle_search_hits_from_blob_empty() -> None:
    assert bundle_search_hits_from_blob(None) == []
    assert bundle_search_hits_from_blob({}) == []
    assert bundle_search_hits_from_blob({"hits": "x"}) == []
    assert bundle_search_hits_from_blob({"hits": [1, {"id": "a"}]}) == [{"id": "a"}]


def test_bundle_search_hits_export_json_and_csv() -> None:
    hits = [
        {"id": "auth", "title": "Auth", "tags": ["security", "rbac"], "score": 0.9},
        {"id": "plain", "title": "Plain"},
    ]
    parsed = json.loads(bundle_search_hits_export_json(hits))
    assert len(parsed) == 2
    assert parsed[0]["id"] == "auth"
    csv_text = bundle_search_hits_table_rows_csv(hits)
    assert csv_text.splitlines()[0] == "id,title,tags,score"
    assert "auth" in csv_text
    assert "security, rbac" in csv_text or "security" in csv_text
    assert bundle_search_hits_table_rows_csv([]) == ""


def test_bundle_catalog_local_bundles_missing_yaml(tmp_path: Path) -> None:
    assert bundle_catalog_local_bundles(tmp_path) == []


def test_bundle_catalog_local_bundles_export_json_and_csv(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "bundles:\n"
        "  - id: auth\n"
        "    title: Auth Module\n"
        "    tags: [security, rbac]\n"
        "  - id: plain\n"
        "    title: Plain\n",
        encoding="utf-8",
    )
    bundles = bundle_catalog_local_bundles(tmp_path)
    assert len(bundles) == 2
    rows = bundle_catalog_local_bundles_table_rows(bundles)
    assert rows[0]["id"] == "auth"
    assert "security" in rows[0]["tags"]
    parsed = json.loads(bundle_catalog_local_bundles_export_json(bundles))
    assert len(parsed) == 2
    csv_text = bundle_catalog_local_bundles_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "id,title,tags"
    assert "auth" in csv_text
    assert bundle_catalog_local_bundles_table_rows_csv([]) == ""


def test_bundle_catalog_local_bundles_malformed_yaml(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text("not: [valid", encoding="utf-8")
    assert bundle_catalog_local_bundles(tmp_path) == []


def test_bundle_catalog_top_tag_counts_export_json_and_csv(tmp_path: Path) -> None:
    cat_dir = tmp_path / "configs" / "bundles"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.yaml").write_text(
        "bundles:\n"
        "  - id: a\n"
        "    tags: [foo, bar, foo]\n"
        "  - id: b\n"
        "    tags: [foo, baz]\n",
        encoding="utf-8",
    )
    rows = bundle_catalog_top_tag_counts(tmp_path, top_n=5)
    assert rows == [
        {"tag": "foo", "count": 3},
        {"tag": "bar", "count": 1},
        {"tag": "baz", "count": 1},
    ]
    parsed = json.loads(bundle_catalog_top_tag_counts_export_json(rows))
    assert parsed == rows
    csv_text = bundle_catalog_top_tag_counts_table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "tag,count"
    assert "foo,3" in csv_text
    assert bundle_catalog_top_tag_counts_export_json([]) == "[]"
    assert bundle_catalog_top_tag_counts_table_rows_csv([]) == ""

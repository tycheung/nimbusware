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
    bundle_faiss_build_command_snippet,
    bundle_faiss_build_command_snippet_explicit,
    bundle_faiss_build_powershell_snippet_explicit,
    bundle_faiss_bundle_order_duplicate_ids_caption,
    bundle_faiss_bundle_order_json_file_bytes_caption,
    bundle_faiss_catalog_index_mtime_delta_caption,
    bundle_faiss_catalog_order_count_parity_caption,
    bundle_faiss_catalog_order_id_set_mismatch_caption,
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
    bundle_faiss_readiness_summary_table_rows,
    bundle_faiss_readiness_summary_table_rows_csv,
)


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
    root = Path(__file__).resolve().parents[2]
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

    root = Path(__file__).resolve().parents[2]
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



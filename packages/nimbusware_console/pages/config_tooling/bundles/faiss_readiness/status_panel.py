from __future__ import annotations

from pathlib import Path
from typing import Any

# fo501: allowed star-from-barrel — bundles/_shared re-exports workflows/_shared
from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def render_faiss_status_panel(
    repo_root: Path,
    *,
    _faiss: dict[str, Any],
    _faiss_sum: dict[str, Any],
) -> None:
        st.caption(
            "File presence matches **GET /v1/bundles/search** / ``bundle_faiss_index_ready``. "
            "When **stale** is true, ``catalog.yaml`` is newer than both index files on disk — "
            "re-run the build script after catalog edits. "
            + bundle_faiss_index_workflow_caption_note(),
        )
        _faiss = bundle_faiss_index_status(repo_root)
        _faiss_sum = bundle_faiss_readiness_summary(repo_root)
        _faiss_cat_ver_cap = bundle_faiss_catalog_yaml_version_caption(repo_root)
        if _faiss_cat_ver_cap:
            st.caption(_faiss_cat_ver_cap)
        _faiss_bucket_cap = bundle_faiss_readiness_code_caption(repo_root)
        if _faiss_bucket_cap:
            st.caption(_faiss_bucket_cap)
        _faiss_headline_cap = bundle_faiss_readiness_headline_caption(repo_root)
        if _faiss_headline_cap:
            st.caption(_faiss_headline_cap)
        _faiss_missing_cap = bundle_faiss_readiness_missing_caption(repo_root)
        if _faiss_missing_cap:
            st.caption(_faiss_missing_cap)
        _faiss_missing_rows = bundle_faiss_readiness_missing_paths_table_rows(_faiss_sum)
        if _faiss_missing_rows:
            _faiss_missing_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _faiss_missing_slug = bundle_faiss_readiness_export_filename_slug(repo_root)
            _faiss_missing_json = bundle_faiss_readiness_missing_paths_export_json(
                _faiss_missing_rows,
            )
            _faiss_missing_csv = bundle_faiss_readiness_missing_paths_table_rows_csv(
                _faiss_missing_rows,
            )
            _faiss_missing_dl_json_col, _faiss_missing_dl_csv_col = st.columns(2)
            with _faiss_missing_dl_json_col:
                st.download_button(
                    label="Download FAISS missing index paths JSON",
                    data=_faiss_missing_json.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_missing_paths_"
                        f"{_faiss_missing_slug}_{_faiss_missing_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_faiss_missing_paths_json",
                )
            with _faiss_missing_dl_csv_col:
                if _faiss_missing_csv:
                    st.download_button(
                        label="Download FAISS missing index paths CSV",
                        data=_faiss_missing_csv.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_missing_paths_"
                            f"{_faiss_missing_slug}_{_faiss_missing_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_faiss_missing_paths_csv",
                    )
        _faiss_stale_cap = bundle_faiss_index_stale_caption(repo_root)
        if _faiss_stale_cap:
            st.caption(_faiss_stale_cap)
        _faiss_parity_cap = bundle_faiss_catalog_order_count_parity_caption(repo_root)
        if _faiss_parity_cap:
            st.caption(_faiss_parity_cap)
        _faiss_id_set_cap = bundle_faiss_catalog_order_id_set_mismatch_caption(repo_root)
        if _faiss_id_set_cap:
            st.caption(_faiss_id_set_cap)
            _faiss_mismatch_dd = bundle_faiss_index_operator_drilldown(repo_root)
            _faiss_mismatch_rows = bundle_faiss_id_set_mismatch_table_rows(
                _faiss_mismatch_dd,
            )
            if _faiss_mismatch_rows:
                _faiss_mismatch_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _faiss_mismatch_slug = bundle_faiss_operator_drilldown_export_filename_slug(
                    repo_root,
                )
                _faiss_mismatch_json = bundle_faiss_id_set_mismatch_export_json(
                    _faiss_mismatch_rows,
                )
                _faiss_mismatch_csv = bundle_faiss_id_set_mismatch_table_rows_csv(
                    _faiss_mismatch_rows,
                )
                _faiss_mismatch_dl_json_col, _faiss_mismatch_dl_csv_col = st.columns(2)
                with _faiss_mismatch_dl_json_col:
                    st.download_button(
                        label="Download FAISS id-set mismatch JSON",
                        data=_faiss_mismatch_json.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_id_set_mismatch_"
                            f"{_faiss_mismatch_slug}_{_faiss_mismatch_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_faiss_id_set_mismatch_json",
                    )
                with _faiss_mismatch_dl_csv_col:
                    if _faiss_mismatch_csv:
                        st.download_button(
                            label="Download FAISS id-set mismatch CSV",
                            data=_faiss_mismatch_csv.encode("utf-8"),
                            file_name=(
                                "hermes_bundle_faiss_id_set_mismatch_"
                                f"{_faiss_mismatch_slug}_{_faiss_mismatch_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_faiss_id_set_mismatch_csv",
                        )
        _faiss_dup_cap = bundle_faiss_bundle_order_duplicate_ids_caption(repo_root)
        if _faiss_dup_cap:
            st.caption(_faiss_dup_cap)
            _faiss_dup_dd = bundle_faiss_index_operator_drilldown(repo_root)
            _faiss_dup_rows = bundle_faiss_duplicate_id_table_rows(_faiss_dup_dd)
            if _faiss_dup_rows:
                _faiss_dup_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _faiss_dup_slug = bundle_faiss_operator_drilldown_export_filename_slug(
                    repo_root,
                )
                _faiss_dup_json = bundle_faiss_duplicate_id_export_json(_faiss_dup_rows)
                _faiss_dup_csv = bundle_faiss_duplicate_id_table_rows_csv(_faiss_dup_rows)
                _faiss_dup_dl_json_col, _faiss_dup_dl_csv_col = st.columns(2)
                with _faiss_dup_dl_json_col:
                    st.download_button(
                        label="Download FAISS duplicate bundle ids JSON",
                        data=_faiss_dup_json.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_duplicate_ids_"
                            f"{_faiss_dup_slug}_{_faiss_dup_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_faiss_duplicate_ids_json",
                    )
                with _faiss_dup_dl_csv_col:
                    if _faiss_dup_csv:
                        st.download_button(
                            label="Download FAISS duplicate bundle ids CSV",
                            data=_faiss_dup_csv.encode("utf-8"),
                            file_name=(
                                "hermes_bundle_faiss_duplicate_ids_"
                                f"{_faiss_dup_slug}_{_faiss_dup_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_faiss_duplicate_ids_csv",
                        )
        _faiss_mtime_cap = bundle_faiss_catalog_index_mtime_delta_caption(repo_root)
        if _faiss_mtime_cap:
            st.caption(_faiss_mtime_cap)
        _faiss_idx_n_cap = bundle_faiss_index_dir_file_count_caption(repo_root)
        if _faiss_idx_n_cap:
            st.caption(_faiss_idx_n_cap)
        _faiss_idx_sub_cap = bundle_faiss_index_dir_subdirectory_count_caption(repo_root)
        if _faiss_idx_sub_cap:
            st.caption(_faiss_idx_sub_cap)
        _faiss_idx_list_trunc_cap = bundle_faiss_index_dir_listing_truncated_caption(repo_root)
        if _faiss_idx_list_trunc_cap:
            st.caption(_faiss_idx_list_trunc_cap)
        _faiss_large_cap = bundle_faiss_index_large_file_caption(repo_root)
        if _faiss_large_cap:
            st.caption(_faiss_large_cap)
        _faiss_bo_bytes_cap = bundle_faiss_bundle_order_json_file_bytes_caption(repo_root)
        if _faiss_bo_bytes_cap:
            st.caption(_faiss_bo_bytes_cap)
        st.caption(f"**{_faiss_sum['headline']}** — {_faiss_sum['detail']}")
        if _faiss_sum.get("missing"):
            st.caption("Missing paths: ``" + "``, ``".join(_faiss_sum["missing"]) + "``")
        if _faiss["ready"]:
            st.caption(
                "FAISS bundle index: **present** under ``configs/bundles/index/`` "
                "(``faiss.index`` + ``bundle_order.json``). Search uses vector top-k when "
                "both files exist and ``faiss`` is installed (same as ``BundleCatalog.search``). "
                + bundle_faiss_index_workflow_caption_note(),
            )
            if _faiss.get("stale") is True:
                st.warning(
                    "Index may be **out of date** (catalog mtime newer than index files). "
                    "Rebuild from repo root (see command block below or **Poetry optional "
                    "groups and FAISS** in ``PLAN_GAP.md``). CI smoke: ``"
                    f"{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``.",
                )
                st.code(bundle_faiss_build_command_snippet_explicit(repo_root), language="bash")
                with st.expander("Windows: rebuild (copy-paste)", expanded=False):
                    st.code(
                        bundle_faiss_build_powershell_snippet_explicit(repo_root),
                        language="powershell",
                    )
                    st.code(
                        bundle_faiss_invoke_ps1_snippet_explicit(repo_root),
                        language="powershell",
                    )
        else:
            st.caption(
                "FAISS bundle index: **not present** — search uses tag/id overlap only. "
                "From the repo root (same defaults as **bundle_faiss_index** workflow). "
                + bundle_faiss_index_workflow_caption_note(),
            )
            st.code(bundle_faiss_build_command_snippet(), language="bash")
            with st.expander("Windows: Poetry + build (copy-paste)", expanded=False):
                st.caption(
                    "Same commands as bash; optional wrapper "
                    "``scripts/build_bundle_faiss_index.ps1``.",
                )
                st.code(
                    bundle_faiss_build_powershell_snippet_explicit(repo_root),
                    language="powershell",
                )
                st.caption("One-liner from any directory (absolute paths):")
                st.code(
                    bundle_faiss_invoke_ps1_snippet_explicit(repo_root),
                    language="powershell",
                )
            st.caption(
                "POSIX: optional ``bash scripts/build_bundle_faiss_index.sh`` "
                "(defaults repo root to the script's parent). "
                "``--help`` on the Python script lists ``--repo-root``, ``--catalog``, "
                "``--out-dir``. "
                "See **Poetry optional groups and FAISS** in ``PLAN_GAP.md``; workflow file ``"
                f"{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``.",
            )

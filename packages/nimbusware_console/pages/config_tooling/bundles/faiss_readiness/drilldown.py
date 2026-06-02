from __future__ import annotations

from pathlib import Path

# fo501: allowed star-from-barrel — bundles/_shared re-exports workflows/_shared
from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def render_faiss_drilldown_panel(*, repo_root: Path) -> None:
    with st.expander("Operator drill-down (fo142)", expanded=False):
        st.caption(
            "Read-only: per-file sizes + UTC mtimes + bounded ``configs/bundles/index`` "
            "listing; no ``faiss`` import. Copy-paste rebuild uses the same resolved root "
            "as this console."
        )
        _faiss_dd = bundle_faiss_index_operator_drilldown(repo_root)
        st.json(_faiss_dd)
        _faiss_listing_rows = bundle_faiss_index_dir_listing_table_rows(_faiss_dd)
        if _faiss_listing_rows:
            _faiss_listing_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _faiss_listing_slug = bundle_faiss_operator_drilldown_export_filename_slug(
                repo_root,
            )
            _faiss_listing_json = bundle_faiss_index_dir_listing_export_json(
                _faiss_listing_rows,
            )
            _faiss_listing_csv = bundle_faiss_index_dir_listing_table_rows_csv(
                _faiss_listing_rows,
            )
            _faiss_listing_dl_json_col, _faiss_listing_dl_csv_col = st.columns(2)
            with _faiss_listing_dl_json_col:
                st.download_button(
                    label="Download FAISS index directory listing JSON",
                    data=_faiss_listing_json.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_index_listing_"
                        f"{_faiss_listing_slug}_{_faiss_listing_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_faiss_index_listing_json",
                )
            with _faiss_listing_dl_csv_col:
                if _faiss_listing_csv:
                    st.download_button(
                        label="Download FAISS index directory listing CSV",
                        data=_faiss_listing_csv.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_index_listing_"
                            f"{_faiss_listing_slug}_{_faiss_listing_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_faiss_index_listing_csv",
                    )
        _faiss_dd_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _faiss_dd_slug = bundle_faiss_operator_drilldown_export_filename_slug(repo_root)
        _faiss_dd_json = bundle_faiss_index_operator_drilldown_export_json(repo_root)
        st.download_button(
            label="Download FAISS operator drill-down JSON",
            data=_faiss_dd_json.encode("utf-8"),
            file_name=(f"hermes_bundle_faiss_drilldown_{_faiss_dd_slug}_{_faiss_dd_ts}.json"),
            mime="application/json",
            key="hermes_dl_bundle_faiss_operator_drilldown_json",
        )
        st.caption(
            "Rebuild with explicit ``--repo-root`` (matches **Effective repo root** above).",
        )
        st.code(bundle_faiss_build_command_snippet_explicit(repo_root), language="bash")

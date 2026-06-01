from __future__ import annotations

from nimbusware_console.pages.config_tooling.workflows._shared_catalog import bundle_memory_analytics_from_store, bundle_memory_caption


def render_workflows_bundle_memory_section() -> None:
    with st.expander("Bundle usage memory (integrator outcomes)", expanded=False):
                from hermes_extensions.bundle_memory_factory import build_bundle_outcome_store

                _bm_store = build_bundle_outcome_store(allow_in_memory=True)
                _bm_analytics = bundle_memory_analytics_from_store(_bm_store)
                st.caption(bundle_memory_caption(_bm_analytics))
                _bm_rows = _bm_analytics.get("table_rows") or []
                if _bm_rows:
                    st.dataframe(_bm_rows, use_container_width=True, hide_index=True)
                else:
                    st.caption("No integrator bundle outcomes recorded yet.")

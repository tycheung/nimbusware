from __future__ import annotations

from pathlib import Path

# re-export via bundles/_shared barrel
from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.drilldown import (
    render_faiss_drilldown_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.exports import (
    render_faiss_exports_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.local_search import (
    render_faiss_local_search_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.status_panel import (
    render_faiss_status_panel,
)


def render_faiss_readiness_section(*, repo_root: Path) -> None:
    with st.expander("FAISS index readiness (paths & catalog freshness)", expanded=False):
        st.caption(
            "File presence matches **GET /v1/bundles/search** / ``bundle_faiss_index_ready``. "
            "When **stale** is true, ``catalog.yaml`` is newer than both index files on disk — "
            "re-run the build script after catalog edits. "
            + bundle_faiss_index_workflow_caption_note(),
        )
        _faiss = bundle_faiss_index_status(repo_root)
        _faiss_sum = bundle_faiss_readiness_summary(repo_root)
        render_faiss_status_panel(repo_root, _faiss=_faiss, _faiss_sum=_faiss_sum)
        render_faiss_drilldown_panel(repo_root=repo_root)
        render_faiss_exports_panel(repo_root, _faiss=_faiss, _faiss_sum=_faiss_sum)
    render_faiss_local_search_panel(repo_root=repo_root)

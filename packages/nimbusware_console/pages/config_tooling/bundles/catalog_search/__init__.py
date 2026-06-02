# re-export via bundles/_shared barrel
from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.bundles.catalog_search.rollups_panel import (
    _render_catalog_rollups_panel,
)
from nimbusware_console.pages.config_tooling.bundles.catalog_search.summary_panel import (
    _render_catalog_summary_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness import (
    render_faiss_readiness_section,
)


def render_bundle_catalog_search_section() -> None:
    with st.expander("Bundle catalog search (local repo)", expanded=False):
        st.caption(
            "Read-only: same ``search_bundles`` helper as **GET /v1/bundles/search** over "
            "``configs/bundles/catalog.yaml``. Uses **NIMBUSWARE_REPO_ROOT** (resolved); "
            "matches the API frozen repo root when both use the same env.",
        )
        repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{repo_root}`")
        _render_catalog_summary_panel(repo_root)
        _render_catalog_rollups_panel(repo_root)
    render_faiss_readiness_section(repo_root=repo_root)

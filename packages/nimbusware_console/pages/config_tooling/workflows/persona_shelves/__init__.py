"""``persona_shelves`` config tooling section."""

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.workflows.persona_shelves.catalog_panel import (
    _render_persona_catalog_panel,
)
from nimbusware_console.pages.config_tooling.workflows.persona_shelves.critique_panel import (
    _render_critique_pairings_panel,
)


def render_workflows_persona_shelves_section() -> None:
    with st.expander("Persona shelves (local repo)", expanded=False):
        st.caption(
            "Read-only: same ``PersonaShelf`` + ``configs/personas/shelves.yaml`` shape as "
            "**GET /v1/personas** (``NIMBUSWARE_REPO_ROOT`` / frozen repo root). No API call.",
        )
        st.caption(persona_catalog_taxonomy_scope_frozen_caption())
        _proot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{_proot}`")
        _render_critique_pairings_panel(_proot)
        _render_persona_catalog_panel(_proot)

from nimbusware_console.pages.config_tooling.bundles import (
    render_config_tooling_bundles_section,
)
from nimbusware_console.pages.config_tooling.ollama_models import (
    render_ollama_models_section,
)
from nimbusware_console.pages.config_tooling.workflows import (
    render_config_tooling_workflows_section,
)


def render_config_tooling_section() -> None:
    render_ollama_models_section()
    st.divider()
    render_config_tooling_bundles_section()
    render_config_tooling_workflows_section()

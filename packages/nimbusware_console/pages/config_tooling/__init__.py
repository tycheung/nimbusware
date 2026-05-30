"""Config tooling page sections."""

from nimbusware_console.pages.config_tooling.bundles import (
    render_config_tooling_bundles_section,
)
from nimbusware_console.pages.config_tooling.workflows import (
    render_config_tooling_workflows_section,
)

def render_config_tooling_section() -> None:
    render_config_tooling_bundles_section()
    render_config_tooling_workflows_section()

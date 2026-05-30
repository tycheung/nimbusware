"""Config tooling — workflow explainers and disk apply sections."""

from __future__ import annotations

from nimbusware_console.pages.config_tooling.workflows.bundle_editor import (
    render_workflows_bundle_editor_section,
)
from nimbusware_console.pages.config_tooling.workflows.bundle_memory import (
    render_workflows_bundle_memory_section,
)
from nimbusware_console.pages.config_tooling.workflows.integrator import (
    render_workflows_integrator_section,
)
from nimbusware_console.pages.config_tooling.workflows.persona_editor import (
    render_workflows_persona_editor_section,
)
from nimbusware_console.pages.config_tooling.workflows.persona_shelves import (
    render_workflows_persona_shelves_section,
)
from nimbusware_console.pages.config_tooling.workflows.prune import (
    render_workflows_prune_section,
)


def render_config_tooling_workflows_section() -> None:
    render_workflows_bundle_memory_section()
    render_workflows_bundle_editor_section()
    render_workflows_integrator_section()
    render_workflows_persona_shelves_section()
    render_workflows_persona_editor_section()
    render_workflows_prune_section()

__all__ = ["render_config_tooling_workflows_section"]

"""Workflow-driven security scan metadata on verifier failures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)
from nimbusware_env.env_flags import env_force_off, env_force_on


def security_scan_metadata_on_verify_enabled(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """True when env enables (and not kill-switched), else workflow YAML flag (§14 #18).

    ``HERMES_ATTACH_SECURITY_SCAN_METADATA``:
      ``1`` / ``true`` / ``yes`` forces attach even when workflow is off;
      ``0`` / ``false`` / ``no`` disables attach even when workflow is on (ops kill-switch).
    When unset, follow ``security_scan_metadata_on_verify`` on the frozen workflow YAML.
    """
    if env_force_off("HERMES_ATTACH_SECURITY_SCAN_METADATA"):
        return False
    if env_force_on("HERMES_ATTACH_SECURITY_SCAN_METADATA"):
        return True
    return parse_security_scan_metadata_on_verify_workflow(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )

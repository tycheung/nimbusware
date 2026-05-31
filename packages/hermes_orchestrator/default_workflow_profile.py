"""Default workflow profile for API ingress and orchestrator (§14 optional product)."""
from __future__ import annotations

import os

_PRODUCTION_PROFILE = "nimbusware_production"
def default_workflow_profile() -> str:
    """Return default profile; override with ``NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE``."""
    raw = os.environ.get("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", _PRODUCTION_PROFILE).strip()
    return raw or _PRODUCTION_PROFILE

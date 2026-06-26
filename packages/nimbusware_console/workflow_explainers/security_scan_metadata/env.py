from __future__ import annotations

from typing import Any

from nimbusware_console.explainer_core.env_captions import env_tri_state_yaml_follows_summary


def _nimbusware_attach_security_scan_metadata_env_summary() -> dict[str, Any]:
    return dict(env_tri_state_yaml_follows_summary("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA"))

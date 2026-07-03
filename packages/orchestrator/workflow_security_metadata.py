from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.workflow_profiles import workflow_profile_dict


def _coerce_security_scan_metadata_enabled_value(ev: object) -> bool:
    if isinstance(ev, bool):
        return ev
    if isinstance(ev, (int, float)):
        return bool(ev)
    if isinstance(ev, str):
        return ev.strip().lower() in ("1", "true", "yes", "on")
    return False


def _parse_security_scan_metadata_value(v: object) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(v, list):
        return False
    if isinstance(v, dict):
        if "enabled" not in v:
            return False
        return _coerce_security_scan_metadata_enabled_value(v.get("enabled"))
    return False


def parse_security_scan_metadata_on_verify_workflow(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """Read ``security_scan_metadata_on_verify`` from workflow YAML; default ``False``."""
    if workflow_profile is None or not str(workflow_profile).strip():
        return False
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return False
    v = raw.get("security_scan_metadata_on_verify")
    return _parse_security_scan_metadata_value(v) if v is not None else False

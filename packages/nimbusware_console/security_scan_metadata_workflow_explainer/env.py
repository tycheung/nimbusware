from __future__ import annotations

import os
from typing import Any


def _hermes_attach_security_scan_metadata_env_summary() -> dict[str, Any]:
    raw = os.environ.get("HERMES_ATTACH_SECURITY_SCAN_METADATA", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": False,
            "unset_follows_yaml": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "forces_off": True,
            "forces_on": False,
            "unset_follows_yaml": False,
        }
    if low in ("1", "true", "yes"):
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": True,
            "unset_follows_yaml": False,
        }
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset_follows_yaml": True,
        "unrecognised_value": True,
    }



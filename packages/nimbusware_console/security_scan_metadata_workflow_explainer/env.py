from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_tri_state


def _nimbusware_attach_security_scan_metadata_env_summary() -> dict[str, Any]:
    raw = env_tri_state("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA")
    if raw is None:
        return {
            "raw": "",
            "forces_off": False,
            "forces_on": False,
            "unset_follows_yaml": True,
        }
    if raw == "off":
        return {
            "raw": "0",
            "forces_off": True,
            "forces_on": False,
            "unset_follows_yaml": False,
        }
    if raw == "on":
        return {
            "raw": "1",
            "forces_off": False,
            "forces_on": True,
            "unset_follows_yaml": False,
        }
    return {
        "raw": "",
        "forces_off": False,
        "forces_on": False,
        "unset_follows_yaml": True,
        "unrecognised_value": True,
    }

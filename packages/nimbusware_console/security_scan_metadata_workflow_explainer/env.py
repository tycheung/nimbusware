from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import csv
import json
import os
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from nimbusware_config.workflow_read import (
    parse_security_scan_metadata_on_verify_workflow,
    security_scan_metadata_on_verify_enabled,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under

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



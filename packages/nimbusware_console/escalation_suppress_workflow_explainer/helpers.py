from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from nimbusware_config.workflow_read import (
    escalation_policy_breadth,
    load_yaml,
    parse_escalation_workflow_block,
    workflow_profile_dict,
    workflow_profile_path,
)
from nimbusware_console.components.workflow_explainer_helpers import (
    json_safe_yaml_fragment,
    mtime_iso_utc,
    relative_under,
)

def _age_seconds_utc(iso: str | None) -> int | None:
    if not isinstance(iso, str):
        return None
    stripped = iso.strip()
    if not stripped:
        return None
    normalised = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if age < 0:
        return None
    return age



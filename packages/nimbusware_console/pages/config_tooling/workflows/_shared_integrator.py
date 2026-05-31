from __future__ import annotations

import csv
import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from nimbusware_console.integrator_workflow_apply import (
    ALLOW_WORKFLOW_YAML_WRITE_ENV,
    apply_agent_evaluator_yaml,
    apply_full_workflow_yaml,
    apply_integrator_gate_yaml,
    prepare_agent_evaluator_apply,
    prepare_full_workflow_apply,
    prepare_integrator_gate_apply,
    workflow_yaml_write_enabled,
)
from nimbusware_console.integrator_workflow_preview import (
    full_workflow_merge_added_top_level_caption,
    full_workflow_merge_attention_export_filename_slug,
    full_workflow_merge_attention_export_json,
    full_workflow_merge_attention_operator_metrics,
    full_workflow_merge_attention_operator_metrics_caption,
    full_workflow_merge_attention_operator_metrics_export_filename_slug,
    full_workflow_merge_attention_operator_metrics_export_json,
    full_workflow_merge_attention_operator_metrics_table_rows,
    full_workflow_merge_attention_operator_metrics_table_rows_csv,
    full_workflow_merge_attention_rows,
    full_workflow_merge_attention_table_rows_csv,
    full_workflow_merge_changed_top_level_caption,
    full_workflow_merge_diff,
    full_workflow_merge_diff_audit_fingerprint_caption,
    full_workflow_merge_diff_export_filename_slug,
    full_workflow_merge_diff_export_json,
    full_workflow_merge_diff_operator_metrics,
    full_workflow_merge_diff_operator_metrics_caption,
    full_workflow_merge_diff_operator_metrics_export_filename_slug,
    full_workflow_merge_diff_operator_metrics_export_json,
    full_workflow_merge_diff_operator_metrics_table_rows,
    full_workflow_merge_diff_operator_metrics_table_rows_csv,
    full_workflow_merge_diff_table_rows,
    full_workflow_merge_diff_table_rows_csv,
    full_workflow_merge_disk_only_top_level_caption,
    full_workflow_merge_overview_caption,
    full_workflow_merge_paste_only_top_level_caption,
    full_workflow_merge_pasted_top_level_caption,
    full_workflow_merge_removed_top_level_caption,
    full_workflow_merge_subtree_added_fields_caption,
    full_workflow_merge_subtree_changed_fields_caption,
    full_workflow_merge_subtree_overview_caption,
    full_workflow_merge_subtree_removed_fields_caption,
    full_workflow_merge_top_level_churn_count_caption,
    full_workflow_merge_unchanged_top_level_caption,
    full_workflow_merge_unchanged_with_churn_caption,
    integrator_preview_payload,
    list_workflow_profile_keys,
    parse_full_workflow_yaml_paste,
)

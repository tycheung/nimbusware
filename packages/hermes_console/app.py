"""Run list, timeline, findings, critic matrix, retry / escalate (plan §7, §14 #11)."""

from __future__ import annotations

from hermes_env import load_dotenv

load_dotenv()

import csv
import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import streamlit as st

from hermes_console.agent_evaluator_display import (
    agent_evaluator_auto_actions_caption,
    agent_evaluator_auto_actions_table_rows,
    agent_evaluator_evaluation_caption,
    agent_evaluator_from_timeline,
    agent_evaluator_operator_metrics,
    agent_evaluator_operator_metrics_caption,
    agent_evaluator_operator_metrics_export_json,
    agent_evaluator_operator_metrics_table_rows,
    agent_evaluator_operator_metrics_table_rows_csv,
    agent_evaluator_session_caption,
    agent_evaluator_summary_rows,
    agent_evaluator_timeline_export_filename_slug,
    agent_evaluator_timeline_export_json,
    agent_evaluator_timeline_table_rows_csv,
)
from hermes_console.agent_evaluator_workflow_explainer import (
    agent_evaluator_auto_create_env_gate_caption,
    agent_evaluator_auto_promote_env_gate_caption,
    agent_evaluator_env_gate_caption,
    agent_evaluator_explainer_export_json,
    agent_evaluator_explainer_table_rows,
    agent_evaluator_explainer_table_rows_csv,
    agent_evaluator_export_filename_slug,
    agent_evaluator_llm_evaluation_enabled_caption,
    agent_evaluator_persona_id_caption,
    agent_evaluator_workflow_explainer_operator_metrics,
    agent_evaluator_workflow_explainer_operator_metrics_caption,
    agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug,
    agent_evaluator_workflow_explainer_operator_metrics_export_json,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv,
    agent_evaluator_workflow_explainer_payload,
    agent_evaluator_workflow_yaml_version_caption,
    agent_evaluator_would_emit_caption,
    agent_evaluator_yaml_key_present_caption,
    agent_evaluator_yaml_parsed_enabled_caption,
    agent_evaluator_yaml_raw_type_caption,
    agent_evaluator_yaml_true_bool_count_caption,
)
from hermes_console.bundle_catalog_editor import (
    bundle_editor_patch_payload,
    bundle_editor_validation_issues,
)
from hermes_console.bundle_catalog import (
    BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH,
    bundle_catalog_bundle_count_caption,
    bundle_catalog_bundle_ids_sample,
    bundle_catalog_bundles_without_id_caption,
    bundle_catalog_bundles_without_id_count,
    bundle_catalog_bundles_without_id_rollup,
    bundle_catalog_bundles_without_id_rollup_export_filename_slug,
    bundle_catalog_bundles_without_id_rollup_export_json,
    bundle_catalog_bundles_without_id_rollup_operator_metrics,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_caption,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv,
    bundle_catalog_bundles_without_id_rollup_table_rows,
    bundle_catalog_bundles_without_id_rollup_table_rows_csv,
    bundle_catalog_bundles_without_tags_caption,
    bundle_catalog_bundles_without_tags_count,
    bundle_catalog_bundles_without_tags_rollup,
    bundle_catalog_bundles_without_tags_rollup_export_filename_slug,
    bundle_catalog_bundles_without_tags_rollup_export_json,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_filename_slug,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_json,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows,
    bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows_csv,
    bundle_catalog_bundles_without_tags_rollup_table_rows,
    bundle_catalog_bundles_without_tags_rollup_table_rows_csv,
    bundle_catalog_distinct_tag_count_caption,
    bundle_catalog_distinct_tags_sample,
    bundle_catalog_local_bundles,
    bundle_catalog_local_bundles_export_json,
    bundle_catalog_local_bundles_table_rows,
    bundle_catalog_local_bundles_table_rows_csv,
    bundle_catalog_local_export_filename_slug,
    bundle_catalog_local_summary,
    bundle_catalog_local_summary_export_filename_slug,
    bundle_catalog_local_summary_export_json,
    bundle_catalog_local_summary_operator_metrics,
    bundle_catalog_local_summary_operator_metrics_caption,
    bundle_catalog_local_summary_operator_metrics_export_filename_slug,
    bundle_catalog_local_summary_operator_metrics_export_json,
    bundle_catalog_local_summary_operator_metrics_table_rows,
    bundle_catalog_local_summary_operator_metrics_table_rows_csv,
    bundle_catalog_local_summary_table_rows,
    bundle_catalog_local_summary_table_rows_csv,
    bundle_catalog_top_tag_caption,
    bundle_catalog_top_tag_counts,
    bundle_catalog_top_tag_counts_export_json,
    bundle_catalog_top_tag_counts_table_rows_csv,
    bundle_faiss_build_command_snippet,
    bundle_faiss_build_command_snippet_explicit,
    bundle_faiss_build_powershell_snippet_explicit,
    bundle_faiss_bundle_order_duplicate_ids_caption,
    bundle_faiss_bundle_order_json_file_bytes_caption,
    bundle_faiss_catalog_index_mtime_delta_caption,
    bundle_faiss_catalog_order_count_parity_caption,
    bundle_faiss_catalog_order_id_set_mismatch_caption,
    bundle_faiss_catalog_yaml_version_caption,
    bundle_faiss_duplicate_id_export_json,
    bundle_faiss_duplicate_id_table_rows,
    bundle_faiss_duplicate_id_table_rows_csv,
    bundle_faiss_id_set_mismatch_export_json,
    bundle_faiss_id_set_mismatch_table_rows,
    bundle_faiss_id_set_mismatch_table_rows_csv,
    bundle_faiss_index_dir_file_count_caption,
    bundle_faiss_index_dir_listing_export_json,
    bundle_faiss_index_dir_listing_table_rows,
    bundle_faiss_index_dir_listing_table_rows_csv,
    bundle_faiss_index_dir_listing_truncated_caption,
    bundle_faiss_index_dir_subdirectory_count_caption,
    bundle_faiss_index_large_file_caption,
    bundle_faiss_index_operator_drilldown,
    bundle_faiss_index_operator_drilldown_export_json,
    bundle_faiss_index_stale_caption,
    bundle_faiss_index_status,
    bundle_faiss_index_status_export_json,
    bundle_faiss_index_status_table_rows,
    bundle_faiss_index_status_table_rows_csv,
    bundle_faiss_index_workflow_caption_note,
    bundle_faiss_invoke_ps1_snippet_explicit,
    bundle_faiss_operator_drilldown_export_filename_slug,
    bundle_faiss_readiness_code_caption,
    bundle_faiss_readiness_export_filename_slug,
    bundle_faiss_readiness_headline_caption,
    bundle_faiss_readiness_missing_caption,
    bundle_faiss_readiness_missing_paths_export_json,
    bundle_faiss_readiness_missing_paths_table_rows,
    bundle_faiss_readiness_missing_paths_table_rows_csv,
    bundle_faiss_readiness_summary,
    bundle_faiss_readiness_summary_export_json,
    bundle_faiss_readiness_summary_operator_metrics,
    bundle_faiss_readiness_summary_operator_metrics_caption,
    bundle_faiss_readiness_summary_operator_metrics_export_filename_slug,
    bundle_faiss_readiness_summary_operator_metrics_export_json,
    bundle_faiss_readiness_summary_operator_metrics_table_rows,
    bundle_faiss_readiness_summary_operator_metrics_table_rows_csv,
    bundle_faiss_readiness_summary_table_rows,
    bundle_faiss_readiness_summary_table_rows_csv,
    bundle_search_after_hits_stale_caption,
    bundle_search_empty_hits_readiness_caption,
    bundle_search_faiss_ready_caption,
    bundle_search_filename_slug,
    bundle_search_hit_count_caption,
    bundle_search_hits_export_json,
    bundle_search_hits_from_blob,
    bundle_search_hits_summary_caption,
    bundle_search_hits_table_rows_csv,
    bundle_search_k_caption,
    bundle_search_operator_metrics,
    bundle_search_operator_metrics_caption,
    bundle_search_operator_metrics_export_filename_slug,
    bundle_search_operator_metrics_export_json,
    bundle_search_operator_metrics_table_rows,
    bundle_search_operator_metrics_table_rows_csv,
    bundle_search_query_length_caption,
    bundle_search_top_hit_preview_caption,
    run_bundle_catalog_search,
)
from hermes_console.console_theme import (
    streamlit_theme_defaults_caption,
    streamlit_white_label_deferred_caption,
)
from hermes_console.critic_matrix_display import (
    critic_matrix_export_filename_slug,
    critic_matrix_export_json,
    critic_matrix_operator_metrics,
    critic_matrix_operator_metrics_caption,
    critic_matrix_operator_metrics_export_json,
    critic_matrix_operator_metrics_table_rows,
    critic_matrix_operator_metrics_table_rows_csv,
    critic_matrix_rows_from_events,
    critic_matrix_table_rows_csv,
)
from hermes_console.escalation_suppress_workflow_explainer import (
    escalation_policy_export_filename_slug,
    escalation_policy_yaml_age_caption,
    escalation_policy_yaml_anti_deadlock_min_progress_caption,
    escalation_policy_yaml_anti_deadlock_shape_caption,
    escalation_policy_yaml_deadlock_minutes_caption,
    escalation_policy_yaml_file_bytes_caption,
    escalation_policy_yaml_key_count_caption,
    escalation_policy_yaml_keys_all_export_json,
    escalation_policy_yaml_keys_all_table_rows,
    escalation_policy_yaml_keys_all_table_rows_csv,
    escalation_policy_yaml_keys_sample_caption,
    escalation_policy_yaml_max_retries_caption,
    escalation_policy_yaml_mtime_caption,
    escalation_policy_yaml_relpath_caption,
    escalation_policy_yaml_top_level_kinds_caption,
    escalation_policy_yaml_top_level_kinds_export_json,
    escalation_policy_yaml_top_level_kinds_table_rows,
    escalation_policy_yaml_top_level_kinds_table_rows_csv,
    escalation_policy_yaml_verification_shape_caption,
    escalation_policy_yaml_version_caption,
    escalation_suppress_explainer_export_json,
    escalation_suppress_explainer_table_rows,
    escalation_suppress_explainer_table_rows_csv,
    escalation_suppress_export_filename_slug,
    escalation_suppress_flag_caption,
    escalation_suppress_workflow_explainer_operator_metrics,
    escalation_suppress_workflow_explainer_operator_metrics_caption,
    escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug,
    escalation_suppress_workflow_explainer_operator_metrics_export_json,
    escalation_suppress_workflow_explainer_operator_metrics_table_rows,
    escalation_suppress_workflow_explainer_operator_metrics_table_rows_csv,
    escalation_suppress_workflow_explainer_payload,
    escalation_yaml_key_present_caption,
)
from hermes_console.findings_display import (
    findings_empty_caption,
    findings_export_filename_slug,
    findings_export_json,
    findings_list_from_response,
    findings_operator_metrics,
    findings_operator_metrics_caption,
    findings_operator_metrics_export_json,
    findings_operator_metrics_table_rows,
    findings_operator_metrics_table_rows_csv,
    findings_table_rows,
    findings_table_rows_csv,
)
from hermes_console.integrator_gate_display import (
    integrator_gate_compatibility_ranking_caption,
    integrator_gate_compatibility_ranking_table_rows,
    integrator_gate_delta_bundle_changed_caption,
    integrator_gate_delta_export_filename_slug,
    integrator_gate_delta_export_json,
    integrator_gate_delta_from_timeline,
    integrator_gate_delta_operator_metrics,
    integrator_gate_delta_operator_metrics_caption,
    integrator_gate_delta_operator_metrics_export_json,
    integrator_gate_delta_operator_metrics_table_rows_csv,
    integrator_gate_delta_operator_table_rows,
    integrator_gate_delta_summary_rows,
    integrator_gate_delta_summary_rows_csv,
    integrator_gate_delta_transition_caption,
    integrator_gate_delta_verdict_changed_caption,
    integrator_gate_from_timeline,
    integrator_gate_history_distinct_bundles_caption,
    integrator_gate_history_entry_count_caption,
    integrator_gate_history_export_filename_slug,
    integrator_gate_history_export_json,
    integrator_gate_history_failure_reason_caption,
    integrator_gate_history_from_timeline,
    integrator_gate_history_latest_margin_caption,
    integrator_gate_history_metrics_table_rows,
    integrator_gate_history_operator_metrics,
    integrator_gate_history_operator_metrics_caption,
    integrator_gate_history_operator_metrics_export_json,
    integrator_gate_history_operator_metrics_table_rows_csv,
    integrator_gate_history_score_range_caption,
    integrator_gate_history_table_rows,
    integrator_gate_history_table_rows_csv,
    integrator_gate_history_verdict_tally_caption,
    integrator_gate_latest_bundle_id_caption,
    integrator_gate_latest_export_filename_slug,
    integrator_gate_latest_export_json,
    integrator_gate_latest_metrics_table_rows,
    integrator_gate_latest_operator_metrics,
    integrator_gate_latest_operator_metrics_caption,
    integrator_gate_latest_operator_metrics_export_json,
    integrator_gate_latest_operator_metrics_table_rows_csv,
    integrator_gate_latest_score_margin_caption,
    integrator_gate_latest_summary_rows_csv,
    integrator_gate_latest_tag_overlap_caption,
    integrator_gate_summary_rows,
)
from hermes_console.integrator_threshold_explainer import (
    integrator_threshold_explainer_export_json,
    integrator_threshold_explainer_operator_metrics,
    integrator_threshold_explainer_operator_metrics_caption,
    integrator_threshold_explainer_operator_metrics_export_filename_slug,
    integrator_threshold_explainer_operator_metrics_export_json,
    integrator_threshold_explainer_operator_metrics_table_rows,
    integrator_threshold_explainer_operator_metrics_table_rows_csv,
    integrator_threshold_explainer_payload,
    integrator_threshold_explainer_table_rows,
    integrator_threshold_explainer_table_rows_csv,
    integrator_threshold_export_filename_slug,
    integrator_threshold_gate_emission_caption,
    integrator_threshold_min_score_agreement_caption,
    integrator_threshold_paste_parse_caption,
    integrator_threshold_project_tags_caption,
    integrator_threshold_thresholds_yaml_version_caption,
)
from hermes_console.integrator_workflow_apply import (
    ALLOW_WORKFLOW_YAML_WRITE_ENV,
    apply_agent_evaluator_yaml,
    apply_full_workflow_yaml,
    apply_integrator_gate_yaml,
    prepare_agent_evaluator_apply,
    prepare_full_workflow_apply,
    prepare_integrator_gate_apply,
    workflow_yaml_write_enabled,
)
from hermes_console.integrator_workflow_preview import (
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
from hermes_console.persona_assignment_display import (
    persona_assignment_caption,
    persona_assignment_from_timeline,
    persona_assignment_summary_rows,
    persona_assignment_timeline_export_json,
    persona_assignment_timeline_table_rows_csv,
)
from hermes_console.persona_catalog import (
    critique_pairings_critic_counts_all_export_json,
    critique_pairings_critic_counts_all_table_rows,
    critique_pairings_critic_counts_all_table_rows_csv,
    critique_pairings_critic_counts_export_json,
    critique_pairings_critic_counts_table_rows,
    critique_pairings_critic_counts_table_rows_csv,
    critique_pairings_export_filename_slug,
    critique_pairings_operator_summary,
    critique_pairings_operator_summary_export_json,
    critique_pairings_operator_summary_operator_metrics,
    critique_pairings_operator_summary_operator_metrics_caption,
    critique_pairings_operator_summary_operator_metrics_export_filename_slug,
    critique_pairings_operator_summary_operator_metrics_export_json,
    critique_pairings_operator_summary_operator_metrics_table_rows,
    critique_pairings_operator_summary_operator_metrics_table_rows_csv,
    critique_pairings_producer_keys_all_export_json,
    critique_pairings_producer_keys_all_table_rows,
    critique_pairings_producer_keys_all_table_rows_csv,
    critique_pairings_producer_keys_export_json,
    critique_pairings_producer_keys_table_rows,
    critique_pairings_producer_keys_table_rows_csv,
    filter_persona_catalog_flat_rows,
    load_persona_shelves_catalog,
    persona_catalog_allowed_tool_filter_caption,
    persona_catalog_critique_pairings_total_caption,
    persona_catalog_display_name_duplicates_operator_caption,
    persona_catalog_display_name_length_caption,
    persona_catalog_distinct_allowed_tools,
    persona_catalog_empty_id_operator_caption,
    persona_catalog_flat_export_filename_slug,
    persona_catalog_flat_rows,
    persona_catalog_flat_rows_csv,
    persona_catalog_flat_rows_export_json,
    persona_catalog_operator_summary,
    persona_catalog_operator_summary_export_json,
    persona_catalog_operator_summary_operator_metrics,
    persona_catalog_operator_summary_operator_metrics_caption,
    persona_catalog_operator_summary_operator_metrics_export_filename_slug,
    persona_catalog_operator_summary_operator_metrics_export_json,
    persona_catalog_operator_summary_operator_metrics_table_rows,
    persona_catalog_operator_summary_operator_metrics_table_rows_csv,
    persona_catalog_operator_summary_table_rows_csv,
    persona_catalog_persona_id_duplicates_operator_caption,
    persona_catalog_persona_id_length_caption,
    persona_catalog_probation_breakdown_caption,
    persona_catalog_taxonomy_scope_frozen_caption,
    persona_catalog_without_capability_profile_caption,
    persona_catalog_without_instructions_caption,
    persona_probation_other_by_shelf_export_json,
    persona_probation_other_by_shelf_table_rows_csv,
    persona_probation_other_examples_by_shelf_table_rows,
    persona_probation_other_export_filename_slug,
)
from hermes_console.persona_editor import (
    build_patch_request,
    diff_summary,
    find_persona_in_catalog,
    parse_write_response,
    persona_editor_diff_summary_caption,
    persona_editor_display_name_draft_caption,
    persona_editor_expected_version_caption,
    persona_editor_instructions_metrics_caption,
    persona_editor_multiline_field_metrics_caption,
    persona_editor_probation_status_caption,
    persona_editor_probation_status_draft_caption,
    persona_editor_selected_shelf_caption,
    persona_editor_validation_blocking_caption,
    persona_editor_validation_issues,
    persona_editor_validation_table_rows,
    persona_list_field_line_counts_caption,
)
from hermes_console.preflight_cross_run_display import (
    fetch_preflight_history,
    preflight_cross_run_checks_passed_coverage_caption,
    preflight_cross_run_latency_sample_count_coverage_caption,
    preflight_cross_run_multisample_caption,
    preflight_cross_run_operator_depth_caption,
    preflight_cross_run_operator_metrics,
    preflight_cross_run_operator_metrics_caption,
    preflight_cross_run_operator_metrics_export_filename_slug,
    preflight_cross_run_operator_metrics_export_json,
    preflight_cross_run_operator_metrics_table_rows,
    preflight_cross_run_operator_metrics_table_rows_csv,
    preflight_cross_run_p95_spread_caption,
    preflight_cross_run_trend_export_filename_slug,
    preflight_cross_run_trend_export_json,
    preflight_cross_run_trend_rows,
    preflight_cross_run_trend_rows_csv,
    preflight_cross_run_trend_summary,
    preflight_cross_run_validated_model_id_coverage_caption,
    preflight_history_metrics_export_download_filename_slug,
    preflight_history_metrics_export_download_json,
    preflight_history_response_limit,
    preflight_history_response_metrics_export_caption,
    preflight_history_response_sli_caption,
    preflight_pairs_from_history_response,
)
from hermes_console.preflight_history_display import (
    preflight_history_checks_passed_caption,
    preflight_history_context_tokens_caption,
    preflight_history_event_id_caption,
    preflight_history_export_filename_slug,
    preflight_history_export_json,
    preflight_history_from_timeline,
    preflight_history_histogram_mode_caption,
    preflight_history_histogram_payload,
    preflight_history_latency_samples_table_rows,
    preflight_history_operator_metrics,
    preflight_history_operator_metrics_caption,
    preflight_history_operator_metrics_export_json,
    preflight_history_operator_metrics_table_rows,
    preflight_history_operator_metrics_table_rows_csv,
    preflight_history_p95_latency_caption,
    preflight_history_p95_source_caption,
    preflight_history_provider_caption,
    preflight_history_sample_count_caption,
    preflight_history_samples_table_caption,
    preflight_history_summary_rows,
    preflight_history_summary_rows_csv,
    preflight_history_validated_model_caption,
)
from hermes_console.prune_status_display import (
    load_prune_status,
    prune_scraper_artifact_prune_workflow_caption,
    prune_status_age_since_wrote_at_caption,
    prune_status_base_dir_caption,
    prune_status_dry_run_caption,
    prune_status_export_json,
    prune_status_freshness_caption,
    prune_status_max_age_days_caption,
    prune_status_object_store_prune_caption,
    prune_status_operator_metrics,
    prune_status_operator_metrics_caption,
    prune_status_operator_metrics_export_filename_slug,
    prune_status_operator_metrics_export_json,
    prune_status_operator_metrics_table_rows,
    prune_status_operator_metrics_table_rows_csv,
    prune_status_pattern_filter_caption,
    prune_status_pruned_outcome_caption,
    prune_status_retention_alert_caption,
    prune_status_retention_execution_caption,
    prune_status_retention_policy_caption,
    prune_status_schema_version_caption,
    prune_status_summary_rows,
    prune_status_summary_rows_csv,
    prune_status_wrote_at_caption,
)
from hermes_console.run_escalated_display import (
    run_escalated_actor_without_notes_caption,
    run_escalated_delta_export_filename_slug,
    run_escalated_delta_export_json,
    run_escalated_delta_from_timeline,
    run_escalated_delta_operator_metrics,
    run_escalated_delta_operator_metrics_caption,
    run_escalated_delta_operator_metrics_export_json,
    run_escalated_delta_operator_metrics_table_rows,
    run_escalated_delta_operator_metrics_table_rows_csv,
    run_escalated_delta_summary_rows,
    run_escalated_delta_table_rows_csv,
    run_escalated_delta_transition_caption,
    run_escalated_event_id_caption,
    run_escalated_export_filename_slug,
    run_escalated_export_json,
    run_escalated_from_timeline,
    run_escalated_history_distinct_actors_caption,
    run_escalated_history_entry_count_caption,
    run_escalated_history_export_filename_slug,
    run_escalated_history_export_json,
    run_escalated_history_from_timeline,
    run_escalated_history_operator_metrics,
    run_escalated_history_operator_metrics_caption,
    run_escalated_history_operator_metrics_export_json,
    run_escalated_history_operator_metrics_table_rows,
    run_escalated_history_operator_metrics_table_rows_csv,
    run_escalated_history_table_rows,
    run_escalated_history_table_rows_csv,
    run_escalated_notes_preview_caption,
    run_escalated_occurred_at_caption,
    run_escalated_operator_metrics,
    run_escalated_operator_metrics_caption,
    run_escalated_operator_metrics_export_json,
    run_escalated_operator_metrics_table_rows,
    run_escalated_operator_metrics_table_rows_csv,
    run_escalated_policy_cross_ref_caption,
    run_escalated_reason_summary_caption,
    run_escalated_summary_rows,
    run_escalated_summary_rows_csv,
)
from hermes_console.run_list_pagination_display import (
    run_detail_summary_export_filename_slug,
    run_detail_summary_export_json,
    run_detail_summary_operator_metrics,
    run_detail_summary_operator_metrics_caption,
    run_detail_summary_operator_metrics_export_filename_slug,
    run_detail_summary_operator_metrics_export_json,
    run_detail_summary_operator_metrics_table_rows,
    run_detail_summary_operator_metrics_table_rows_csv,
    run_list_active_query_params_caption,
    run_list_created_range_caption,
    run_list_has_escalation_filter_caption,
    run_list_has_more_true_caption,
    run_list_include_summary_filter_caption,
    run_list_keyset_next_page_caption,
    run_list_next_cursor_length_caption,
    run_list_order_desc_caption,
    run_list_page_vs_total_caption,
    run_list_pagination_link_caption,
    run_list_response_pagination_caption,
    run_list_status_filter_caption,
    run_list_summaries_sparse_caption,
    run_list_workflow_profile_filter_caption,
    timeline_events_export_filename_slug,
    timeline_events_export_json,
    timeline_events_from_body,
    timeline_events_operator_metrics,
    timeline_events_operator_metrics_caption,
    timeline_events_operator_metrics_export_json,
    timeline_events_operator_metrics_table_rows,
    timeline_events_operator_metrics_table_rows_csv,
    timeline_events_table_rows,
    timeline_events_table_rows_csv,
)
from hermes_console.scraper_fetch_display import (
    scraper_fetch_artifacts_caption,
    scraper_fetch_failure_reason_caption,
    scraper_fetch_fetches_export_filename_slug,
    scraper_fetch_fetches_export_json,
    scraper_fetch_fetches_table_rows,
    scraper_fetch_fetches_table_rows_csv,
    scraper_fetch_from_timeline,
    scraper_fetch_operator_metrics,
    scraper_fetch_operator_metrics_caption,
    scraper_fetch_operator_metrics_export_json,
    scraper_fetch_operator_metrics_table_rows,
    scraper_fetch_operator_metrics_table_rows_csv,
    scraper_fetch_outcome_caption,
    scraper_fetch_summary_export_filename_slug,
    scraper_fetch_summary_export_json,
    scraper_fetch_summary_rows,
    scraper_fetch_summary_rows_csv,
)
from hermes_console.security_scan_metadata_workflow_explainer import (
    security_scan_metadata_effective_enabled_caption,
    security_scan_metadata_env_gate_caption,
    security_scan_metadata_explainer_export_json,
    security_scan_metadata_explainer_table_rows,
    security_scan_metadata_explainer_table_rows_csv,
    security_scan_metadata_export_filename_slug,
    security_scan_metadata_mapping_key_count_caption,
    security_scan_metadata_workflow_explainer_operator_metrics,
    security_scan_metadata_workflow_explainer_operator_metrics_caption,
    security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug,
    security_scan_metadata_workflow_explainer_operator_metrics_export_json,
    security_scan_metadata_workflow_explainer_operator_metrics_table_rows,
    security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv,
    security_scan_metadata_workflow_explainer_payload,
    security_scan_metadata_workflow_yaml_file_bytes_caption,
    security_scan_metadata_workflow_yaml_relpath_caption,
    security_scan_metadata_workflow_yaml_string_key_count_caption,
    security_scan_metadata_workflow_yaml_version_caption,
    security_scan_metadata_yaml_effective_mismatch_caption,
    security_scan_metadata_yaml_raw_type_caption,
)
from hermes_console.security_scan_on_verify_display import (
    security_scan_category_severity_caption,
    security_scan_finding_event_ids_caption,
    security_scan_history_entry_count_caption,
    security_scan_history_export_filename_slug,
    security_scan_history_export_json,
    security_scan_history_from_timeline,
    security_scan_history_operator_metrics,
    security_scan_history_operator_metrics_caption,
    security_scan_history_operator_metrics_export_json,
    security_scan_history_operator_metrics_table_rows,
    security_scan_history_operator_metrics_table_rows_csv,
    security_scan_history_severity_sample_caption,
    security_scan_history_table_rows,
    security_scan_history_table_rows_csv,
    security_scan_linter_exit_codes_caption,
    security_scan_linter_failed_linters_caption,
    security_scan_linter_missing_linters_caption,
    security_scan_linter_nonzero_caption,
    security_scan_linter_ok_linters_caption,
    security_scan_linter_operator_metrics,
    security_scan_linter_operator_metrics_caption,
    security_scan_linter_operator_metrics_export_json,
    security_scan_linter_operator_metrics_table_rows,
    security_scan_linter_operator_metrics_table_rows_csv,
    security_scan_linter_status_rows,
    security_scan_linter_status_summary_caption,
    security_scan_linter_worst_status_caption,
    security_scan_metadata_timeline_workflow_alignment_caption,
    security_scan_occurred_at_age_caption,
    security_scan_on_verify_from_timeline,
    security_scan_on_verify_latest_export_filename_slug,
    security_scan_on_verify_latest_export_json,
    security_scan_on_verify_latest_operator_metrics,
    security_scan_on_verify_latest_operator_metrics_caption,
    security_scan_on_verify_latest_operator_metrics_export_json,
    security_scan_on_verify_latest_operator_metrics_table_rows,
    security_scan_on_verify_latest_operator_metrics_table_rows_csv,
    security_scan_on_verify_latest_summary_rows_csv,
    security_scan_on_verify_summary_rows,
    security_scan_snippet_length_caption,
    security_scan_snippet_line_count_caption,
)
from hermes_console.self_refinement_display import (
    self_refinement_auto_promote_caption,
    self_refinement_description_length_caption,
    self_refinement_evaluation_caption,
    self_refinement_from_timeline,
    self_refinement_iteration_caption,
    self_refinement_latest_export_filename_slug,
    self_refinement_latest_export_json,
    self_refinement_latest_summary_rows_csv,
    self_refinement_llm_critique_stage_caption,
    self_refinement_marker_avg_interval_caption,
    self_refinement_marker_first_last_caption,
    self_refinement_marker_history_entry_count_caption,
    self_refinement_marker_history_export_filename_slug,
    self_refinement_marker_history_export_json,
    self_refinement_marker_history_from_timeline,
    self_refinement_marker_history_operator_metrics,
    self_refinement_marker_history_operator_metrics_caption,
    self_refinement_marker_history_operator_metrics_export_json,
    self_refinement_marker_history_operator_metrics_table_rows,
    self_refinement_marker_history_operator_metrics_table_rows_csv,
    self_refinement_marker_history_table_rows,
    self_refinement_marker_history_table_rows_csv,
    self_refinement_marker_window_caption,
    self_refinement_markers_per_minute_caption,
    self_refinement_phase_d_signal_caption,
    self_refinement_prior_gate_verdict_caption,
    self_refinement_policy_attempt_caption,
    self_refinement_session_caption,
    self_refinement_snapshot_from_compare_paste,
    self_refinement_stage_name_caption,
    self_refinement_summary_rows,
    self_refinement_timeline_metrics_table_rows,
    self_refinement_timeline_operator_metrics,
    self_refinement_timeline_operator_metrics_export_json,
    self_refinement_timeline_operator_metrics_table_rows_csv,
    self_refinement_timeline_policy_version_caption,
    self_refinement_ungated_loop_caption,
    self_refinement_version_attempt_caption,
)
from hermes_console.self_refinement_workflow_explainer import (
    self_refinement_explainer_export_json,
    self_refinement_explainer_table_rows,
    self_refinement_explainer_table_rows_csv,
    self_refinement_export_filename_slug,
    self_refinement_marker_merge_compare_export_filename_slug,
    self_refinement_marker_merge_compare_export_json,
    self_refinement_marker_merge_compare_snapshot,
    self_refinement_marker_merge_compare_table_rows_csv,
    self_refinement_marker_merge_vs_timeline_rows,
    self_refinement_merged_description_preview_caption,
    self_refinement_merged_version_caption,
    self_refinement_policy_yaml_disk_version_caption,
    self_refinement_policy_yaml_file_bytes_caption,
    self_refinement_ungated_loop_env_gate_caption,
    self_refinement_workflow_explainer_operator_metrics,
    self_refinement_workflow_explainer_operator_metrics_caption,
    self_refinement_workflow_explainer_operator_metrics_export_filename_slug,
    self_refinement_workflow_explainer_operator_metrics_export_json,
    self_refinement_workflow_explainer_operator_metrics_table_rows,
    self_refinement_workflow_explainer_operator_metrics_table_rows_csv,
    self_refinement_workflow_explainer_payload,
    self_refinement_workflow_yaml_raw_type_caption,
    self_refinement_would_emit_after_env_caption,
    self_refinement_would_emit_marker_caption,
)
from hermes_console.universal_critique_timeline_display import (
    universal_critique_fail_stage_rows_csv,
    universal_critique_from_timeline,
    universal_critique_snapshot_from_compare_paste,
    universal_critique_timeline_export_filename_slug,
    universal_critique_timeline_export_json,
    universal_critique_timeline_fail_count_caption,
    universal_critique_timeline_fail_stage_caption,
    universal_critique_timeline_fail_stage_rows,
    universal_critique_timeline_operator_metrics,
    universal_critique_timeline_operator_metrics_caption,
    universal_critique_timeline_operator_metrics_export_json,
    universal_critique_timeline_operator_metrics_table_rows,
    universal_critique_timeline_operator_metrics_table_rows_csv,
    universal_critique_timeline_stage_rows,
    universal_critique_timeline_stage_rows_csv,
)
from hermes_console.universal_critique_workflow_explainer import (
    universal_critique_default_enabled_caption,
    universal_critique_enabled_stages_caption,
    universal_critique_env_override_deltas,
    universal_critique_env_override_summary_caption,
    universal_critique_explainer_export_json,
    universal_critique_explainer_table_rows,
    universal_critique_explainer_table_rows_csv,
    universal_critique_export_filename_slug,
    universal_critique_workflow_explainer_operator_metrics,
    universal_critique_workflow_explainer_operator_metrics_caption,
    universal_critique_workflow_explainer_operator_metrics_export_filename_slug,
    universal_critique_workflow_explainer_operator_metrics_export_json,
    universal_critique_workflow_explainer_operator_metrics_table_rows,
    universal_critique_workflow_explainer_operator_metrics_table_rows_csv,
    universal_critique_workflow_explainer_payload,
    universal_critique_workflow_vs_timeline_rows,
    universal_critique_workflow_yaml_bytes_caption,
    universal_critique_workflow_yaml_relpath_caption,
    universal_critique_yaml_enabled_bucket_caption,
    universal_critique_yaml_present_caption,
    universal_critique_yaml_stage_keys_caption,
    universal_critique_yaml_top_level_enabled_false_count_caption,
    universal_critique_yaml_top_level_enabled_true_count_caption,
    universal_critique_yaml_top_level_list_child_count_caption,
    universal_critique_yaml_top_level_mapping_child_count_caption,
    universal_critique_yaml_top_level_nonempty_count_caption,
)

API_BASE = os.environ.get("HERMES_API_BASE", "http://127.0.0.1:8000/v1")


def _resolve_prune_status_path() -> Path | None:
    """Return ``HERMES_PRUNE_STATUS_PATH`` expanded to a ``Path``, or ``None`` when unset.

    Resolved per-render so operators can switch the env var without restarting the
    Streamlit server. Matches the script-side resolution in
    ``scripts/prune_scraper_artifacts.py``.
    """
    raw = os.environ.get("HERMES_PRUNE_STATUS_PATH", "").strip()
    return Path(raw).expanduser() if raw else None

_RUN_LIST_QP_KEYS = frozenset({
    "workflow_profile",
    "workflow_profile_prefix",
    "order",
    "include_summary",
    "has_escalation",
    "offset",
    "limit",
    "created_after",
    "created_before",
    "status",
    "cursor",
})

_SS_WF = "hermes_list_wf"
_SS_PFX = "hermes_list_pfx"
_SS_ORDER = "hermes_list_order"
_SS_ESC = "hermes_list_esc"
_SS_SUM = "hermes_include_summary"
_SS_CA = "hermes_list_created_after"
_SS_CB = "hermes_list_created_before"
_SS_OFF = "hermes_list_offset"
_SS_LIM = "hermes_list_limit"
_SS_ST = "hermes_list_status"
_SS_CUR = "hermes_list_cursor"
_LAST_LIST_ERR = "hermes_last_list_error"
_LAST_LIST_JSON = "hermes_last_list_json"
_PREFLIGHT_TREND_ERR = "hermes_preflight_trend_err"
_PREFLIGHT_TREND_HISTORY_BODY = "hermes_preflight_trend_history_body"
_PREFLIGHT_TREND_ROWS = "hermes_preflight_trend_rows"
_SS_DETAIL = "hermes_detail_run_id"
_DF_LIST_KEY = "hermes_run_list_df"
_DF_LIST_SEL_SIG = "hermes_run_list_df_sel_rows"
_SS_LIST_COLS = "hermes_list_visible_optional_cols"
_LIST_OPTIONAL_ORDER = (
    "status",
    "workflow_profile",
    "event_count",
    "findings_count",
    "has_escalation",
)


def _qp_get(name: str) -> str | None:
    raw = st.query_params.get(name)
    if raw is None:
        return None
    if isinstance(raw, list):
        s = (raw[0] if raw else "") or ""
    else:
        s = str(raw)
    s = s.strip()
    return s if s else None


def _run_list_qp_snapshot() -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for k in sorted(_RUN_LIST_QP_KEYS):
        v = _qp_get(k)
        if v is not None:
            pairs.append((k, v))
    return tuple(pairs)


def _run_list_reset_defaults() -> None:
    st.session_state[_SS_WF] = ""
    st.session_state[_SS_PFX] = ""
    st.session_state[_SS_ORDER] = "newest_first"
    st.session_state[_SS_ESC] = "(not set)"
    st.session_state[_SS_SUM] = False
    st.session_state[_SS_CA] = ""
    st.session_state[_SS_CB] = ""
    st.session_state[_SS_OFF] = 0
    st.session_state[_SS_LIM] = 50
    st.session_state[_SS_ST] = "(not set)"
    st.session_state[_SS_CUR] = ""
    st.session_state.pop(_LAST_LIST_JSON, None)
    st.session_state.pop(_SS_LIST_COLS, None)


def _run_list_ensure_defaults() -> None:
    defaults: dict[str, Any] = {
        _SS_WF: "",
        _SS_PFX: "",
        _SS_ORDER: "newest_first",
        _SS_ESC: "(not set)",
        _SS_SUM: False,
        _SS_CA: "",
        _SS_CB: "",
        _SS_OFF: 0,
        _SS_LIM: 50,
        _SS_ST: "(not set)",
        _SS_CUR: "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _run_list_qp_apply_to_session(warned: list[str]) -> None:
    snap = _run_list_qp_snapshot()
    prev = st.session_state.get("_hermes_run_list_qp_snap")
    if prev == snap:
        return
    if not snap:
        st.session_state["_hermes_run_list_qp_snap"] = snap
        if prev not in (None, ()):
            _run_list_reset_defaults()
        return
    st.session_state["_hermes_run_list_qp_snap"] = snap
    _run_list_reset_defaults()
    if (v := _qp_get("workflow_profile")) is not None:
        st.session_state[_SS_WF] = v
    if (v := _qp_get("workflow_profile_prefix")) is not None:
        st.session_state[_SS_PFX] = v
    if (v := _qp_get("order")) is not None:
        if v in ("newest_first", "oldest_first"):
            st.session_state[_SS_ORDER] = v
        else:
            warned.append(f"Ignored invalid order in URL: {v!r}")
    if st.query_params.get("include_summary") is not None:
        sv = (_qp_get("include_summary") or "").lower()
        st.session_state[_SS_SUM] = sv in ("1", "true", "yes", "on")
    if st.query_params.get("has_escalation") is not None:
        he = _qp_get("has_escalation") or ""
        if he in ("0", "1"):
            st.session_state[_SS_ESC] = he
        else:
            warned.append(f"Ignored invalid has_escalation in URL: {he!r}")
    if (v := _qp_get("created_after")) is not None:
        st.session_state[_SS_CA] = v
    if (v := _qp_get("created_before")) is not None:
        st.session_state[_SS_CB] = v
    if st.query_params.get("offset") is not None:
        raw = _qp_get("offset") or "0"
        try:
            st.session_state[_SS_OFF] = max(0, int(raw))
        except ValueError:
            warned.append("Ignored invalid offset in URL")
    if st.query_params.get("limit") is not None:
        raw = _qp_get("limit") or "50"
        try:
            st.session_state[_SS_LIM] = max(1, min(200, int(raw)))
        except ValueError:
            warned.append("Ignored invalid limit in URL")
    if (v := _qp_get("status")) is not None:
        if v in ("created", "running", "terminal"):
            st.session_state[_SS_ST] = v
        else:
            warned.append(f"Ignored invalid status in URL: {v!r}")
    if (v := _qp_get("cursor")) is not None:
        st.session_state[_SS_CUR] = v
        st.session_state[_SS_OFF] = 0


def _run_list_qp_push(params: dict[str, str | int]) -> None:
    for k in list(_RUN_LIST_QP_KEYS):
        try:
            del st.query_params[k]
        except KeyError:
            pass
    for k, v in params.items():
        if k not in _RUN_LIST_QP_KEYS:
            continue
        if k == "offset" and int(v) == 0:
            continue
        if k == "include_summary" and int(v) == 0:
            continue
        if k == "cursor" and not str(v).strip():
            continue
        st.query_params[str(k)] = str(v)


_LAST_LIST_PAGE = "hermes_last_list_page"
_LAST_BUNDLE_SEARCH_JSON = "hermes_last_bundle_search_json"
_LAST_PERSONA_CATALOG_JSON = "hermes_last_persona_catalog_json"
_LAST_INTEGRATOR_PREVIEW = "hermes_last_integrator_preview_json"
_LAST_INTEGRATOR_MERGE_DRY = "hermes_last_integrator_merge_dry_run"
_LAST_AGENT_EVALUATOR_MERGE_DRY = "hermes_last_agent_evaluator_merge_dry_run"
_LAST_FULL_WORKFLOW_MERGE_DRY = "hermes_last_full_workflow_merge_dry_run"


def _build_run_list_params() -> dict[str, str | int]:
    off = int(st.session_state[_SS_OFF])
    order_val = str(st.session_state[_SS_ORDER])
    lim_raw = int(st.session_state[_SS_LIM])
    inc = bool(st.session_state[_SS_SUM])
    wf = str(st.session_state[_SS_WF]).strip()
    pfx = str(st.session_state[_SS_PFX]).strip()
    esc = str(st.session_state[_SS_ESC])
    ca = str(st.session_state[_SS_CA]).strip()
    cb = str(st.session_state[_SS_CB]).strip()
    cur = str(st.session_state.get(_SS_CUR, "")).strip()
    params: dict[str, str | int] = {"order": order_val}
    if cur:
        params["cursor"] = cur
        params["offset"] = 0
    else:
        params["offset"] = off
    if inc:
        params["include_summary"] = 1
        params["limit"] = min(lim_raw, 20)
    else:
        params["limit"] = lim_raw
    if wf:
        params["workflow_profile"] = wf
    elif pfx:
        params["workflow_profile_prefix"] = pfx
    if esc == "0":
        params["has_escalation"] = 0
    elif esc == "1":
        params["has_escalation"] = 1
    if ca:
        params["created_after"] = ca
    if cb:
        params["created_before"] = cb
    stv = str(st.session_state[_SS_ST])
    if stv in ("created", "running", "terminal"):
        params["status"] = stv
    return params


def _store_list_snapshot(
    data: dict[str, Any],
    params: dict[str, str | int],
    *,
    link_header: str | None,
) -> None:
    run_ids = data.get("run_ids") or []
    total_raw = data.get("total")
    total_snap: int | None = None
    if isinstance(total_raw, int) and not isinstance(total_raw, bool):
        total_snap = total_raw
    st.session_state[_LAST_LIST_PAGE] = {
        "offset": int(data.get("offset", 0)),
        "has_more": bool(data.get("has_more", False)),
        "n_ids": len(run_ids),
        "params": dict(params),
        "next_cursor": data.get("next_cursor"),
        "total": total_snap,
        "link": (
            link_header.strip()
            if isinstance(link_header, str) and link_header.strip()
            else ""
        ),
    }


def _run_list_clear_query_params() -> None:
    for k in _RUN_LIST_QP_KEYS:
        if k in st.query_params:
            del st.query_params[k]
    st.session_state["_hermes_run_list_qp_snap"] = ()


def _run_list_payload_to_csv(data: dict[str, Any]) -> str:
    """Serialize last list payload to CSV (parity with compact dataframe columns)."""
    run_ids = data.get("run_ids") or []
    raw_sum = data.get("summaries")
    summaries: dict[str, Any] = raw_sum if isinstance(raw_sum, dict) else {}
    use_extra = any(
        isinstance(summaries.get(rid), dict) and summaries.get(rid)
        for rid in run_ids
    )
    buf = io.StringIO()
    if use_extra:
        fieldnames = (
            "run_id",
            "status",
            "workflow_profile",
            "event_count",
            "findings_count",
            "has_escalation",
        )
        w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for rid in run_ids:
            s = summaries.get(rid) if isinstance(summaries, dict) else {}
            row = {k: "" for k in fieldnames}
            row["run_id"] = str(rid)
            if isinstance(s, dict):
                for k in (
                    "status",
                    "workflow_profile",
                    "event_count",
                    "findings_count",
                    "has_escalation",
                ):
                    v = s.get(k)
                    if v is not None:
                        row[k] = str(v)
            w.writerow(row)
    else:
        w = csv.DictWriter(buf, fieldnames=["run_id"], extrasaction="ignore")
        w.writeheader()
        for rid in run_ids:
            w.writerow({"run_id": str(rid)})
    return buf.getvalue()


def _render_run_list(data: dict[str, Any], *, include_summary: bool) -> None:
    rows = data.get("run_ids") or []
    m1, m2, m3 = st.columns(3)
    tot = data.get("total")
    m1.metric("total (list)", tot if isinstance(tot, int) else "—")
    if "has_more" in data:
        m2.metric("has_more", "yes" if data.get("has_more") else "no")
    else:
        m2.metric("has_more", "—")
    m3.metric("run_ids returned", len(rows))
    _snap_page = st.session_state.get(_LAST_LIST_PAGE)
    _link_pr = False
    if isinstance(_snap_page, dict):
        _ln = _snap_page.get("link") or ""
        _link_pr = isinstance(_ln, str) and bool(_ln.strip())
    _list_pag_cap = run_list_response_pagination_caption(data, link_header_present=_link_pr)
    if _list_pag_cap:
        st.caption(_list_pag_cap)
    _list_link_cap = run_list_pagination_link_caption(link_header_present=_link_pr)
    if _list_link_cap:
        st.caption(_list_link_cap)
    _list_page_total_cap = run_list_page_vs_total_caption(data)
    if _list_page_total_cap:
        st.caption(_list_page_total_cap)
    _list_keyset_cap = run_list_keyset_next_page_caption(data)
    if _list_keyset_cap:
        st.caption(_list_keyset_cap)
    _list_nc_len_cap = run_list_next_cursor_length_caption(data)
    if _list_nc_len_cap:
        st.caption(_list_nc_len_cap)
    _list_sum_sparse = run_list_summaries_sparse_caption(data)
    if _list_sum_sparse:
        st.caption(_list_sum_sparse)
    qp = _build_run_list_params()
    _list_qp_cap = run_list_active_query_params_caption(qp)
    if _list_qp_cap:
        st.caption(_list_qp_cap)
    _list_date_cap = run_list_created_range_caption(qp)
    if _list_date_cap:
        st.caption(_list_date_cap)
    _list_status_cap = run_list_status_filter_caption(qp)
    if _list_status_cap:
        st.caption(_list_status_cap)
    _list_esc_cap = run_list_has_escalation_filter_caption(qp)
    if _list_esc_cap:
        st.caption(_list_esc_cap)
    _list_wf_cap = run_list_workflow_profile_filter_caption(qp)
    if _list_wf_cap:
        st.caption(_list_wf_cap)
    _list_inc_sum_cap = run_list_include_summary_filter_caption(qp)
    if _list_inc_sum_cap:
        st.caption(_list_inc_sum_cap)
    _list_order_cap = run_list_order_desc_caption(qp)
    if _list_order_cap:
        st.caption(_list_order_cap)
    _list_has_more_cap = run_list_has_more_true_caption(data)
    if _list_has_more_cap:
        st.caption(_list_has_more_cap)
    q = urlencode(sorted((str(k), str(v)) for k, v in qp.items()))
    list_url = f"{API_BASE}/runs?{q}" if q else f"{API_BASE}/runs"
    st.caption("Shareable GET /v1/runs URL (matches current filters)")
    st.code(list_url, language=None)
    with st.expander("Raw list JSON", expanded=False):
        st.json(data)
    if not rows:
        st.info("No runs match the current filters (or the list is empty).")
    summaries = data.get("summaries") or {}
    if rows:
        table: list[dict[str, object]] = []
        for rid in rows:
            s = summaries.get(rid) if isinstance(summaries, dict) else {}
            row: dict[str, object] = {"run_id": rid}
            if isinstance(s, dict):
                row.update(
                    {
                        "status": s.get("status"),
                        "workflow_profile": s.get("workflow_profile"),
                        "event_count": s.get("event_count"),
                        "findings_count": s.get("findings_count"),
                        "has_escalation": s.get("has_escalation"),
                    },
                )
            table.append(row)
        optional_present = [
            k for k in _LIST_OPTIONAL_ORDER if any(k in r for r in table)
        ]
        disp: list[dict[str, object]] = table
        if optional_present:
            if _SS_LIST_COLS not in st.session_state:
                st.session_state[_SS_LIST_COLS] = optional_present.copy()
            st.multiselect(
                "Columns in compact list (run_id always shown)",
                options=optional_present,
                key=_SS_LIST_COLS,
            )
            _picked_raw = st.session_state.get(_SS_LIST_COLS)
            if not isinstance(_picked_raw, list):
                _picked = optional_present.copy()
            else:
                _picked = [c for c in _picked_raw if c in optional_present]
            disp = []
            for row in table:
                out: dict[str, object] = {"run_id": row["run_id"]}
                for k in _picked:
                    out[k] = row.get(k)
                disp.append(out)
        st.caption(
            "Compact run list (full payload in **Raw list JSON** expander). "
            "Select a row to fill **Run ID (detail)** below.",
        )
        st.dataframe(
            disp,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=_DF_LIST_KEY,
        )
        _df_state = st.session_state.get(_DF_LIST_KEY)
        if isinstance(_df_state, dict):
            _sel = _df_state.get("selection")
            if isinstance(_sel, dict):
                _row_ixs = _sel.get("rows")
                if isinstance(_row_ixs, list):
                    _ixs: list[int] = []
                    for x in _row_ixs:
                        if isinstance(x, int) and not isinstance(x, bool):
                            _ixs.append(x)
                    _cur_rows = tuple(_ixs)
                else:
                    _cur_rows = ()
            else:
                _cur_rows = ()
        else:
            _cur_rows = ()
        _prev_rows = st.session_state.get(_DF_LIST_SEL_SIG)
        if _cur_rows and _cur_rows != _prev_rows:
            _ix = _cur_rows[0]
            if 0 <= _ix < len(rows):
                st.session_state[_SS_DETAIL] = str(rows[_ix])
                st.session_state[_DF_LIST_SEL_SIG] = _cur_rows
        elif not _cur_rows:
            st.session_state[_DF_LIST_SEL_SIG] = ()
        if include_summary and isinstance(summaries, dict) and rows:
            chip_parts: list[str] = []
            for rid in rows[:16]:
                sb = summaries.get(rid)
                if isinstance(sb, dict):
                    st_label = sb.get("status", "?")
                    chip_parts.append(f"{rid[:8]}… → {st_label}")
            if chip_parts:
                st.caption("Status (from summaries): " + " · ".join(chip_parts))
    _blob = st.session_state.get(_LAST_LIST_JSON)
    if isinstance(_blob, dict):
        _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _jcol, _ccol = st.columns(2)
        with _jcol:
            st.download_button(
                label="Download run list JSON",
                data=json.dumps(_blob, indent=2).encode("utf-8"),
                file_name=f"hermes_runs_list_{_ts}.json",
                mime="application/json",
                key="hermes_dl_run_list_json",
            )
        with _ccol:
            st.download_button(
                label="Download run list CSV",
                data=_run_list_payload_to_csv(_blob).encode("utf-8"),
                file_name=f"hermes_runs_list_{_ts}.csv",
                mime="text/csv",
                key="hermes_dl_run_list_csv",
            )


def _run_list_fetch_and_display() -> bool:
    params = _build_run_list_params()
    try:
        r = httpx.get(f"{API_BASE}/runs", params=params, timeout=15.0)
        r.raise_for_status()
        _run_list_qp_push(params)
        data = r.json()
        _hdrs = r.headers
        _link_h = _hdrs.get("link") or _hdrs.get("Link")
        _link_arg = _link_h if isinstance(_link_h, str) else None
        _store_list_snapshot(data, params, link_header=_link_arg)
        st.session_state[_LAST_LIST_JSON] = data
        st.session_state.pop(_LAST_LIST_ERR, None)
        _render_run_list(data, include_summary=bool(st.session_state[_SS_SUM]))
    except httpx.HTTPError as exc:
        st.session_state.pop(_LAST_LIST_PAGE, None)
        st.session_state.pop(_LAST_LIST_JSON, None)
        st.session_state[_LAST_LIST_ERR] = str(exc)
        st.error(f"API error: {exc}")
        return False
    else:
        return True


st.set_page_config(page_title="Nimbusware Console", layout="wide")
st.title("Nimbusware operator console")
st.caption(streamlit_theme_defaults_caption(repo_root=Path(os.environ.get("HERMES_REPO_ROOT", "."))))
st.caption(streamlit_white_label_deferred_caption())

_repo_for_ui = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
with st.sidebar:
    from hermes_console.custom_agents_ui import render_custom_agents_sidebar

    render_custom_agents_sidebar(_repo_for_ui)

with st.container():
    from hermes_console.operator_chat import render_operator_chat

    render_operator_chat(repo_root=_repo_for_ui)
    st.divider()

_run_list_ensure_defaults()
if _SS_DETAIL not in st.session_state:
    st.session_state[_SS_DETAIL] = ""
_qp_warnings: list[str] = []
_run_list_qp_apply_to_session(_qp_warnings)
for _msg in _qp_warnings:
    st.warning(_msg)
if st.session_state.get(_LAST_LIST_ERR):
    st.warning(f"Last list fetch failed: {st.session_state[_LAST_LIST_ERR]}")
with st.expander("Bundle catalog search (local repo)", expanded=False):
    st.caption(
        "Read-only: same ``search_bundles`` helper as **GET /v1/bundles/search** over "
        "``configs/bundles/catalog.yaml``. Uses **HERMES_REPO_ROOT** (resolved); "
        "matches the API frozen repo root when both use the same env.",
    )
    _root = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
    st.caption(f"Effective repo root: `{_root}`")
    _bcat_sum = bundle_catalog_local_summary(_root)
    if _bcat_sum.get("has_catalog_yaml"):
        _bcat_sum_metrics = bundle_catalog_local_summary_operator_metrics(_bcat_sum)
        _bcat_sum_metrics_cap = bundle_catalog_local_summary_operator_metrics_caption(
            _bcat_sum_metrics,
        )
        if _bcat_sum_metrics_cap:
            st.caption(_bcat_sum_metrics_cap)
        _bcat_sum_metric_rows = bundle_catalog_local_summary_operator_metrics_table_rows(
            _bcat_sum_metrics,
        )
        if _bcat_sum_metric_rows:
            st.dataframe(_bcat_sum_metric_rows, use_container_width=True)
        _bcat_sum_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _bcat_sum_metrics_slug = (
            bundle_catalog_local_summary_operator_metrics_export_filename_slug()
        )
        _bcat_sum_metrics_json = bundle_catalog_local_summary_operator_metrics_export_json(
            _bcat_sum_metrics,
        )
        _bcat_sum_metrics_csv = bundle_catalog_local_summary_operator_metrics_table_rows_csv(
            _bcat_sum_metric_rows,
        )
        _bcat_sum_m_dl_json_col, _bcat_sum_m_dl_csv_col = st.columns(2)
        with _bcat_sum_m_dl_json_col:
            st.download_button(
                label="Download local catalog operator metrics JSON",
                data=_bcat_sum_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_bcat_sum_metrics_slug}_"
                    f"{bundle_catalog_local_export_filename_slug(_root)}_"
                    f"{_bcat_sum_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_catalog_local_summary_metrics_json",
            )
        with _bcat_sum_m_dl_csv_col:
            if _bcat_sum_metrics_csv:
                st.download_button(
                    label="Download local catalog operator metrics CSV",
                    data=_bcat_sum_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_bcat_sum_metrics_slug}_"
                        f"{bundle_catalog_local_export_filename_slug(_root)}_"
                        f"{_bcat_sum_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_catalog_local_summary_metrics_csv",
                )
        _bcat_sum_rows = bundle_catalog_local_summary_table_rows(_bcat_sum)
        if _bcat_sum_rows:
            _bcat_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _bcat_sum_slug = bundle_catalog_local_summary_export_filename_slug()
            _bcat_sum_json = bundle_catalog_local_summary_export_json(_bcat_sum)
            _bcat_sum_csv = bundle_catalog_local_summary_table_rows_csv(_bcat_sum_rows)
            _bcat_sum_dl_json_col, _bcat_sum_dl_csv_col = st.columns(2)
            with _bcat_sum_dl_json_col:
                st.download_button(
                    label="Download local catalog summary JSON",
                    data=_bcat_sum_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_bcat_sum_slug}_"
                        f"{bundle_catalog_local_export_filename_slug(_root)}_{_bcat_sum_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_local_summary_json",
                )
            with _bcat_sum_dl_csv_col:
                if _bcat_sum_csv:
                    st.download_button(
                        label="Download local catalog summary CSV",
                        data=_bcat_sum_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_sum_slug}_"
                            f"{bundle_catalog_local_export_filename_slug(_root)}_{_bcat_sum_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_local_summary_csv",
                    )
        st.caption(
            f"**Local catalog**: ``{_bcat_sum['catalog_yaml_relpath']}`` — "
            f"{_bcat_sum['bundle_count']} bundle(s), "
            f"{_bcat_sum['distinct_tag_count']} distinct tag(s).",
        )
        _bcat_distinct_cap = bundle_catalog_distinct_tag_count_caption(_root)
        if _bcat_distinct_cap:
            st.caption(_bcat_distinct_cap)
        _bcat_tags = bundle_catalog_distinct_tags_sample(_root)
        if _bcat_tags:
            st.caption(
                "Top tags: ``" + "``, ``".join(_bcat_tags) + "``",
            )
        _bcat_top_counts = bundle_catalog_top_tag_counts(_root)
        if _bcat_top_counts:
            _bcat_top_cap = bundle_catalog_top_tag_caption(_root)
            if _bcat_top_cap:
                st.caption(_bcat_top_cap)
            st.dataframe(
                _bcat_top_counts,
                use_container_width=True,
                hide_index=True,
            )
            _bcat_top_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _bcat_top_slug = bundle_catalog_local_export_filename_slug(_root)
            _bcat_top_json = bundle_catalog_top_tag_counts_export_json(_bcat_top_counts)
            _bcat_top_csv = bundle_catalog_top_tag_counts_table_rows_csv(_bcat_top_counts)
            _bcat_top_dl_json_col, _bcat_top_dl_csv_col = st.columns(2)
            with _bcat_top_dl_json_col:
                st.download_button(
                    label="Download top tag counts JSON",
                    data=_bcat_top_json.encode("utf-8"),
                    file_name=(
                        f"hermes_bundle_catalog_top_tags_{_bcat_top_slug}_{_bcat_top_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_top_tags_json",
                )
            with _bcat_top_dl_csv_col:
                if _bcat_top_csv:
                    st.download_button(
                        label="Download top tag counts CSV",
                        data=_bcat_top_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_bundle_catalog_top_tags_{_bcat_top_slug}_{_bcat_top_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_top_tags_csv",
                    )
        _bcat_total = int(_bcat_sum.get("bundle_count") or 0)
        if _bcat_total > 0:
            _bcat_count_cap = bundle_catalog_bundle_count_caption(_root)
            if _bcat_count_cap:
                st.caption(_bcat_count_cap)
            _bcat_without = bundle_catalog_bundles_without_tags_count(_root)
            st.caption(
                f"Bundles without tags: {_bcat_without} of {_bcat_total}.",
            )
            if _bcat_without > 0:
                _bcat_without_rollup = bundle_catalog_bundles_without_tags_rollup(_root)
                _bcat_without_tags_metrics = (
                    bundle_catalog_bundles_without_tags_rollup_operator_metrics(
                        _bcat_without_rollup,
                    )
                )
                _bcat_without_tags_metrics_cap = (
                    bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption(
                        _bcat_without_tags_metrics,
                    )
                )
                if _bcat_without_tags_metrics_cap:
                    st.caption(_bcat_without_tags_metrics_cap)
                _bcat_without_tags_metric_rows = (
                    bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows(
                        _bcat_without_tags_metrics,
                    )
                )
                if _bcat_without_tags_metric_rows:
                    st.dataframe(
                        _bcat_without_tags_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                _bcat_without_tags_metrics_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _bcat_without_tags_metrics_slug = (
                    bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_filename_slug()
                )
                _bcat_without_tags_metrics_json = (
                    bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_json(
                        _bcat_without_tags_metrics,
                    )
                )
                _bcat_without_tags_metrics_csv = (
                    bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows_csv(
                        _bcat_without_tags_metric_rows,
                    )
                )
                _bcat_without_tags_m_dl_json_col, _bcat_without_tags_m_dl_csv_col = (
                    st.columns(2)
                )
                with _bcat_without_tags_m_dl_json_col:
                    st.download_button(
                        label="Download bundles without tags rollup operator metrics JSON",
                        data=_bcat_without_tags_metrics_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_without_tags_metrics_slug}_"
                            f"{_bcat_without_tags_metrics_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_metrics_json",
                    )
                with _bcat_without_tags_m_dl_csv_col:
                    if _bcat_without_tags_metrics_csv:
                        st.download_button(
                            label="Download bundles without tags rollup operator metrics CSV",
                            data=_bcat_without_tags_metrics_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_bcat_without_tags_metrics_slug}_"
                                f"{_bcat_without_tags_metrics_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_metrics_csv",
                        )
                _bcat_without_rows = bundle_catalog_bundles_without_tags_rollup_table_rows(
                    _bcat_without_rollup,
                )
                if _bcat_without_rows:
                    _bcat_without_ts = datetime.now(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ",
                    )
                    _bcat_without_slug = (
                        bundle_catalog_bundles_without_tags_rollup_export_filename_slug()
                    )
                    _bcat_without_repo_slug = bundle_catalog_local_export_filename_slug(
                        _root,
                    )
                    _bcat_without_json = bundle_catalog_bundles_without_tags_rollup_export_json(
                        _bcat_without_rollup,
                    )
                    _bcat_without_csv = (
                        bundle_catalog_bundles_without_tags_rollup_table_rows_csv(
                            _bcat_without_rows,
                        )
                    )
                    _bcat_without_dl_json_col, _bcat_without_dl_csv_col = st.columns(2)
                    with _bcat_without_dl_json_col:
                        st.download_button(
                            label="Download bundles without tags rollup JSON",
                            data=_bcat_without_json.encode("utf-8"),
                            file_name=(
                                f"hermes_{_bcat_without_slug}_"
                                f"{_bcat_without_repo_slug}_{_bcat_without_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_json",
                        )
                    with _bcat_without_dl_csv_col:
                        if _bcat_without_csv:
                            st.download_button(
                                label="Download bundles without tags rollup CSV",
                                data=_bcat_without_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_{_bcat_without_slug}_"
                                    f"{_bcat_without_repo_slug}_{_bcat_without_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_csv",
                            )
            _bcat_without_id = bundle_catalog_bundles_without_id_count(_root)
            _bcat_without_id_cap = bundle_catalog_bundles_without_id_caption(_root)
            if _bcat_without_id_cap:
                st.caption(_bcat_without_id_cap)
            if _bcat_without_id > 0:
                _bcat_without_id_rollup = bundle_catalog_bundles_without_id_rollup(_root)
                _bcat_without_id_metrics = (
                    bundle_catalog_bundles_without_id_rollup_operator_metrics(
                        _bcat_without_id_rollup,
                    )
                )
                _bcat_without_id_metrics_cap = (
                    bundle_catalog_bundles_without_id_rollup_operator_metrics_caption(
                        _bcat_without_id_metrics,
                    )
                )
                if _bcat_without_id_metrics_cap:
                    st.caption(_bcat_without_id_metrics_cap)
                _bcat_without_id_metric_rows = (
                    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows(
                        _bcat_without_id_metrics,
                    )
                )
                if _bcat_without_id_metric_rows:
                    st.dataframe(
                        _bcat_without_id_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                _bcat_without_id_metrics_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _bcat_without_id_metrics_slug = (
                    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug()
                )
                _bcat_without_id_metrics_json = (
                    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json(
                        _bcat_without_id_metrics,
                    )
                )
                _bcat_without_id_metrics_csv = (
                    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv(
                        _bcat_without_id_metric_rows,
                    )
                )
                _bcat_without_id_m_dl_json_col, _bcat_without_id_m_dl_csv_col = st.columns(2)
                with _bcat_without_id_m_dl_json_col:
                    st.download_button(
                        label="Download bundles without id rollup operator metrics JSON",
                        data=_bcat_without_id_metrics_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_without_id_metrics_slug}_"
                            f"{_bcat_without_id_metrics_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_catalog_bundles_without_id_rollup_metrics_json",
                    )
                with _bcat_without_id_m_dl_csv_col:
                    if _bcat_without_id_metrics_csv:
                        st.download_button(
                            label="Download bundles without id rollup operator metrics CSV",
                            data=_bcat_without_id_metrics_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_bcat_without_id_metrics_slug}_"
                                f"{_bcat_without_id_metrics_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_catalog_bundles_without_id_rollup_metrics_csv",
                        )
                _bcat_without_id_rows = bundle_catalog_bundles_without_id_rollup_table_rows(
                    _bcat_without_id_rollup,
                )
                if _bcat_without_id_rows:
                    _bcat_without_id_ts = datetime.now(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ",
                    )
                    _bcat_without_id_slug = (
                        bundle_catalog_bundles_without_id_rollup_export_filename_slug()
                    )
                    _bcat_without_id_repo_slug = bundle_catalog_local_export_filename_slug(
                        _root,
                    )
                    _bcat_without_id_json = bundle_catalog_bundles_without_id_rollup_export_json(
                        _bcat_without_id_rollup,
                    )
                    _bcat_without_id_csv = (
                        bundle_catalog_bundles_without_id_rollup_table_rows_csv(
                            _bcat_without_id_rows,
                        )
                    )
                    _bcat_without_id_dl_json_col, _bcat_without_id_dl_csv_col = st.columns(2)
                    with _bcat_without_id_dl_json_col:
                        st.download_button(
                            label="Download bundles without id rollup JSON",
                            data=_bcat_without_id_json.encode("utf-8"),
                            file_name=(
                                f"hermes_{_bcat_without_id_slug}_"
                                f"{_bcat_without_id_repo_slug}_{_bcat_without_id_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_bundle_catalog_bundles_without_id_rollup_json",
                        )
                    with _bcat_without_id_dl_csv_col:
                        if _bcat_without_id_csv:
                            st.download_button(
                                label="Download bundles without id rollup CSV",
                                data=_bcat_without_id_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_{_bcat_without_id_slug}_"
                                    f"{_bcat_without_id_repo_slug}_{_bcat_without_id_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_bundle_catalog_bundles_without_id_rollup_csv",
                            )
            _bcat_without_tags_cap = bundle_catalog_bundles_without_tags_caption(_root)
            if _bcat_without_tags_cap:
                st.caption(_bcat_without_tags_cap)
        _bcat_ids = bundle_catalog_bundle_ids_sample(_root)
        if _bcat_ids:
            st.caption(
                "Bundle ids: ``" + "``, ``".join(_bcat_ids) + "``",
            )
        if _bcat_total > 0:
            _loc_bundles = bundle_catalog_local_bundles(_root)
            _loc_rows = bundle_catalog_local_bundles_table_rows(_loc_bundles)
            if _loc_rows:
                _loc_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _loc_slug = bundle_catalog_local_export_filename_slug(_root)
                _loc_json = bundle_catalog_local_bundles_export_json(_loc_bundles)
                _loc_csv = bundle_catalog_local_bundles_table_rows_csv(_loc_rows)
                _loc_dl_json_col, _loc_dl_csv_col = st.columns(2)
                with _loc_dl_json_col:
                    st.download_button(
                        label="Download local catalog bundles JSON",
                        data=_loc_json.encode("utf-8"),
                        file_name=(
                            f"hermes_bundle_catalog_local_{_loc_slug}_{_loc_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_catalog_local_json",
                    )
                with _loc_dl_csv_col:
                    if _loc_csv:
                        st.download_button(
                            label="Download local catalog bundles CSV",
                            data=_loc_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_bundle_catalog_local_{_loc_slug}_{_loc_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_catalog_local_csv",
                        )
    else:
        st.caption(
            "**Local catalog**: ``configs/bundles/catalog.yaml`` not found under repo root "
            "(search will return zero hits until it exists).",
        )
    with st.expander("FAISS index readiness (paths & catalog freshness)", expanded=False):
        st.caption(
            "File presence matches **GET /v1/bundles/search** / ``bundle_faiss_index_ready``. "
            "When **stale** is true, ``catalog.yaml`` is newer than both index files on disk — "
            "re-run the build script after catalog edits. "
            + bundle_faiss_index_workflow_caption_note(),
        )
        _faiss = bundle_faiss_index_status(_root)
        _faiss_sum = bundle_faiss_readiness_summary(_root)
        _faiss_cat_ver_cap = bundle_faiss_catalog_yaml_version_caption(_root)
        if _faiss_cat_ver_cap:
            st.caption(_faiss_cat_ver_cap)
        _faiss_bucket_cap = bundle_faiss_readiness_code_caption(_root)
        if _faiss_bucket_cap:
            st.caption(_faiss_bucket_cap)
        _faiss_headline_cap = bundle_faiss_readiness_headline_caption(_root)
        if _faiss_headline_cap:
            st.caption(_faiss_headline_cap)
        _faiss_missing_cap = bundle_faiss_readiness_missing_caption(_root)
        if _faiss_missing_cap:
            st.caption(_faiss_missing_cap)
        _faiss_missing_rows = bundle_faiss_readiness_missing_paths_table_rows(_faiss_sum)
        if _faiss_missing_rows:
            _faiss_missing_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _faiss_missing_slug = bundle_faiss_readiness_export_filename_slug(_root)
            _faiss_missing_json = bundle_faiss_readiness_missing_paths_export_json(
                _faiss_missing_rows,
            )
            _faiss_missing_csv = bundle_faiss_readiness_missing_paths_table_rows_csv(
                _faiss_missing_rows,
            )
            _faiss_missing_dl_json_col, _faiss_missing_dl_csv_col = st.columns(2)
            with _faiss_missing_dl_json_col:
                st.download_button(
                    label="Download FAISS missing index paths JSON",
                    data=_faiss_missing_json.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_missing_paths_"
                        f"{_faiss_missing_slug}_{_faiss_missing_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_faiss_missing_paths_json",
                )
            with _faiss_missing_dl_csv_col:
                if _faiss_missing_csv:
                    st.download_button(
                        label="Download FAISS missing index paths CSV",
                        data=_faiss_missing_csv.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_missing_paths_"
                            f"{_faiss_missing_slug}_{_faiss_missing_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_faiss_missing_paths_csv",
                    )
        _faiss_stale_cap = bundle_faiss_index_stale_caption(_root)
        if _faiss_stale_cap:
            st.caption(_faiss_stale_cap)
        _faiss_parity_cap = bundle_faiss_catalog_order_count_parity_caption(_root)
        if _faiss_parity_cap:
            st.caption(_faiss_parity_cap)
        _faiss_id_set_cap = bundle_faiss_catalog_order_id_set_mismatch_caption(_root)
        if _faiss_id_set_cap:
            st.caption(_faiss_id_set_cap)
            _faiss_mismatch_dd = bundle_faiss_index_operator_drilldown(_root)
            _faiss_mismatch_rows = bundle_faiss_id_set_mismatch_table_rows(
                _faiss_mismatch_dd,
            )
            if _faiss_mismatch_rows:
                _faiss_mismatch_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _faiss_mismatch_slug = bundle_faiss_operator_drilldown_export_filename_slug(
                    _root,
                )
                _faiss_mismatch_json = bundle_faiss_id_set_mismatch_export_json(
                    _faiss_mismatch_rows,
                )
                _faiss_mismatch_csv = bundle_faiss_id_set_mismatch_table_rows_csv(
                    _faiss_mismatch_rows,
                )
                _faiss_mismatch_dl_json_col, _faiss_mismatch_dl_csv_col = st.columns(2)
                with _faiss_mismatch_dl_json_col:
                    st.download_button(
                        label="Download FAISS id-set mismatch JSON",
                        data=_faiss_mismatch_json.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_id_set_mismatch_"
                            f"{_faiss_mismatch_slug}_{_faiss_mismatch_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_faiss_id_set_mismatch_json",
                    )
                with _faiss_mismatch_dl_csv_col:
                    if _faiss_mismatch_csv:
                        st.download_button(
                            label="Download FAISS id-set mismatch CSV",
                            data=_faiss_mismatch_csv.encode("utf-8"),
                            file_name=(
                                "hermes_bundle_faiss_id_set_mismatch_"
                                f"{_faiss_mismatch_slug}_{_faiss_mismatch_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_faiss_id_set_mismatch_csv",
                        )
        _faiss_dup_cap = bundle_faiss_bundle_order_duplicate_ids_caption(_root)
        if _faiss_dup_cap:
            st.caption(_faiss_dup_cap)
            _faiss_dup_dd = bundle_faiss_index_operator_drilldown(_root)
            _faiss_dup_rows = bundle_faiss_duplicate_id_table_rows(_faiss_dup_dd)
            if _faiss_dup_rows:
                _faiss_dup_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _faiss_dup_slug = bundle_faiss_operator_drilldown_export_filename_slug(
                    _root,
                )
                _faiss_dup_json = bundle_faiss_duplicate_id_export_json(_faiss_dup_rows)
                _faiss_dup_csv = bundle_faiss_duplicate_id_table_rows_csv(_faiss_dup_rows)
                _faiss_dup_dl_json_col, _faiss_dup_dl_csv_col = st.columns(2)
                with _faiss_dup_dl_json_col:
                    st.download_button(
                        label="Download FAISS duplicate bundle ids JSON",
                        data=_faiss_dup_json.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_duplicate_ids_"
                            f"{_faiss_dup_slug}_{_faiss_dup_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_faiss_duplicate_ids_json",
                    )
                with _faiss_dup_dl_csv_col:
                    if _faiss_dup_csv:
                        st.download_button(
                            label="Download FAISS duplicate bundle ids CSV",
                            data=_faiss_dup_csv.encode("utf-8"),
                            file_name=(
                                "hermes_bundle_faiss_duplicate_ids_"
                                f"{_faiss_dup_slug}_{_faiss_dup_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_faiss_duplicate_ids_csv",
                        )
        _faiss_mtime_cap = bundle_faiss_catalog_index_mtime_delta_caption(_root)
        if _faiss_mtime_cap:
            st.caption(_faiss_mtime_cap)
        _faiss_idx_n_cap = bundle_faiss_index_dir_file_count_caption(_root)
        if _faiss_idx_n_cap:
            st.caption(_faiss_idx_n_cap)
        _faiss_idx_sub_cap = bundle_faiss_index_dir_subdirectory_count_caption(_root)
        if _faiss_idx_sub_cap:
            st.caption(_faiss_idx_sub_cap)
        _faiss_idx_list_trunc_cap = bundle_faiss_index_dir_listing_truncated_caption(_root)
        if _faiss_idx_list_trunc_cap:
            st.caption(_faiss_idx_list_trunc_cap)
        _faiss_large_cap = bundle_faiss_index_large_file_caption(_root)
        if _faiss_large_cap:
            st.caption(_faiss_large_cap)
        _faiss_bo_bytes_cap = bundle_faiss_bundle_order_json_file_bytes_caption(_root)
        if _faiss_bo_bytes_cap:
            st.caption(_faiss_bo_bytes_cap)
        st.caption(f"**{_faiss_sum['headline']}** — {_faiss_sum['detail']}")
        if _faiss_sum.get("missing"):
            st.caption("Missing paths: ``" + "``, ``".join(_faiss_sum["missing"]) + "``")
        if _faiss["ready"]:
            st.caption(
                "FAISS bundle index: **present** under ``configs/bundles/index/`` "
                "(``faiss.index`` + ``bundle_order.json``). Search uses vector top-k when "
                "both files exist and ``faiss`` is installed (same as ``BundleCatalog.search``). "
                + bundle_faiss_index_workflow_caption_note(),
            )
            if _faiss.get("stale") is True:
                st.warning(
                    "Index may be **out of date** (catalog mtime newer than index files). "
                    "Rebuild from repo root (see command block below or **Poetry optional "
                    "groups and FAISS** in ``PLAN_GAP.md``). CI smoke: ``"
                    f"{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``.",
                )
                st.code(bundle_faiss_build_command_snippet_explicit(_root), language="bash")
                with st.expander("Windows: rebuild (copy-paste)", expanded=False):
                    st.code(
                        bundle_faiss_build_powershell_snippet_explicit(_root),
                        language="powershell",
                    )
                    st.code(
                        bundle_faiss_invoke_ps1_snippet_explicit(_root),
                        language="powershell",
                    )
        else:
            st.caption(
                "FAISS bundle index: **not present** — search uses tag/id overlap only. "
                "From the repo root (same defaults as **bundle_faiss_index** workflow). "
                + bundle_faiss_index_workflow_caption_note(),
            )
            st.code(bundle_faiss_build_command_snippet(), language="bash")
            with st.expander("Windows: Poetry + build (copy-paste)", expanded=False):
                st.caption(
                    "Same commands as bash; optional wrapper "
                    "``scripts/build_bundle_faiss_index.ps1``.",
                )
                st.code(
                    bundle_faiss_build_powershell_snippet_explicit(_root),
                    language="powershell",
                )
                st.caption("One-liner from any directory (absolute paths):")
                st.code(
                    bundle_faiss_invoke_ps1_snippet_explicit(_root),
                    language="powershell",
                )
            st.caption(
                "POSIX: optional ``bash scripts/build_bundle_faiss_index.sh`` "
                "(defaults repo root to the script's parent). "
                "``--help`` on the Python script lists ``--repo-root``, ``--catalog``, "
                "``--out-dir``. "
                "See **Poetry optional groups and FAISS** in ``PLAN_GAP.md``; workflow file ``"
                f"{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``.",
            )
        with st.expander("Operator drill-down (fo142)", expanded=False):
            st.caption(
                "Read-only: per-file sizes + UTC mtimes + bounded ``configs/bundles/index`` "
                "listing; no ``faiss`` import. Copy-paste rebuild uses the same resolved root "
                "as this console."
            )
            _faiss_dd = bundle_faiss_index_operator_drilldown(_root)
            st.json(_faiss_dd)
            _faiss_listing_rows = bundle_faiss_index_dir_listing_table_rows(_faiss_dd)
            if _faiss_listing_rows:
                _faiss_listing_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _faiss_listing_slug = bundle_faiss_operator_drilldown_export_filename_slug(
                    _root,
                )
                _faiss_listing_json = bundle_faiss_index_dir_listing_export_json(
                    _faiss_listing_rows,
                )
                _faiss_listing_csv = bundle_faiss_index_dir_listing_table_rows_csv(
                    _faiss_listing_rows,
                )
                _faiss_listing_dl_json_col, _faiss_listing_dl_csv_col = st.columns(2)
                with _faiss_listing_dl_json_col:
                    st.download_button(
                        label="Download FAISS index directory listing JSON",
                        data=_faiss_listing_json.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_index_listing_"
                            f"{_faiss_listing_slug}_{_faiss_listing_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_faiss_index_listing_json",
                    )
                with _faiss_listing_dl_csv_col:
                    if _faiss_listing_csv:
                        st.download_button(
                            label="Download FAISS index directory listing CSV",
                            data=_faiss_listing_csv.encode("utf-8"),
                            file_name=(
                                "hermes_bundle_faiss_index_listing_"
                                f"{_faiss_listing_slug}_{_faiss_listing_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_faiss_index_listing_csv",
                        )
            _faiss_dd_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _faiss_dd_slug = bundle_faiss_operator_drilldown_export_filename_slug(_root)
            _faiss_dd_json = bundle_faiss_index_operator_drilldown_export_json(_root)
            st.download_button(
                label="Download FAISS operator drill-down JSON",
                data=_faiss_dd_json.encode("utf-8"),
                file_name=(
                    "hermes_bundle_faiss_drilldown_"
                    f"{_faiss_dd_slug}_{_faiss_dd_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_faiss_operator_drilldown_json",
            )
            st.caption(
                "Rebuild with explicit ``--repo-root`` "
                "(matches **Effective repo root** above).",
            )
            st.code(bundle_faiss_build_command_snippet_explicit(_root), language="bash")
        _faiss_sum_metrics = bundle_faiss_readiness_summary_operator_metrics(_faiss_sum)
        _faiss_sum_metrics_cap = bundle_faiss_readiness_summary_operator_metrics_caption(
            _faiss_sum_metrics,
        )
        if _faiss_sum_metrics_cap:
            st.caption(_faiss_sum_metrics_cap)
        _faiss_sum_metric_rows = bundle_faiss_readiness_summary_operator_metrics_table_rows(
            _faiss_sum_metrics,
        )
        if _faiss_sum_metric_rows:
            st.dataframe(_faiss_sum_metric_rows, use_container_width=True)
        _faiss_ready_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _faiss_ready_metrics_slug = (
            bundle_faiss_readiness_summary_operator_metrics_export_filename_slug()
        )
        _faiss_ready_metrics_json = (
            bundle_faiss_readiness_summary_operator_metrics_export_json(_faiss_sum_metrics)
        )
        _faiss_ready_metrics_csv = (
            bundle_faiss_readiness_summary_operator_metrics_table_rows_csv(
                _faiss_sum_metric_rows,
            )
        )
        _faiss_ready_m_dl_json_col, _faiss_ready_m_dl_csv_col = st.columns(2)
        with _faiss_ready_m_dl_json_col:
            st.download_button(
                label="Download FAISS readiness operator metrics JSON",
                data=_faiss_ready_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_faiss_ready_metrics_slug}_"
                    f"{bundle_faiss_readiness_export_filename_slug(_root)}_"
                    f"{_faiss_ready_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_faiss_readiness_metrics_json",
            )
        with _faiss_ready_m_dl_csv_col:
            if _faiss_ready_metrics_csv:
                st.download_button(
                    label="Download FAISS readiness operator metrics CSV",
                    data=_faiss_ready_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_faiss_ready_metrics_slug}_"
                        f"{bundle_faiss_readiness_export_filename_slug(_root)}_"
                        f"{_faiss_ready_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_faiss_readiness_metrics_csv",
                )
        _faiss_ready_slug = bundle_faiss_readiness_export_filename_slug(_root)
        _faiss_ready_json = bundle_faiss_readiness_summary_export_json(_root)
        _faiss_ready_rows = bundle_faiss_readiness_summary_table_rows(_faiss_sum)
        _faiss_ready_csv = bundle_faiss_readiness_summary_table_rows_csv(_faiss_ready_rows)
        _faiss_ready_dl_json_col, _faiss_ready_dl_csv_col = st.columns(2)
        with _faiss_ready_dl_json_col:
            st.download_button(
                label="Download FAISS index readiness JSON",
                data=_faiss_ready_json.encode("utf-8"),
                file_name=(
                    "hermes_bundle_faiss_readiness_"
                    f"{_faiss_ready_slug}_{_faiss_ready_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_faiss_readiness_json",
            )
        with _faiss_ready_dl_csv_col:
            if _faiss_ready_csv:
                st.download_button(
                    label="Download FAISS index readiness CSV",
                    data=_faiss_ready_csv.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_readiness_"
                        f"{_faiss_ready_slug}_{_faiss_ready_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_faiss_readiness_csv",
                )
        _faiss_status_rows = bundle_faiss_index_status_table_rows(_faiss)
        if _faiss_status_rows:
            _faiss_status_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _faiss_status_slug = bundle_faiss_readiness_export_filename_slug(_root)
            _faiss_status_json = bundle_faiss_index_status_export_json(_faiss)
            _faiss_status_csv = bundle_faiss_index_status_table_rows_csv(_faiss_status_rows)
            _faiss_status_dl_json_col, _faiss_status_dl_csv_col = st.columns(2)
            with _faiss_status_dl_json_col:
                st.download_button(
                    label="Download FAISS index sync status JSON",
                    data=_faiss_status_json.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_index_status_"
                        f"{_faiss_status_slug}_{_faiss_status_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_faiss_index_status_json",
                )
            with _faiss_status_dl_csv_col:
                if _faiss_status_csv:
                    st.download_button(
                        label="Download FAISS index sync status CSV",
                        data=_faiss_status_csv.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_index_status_"
                            f"{_faiss_status_slug}_{_faiss_status_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_faiss_index_status_csv",
                    )
        with st.expander("Raw index readiness JSON", expanded=False):
            st.json(_faiss)
    st.text_input(
        "Query (q)",
        placeholder="e.g. auth, rbac, stripe",
        key="hermes_bundle_q",
    )
    st.number_input(
        "Max results (k)",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        key="hermes_bundle_k",
    )
    if st.button("Search catalog", key="hermes_bundle_search_btn"):
        _bq = str(st.session_state.get("hermes_bundle_q", ""))
        _bk = int(st.session_state.get("hermes_bundle_k", 5))
        if not _bq.strip():
            st.warning("Enter a non-empty query.")
        else:
            st.session_state[_LAST_BUNDLE_SEARCH_JSON] = run_bundle_catalog_search(
                _root,
                _bq,
                k=_bk,
            )
    _bundle_blob = st.session_state.get(_LAST_BUNDLE_SEARCH_JSON)
    if isinstance(_bundle_blob, dict) and str(_bundle_blob.get("query", "")).strip():
        _hits_q = str(_bundle_blob.get("query", ""))
        _hits_list = _bundle_blob.get("hits")
        _hits_n = len(_hits_list) if isinstance(_hits_list, list) else None
        _hits_qlen_cap = bundle_search_query_length_caption(
            _hits_q,
            hit_count=_hits_n,
        )
        if _hits_qlen_cap:
            st.caption(_hits_qlen_cap)
        _hits_k_cap = bundle_search_k_caption(_bundle_blob)
        if _hits_k_cap:
            st.caption(_hits_k_cap)
        _hits_sum_cap = bundle_search_hits_summary_caption(_bundle_blob)
        if _hits_sum_cap:
            st.caption(_hits_sum_cap)
        _hits_faiss_cap = bundle_search_faiss_ready_caption(_bundle_blob)
        if _hits_faiss_cap:
            st.caption(_hits_faiss_cap)
        _hits_count_cap = bundle_search_hit_count_caption(_bundle_blob)
        if _hits_count_cap:
            st.caption(_hits_count_cap)
        _hits_top_cap = bundle_search_top_hit_preview_caption(_bundle_blob)
        if _hits_top_cap:
            st.caption(_hits_top_cap)
        st.json(_bundle_blob)
        _empty_hits_cap = bundle_search_empty_hits_readiness_caption(_bundle_blob)
        if _empty_hits_cap:
            st.caption(_empty_hits_cap)
        _hits = bundle_search_hits_from_blob(_bundle_blob)
        if _hits:
            st.caption("Hits (table view)")
            st.dataframe(_hits, use_container_width=True)
            _bs_hits_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _bs_hits_slug = bundle_search_filename_slug(
                str(_bundle_blob.get("query", "")),
            )
            _bs_hits_json = bundle_search_hits_export_json(_hits)
            _bs_hits_csv = bundle_search_hits_table_rows_csv(_hits)
            _bs_hits_dl_json_col, _bs_hits_dl_csv_col = st.columns(2)
            with _bs_hits_dl_json_col:
                st.download_button(
                    label="Download bundle search hits JSON",
                    data=_bs_hits_json.encode("utf-8"),
                    file_name=(
                        f"hermes_bundle_search_hits_{_bs_hits_slug}_{_bs_hits_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_search_hits_json",
                )
            with _bs_hits_dl_csv_col:
                if _bs_hits_csv:
                    st.download_button(
                        label="Download bundle search hits CSV",
                        data=_bs_hits_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_bundle_search_hits_{_bs_hits_slug}_{_bs_hits_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_search_hits_csv",
                    )
            _stale_cap = bundle_search_after_hits_stale_caption(_bundle_blob)
            if _stale_cap:
                st.caption(_stale_cap)
        _search_metrics = bundle_search_operator_metrics(_bundle_blob)
        _search_metrics_cap = bundle_search_operator_metrics_caption(_search_metrics)
        if _search_metrics_cap:
            st.caption(_search_metrics_cap)
        _search_metric_rows = bundle_search_operator_metrics_table_rows(_search_metrics)
        if _search_metric_rows:
            st.dataframe(_search_metric_rows, use_container_width=True)
        _bs_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _bs_slug = bundle_search_filename_slug(str(_bundle_blob.get("query", "")))
        _search_metrics_slug = bundle_search_operator_metrics_export_filename_slug()
        _search_metrics_json = bundle_search_operator_metrics_export_json(_search_metrics)
        _search_metrics_csv = bundle_search_operator_metrics_table_rows_csv(_search_metric_rows)
        _bs_m_dl1, _bs_m_dl2 = st.columns(2)
        with _bs_m_dl1:
            st.download_button(
                label="Download bundle search operator metrics JSON",
                data=_search_metrics_json.encode("utf-8"),
                file_name=f"hermes_{_search_metrics_slug}_{_bs_slug}_{_bs_ts}.json",
                mime="application/json",
                key="hermes_dl_bundle_search_metrics_json",
            )
        with _bs_m_dl2:
            if _search_metrics_csv:
                st.download_button(
                    label="Download bundle search operator metrics CSV",
                    data=_search_metrics_csv.encode("utf-8"),
                    file_name=f"hermes_{_search_metrics_slug}_{_bs_slug}_{_bs_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_search_metrics_csv",
                )
        with st.expander("Raw bundle search operator metrics JSON", expanded=False):
            st.json(_search_metrics)
        st.download_button(
            label="Download bundle search JSON",
            data=json.dumps(_bundle_blob, indent=2).encode("utf-8"),
            file_name=f"hermes_bundle_search_{_bs_slug}_{_bs_ts}.json",
            mime="application/json",
            key="hermes_dl_bundle_search_json",
        )
with st.expander("Bundle catalog editor (writes via API)", expanded=False):
    st.caption(
        "Edits use **PATCH /v1/bundles/catalog/bundles/{id}** (admin token). "
        "Reload catalog from API before saving."
    )
    _bc_admin = st.text_input(
        "X-Hermes-Admin-Token",
        key="hermes_bundle_edit_token",
        type="password",
    )
    if st.button("Reload bundle catalog from API", key="hermes_bundle_edit_reload"):
        try:
            _bc_r = httpx.get(f"{API_BASE}/bundles/catalog", timeout=10.0)
            _bc_r.raise_for_status()
            st.session_state["hermes_bundle_edit_catalog"] = _bc_r.json()
            st.success("Loaded bundle catalog from API.")
        except httpx.HTTPError as _bc_exc:
            st.error(f"API error: {_bc_exc}")
    _bc_catalog = st.session_state.get("hermes_bundle_edit_catalog")
    if not isinstance(_bc_catalog, dict):
        st.caption("Click 'Reload bundle catalog from API' first.")
    else:
        _bc_bundles = _bc_catalog.get("bundles") or []
        _bc_ids = [
            str(b.get("id", ""))
            for b in _bc_bundles
            if isinstance(b, dict) and b.get("id")
        ]
        _bc_sel = st.selectbox(
            "Bundle",
            options=_bc_ids,
            key="hermes_bundle_edit_select",
        )
        _bc_row = next(
            (b for b in _bc_bundles if isinstance(b, dict) and str(b.get("id")) == _bc_sel),
            {},
        )
        st.text_input(
            "title",
            value=str(_bc_row.get("title") or ""),
            key="hermes_bundle_edit_title",
        )
        _bc_tags = _bc_row.get("tags") or []
        st.text_area(
            "tags (comma-separated)",
            value=", ".join(str(t) for t in _bc_tags if t is not None),
            key="hermes_bundle_edit_tags",
        )
        _bc_issues = bundle_editor_validation_issues(_bc_sel)
        if _bc_issues:
            for _msg in _bc_issues:
                st.warning(_msg)
        if st.button(
            "Save bundle (PATCH)",
            key="hermes_bundle_edit_save",
            disabled=bool(_bc_issues) or not _bc_admin,
        ):
            _payload = bundle_editor_patch_payload(
                title=str(st.session_state.get("hermes_bundle_edit_title", "")),
                tags_text=str(st.session_state.get("hermes_bundle_edit_tags", "")),
            )
            try:
                _bc_patch = httpx.patch(
                    f"{API_BASE}/bundles/catalog/bundles/{_bc_sel}",
                    headers={"X-Hermes-Admin-Token": _bc_admin},
                    json=_payload,
                    timeout=15.0,
                )
                _bc_patch.raise_for_status()
                st.session_state["hermes_bundle_edit_catalog"] = _bc_patch.json()
                st.success("Bundle catalog updated.")
            except httpx.HTTPError as _bc_patch_exc:
                st.error(f"PATCH failed: {_bc_patch_exc}")
with st.expander("Module Integrator gate (workflow preview)", expanded=False):
    st.caption(
        "**fo131** read-only preview + **fo132** / **fo140** optional subtree disk apply + "
        "**§14 #13** optional **full-profile** shallow merge + **fo133** "
        "threshold source "
        "breakdown + **fo134** universal critique + **fo135** self-refinement + **fo136** "
        "security-scan-metadata + **fo137** escalation-suppress + **fo139** "
        "agent-evaluator workflow explainer "
        "(nested expanders): preview "
        "``ModuleIntegrator.score_fit`` against ``configs/bundles/catalog.yaml`` using the same "
        "``integrator_gate`` knobs as the orchestrator (workflow YAML + "
        "``configs/integrator/thresholds.yaml``; "
        "``HERMES_INTEGRATOR_MIN_SCORE_TO_PASS`` still wins "
        "when set). Paste an ``integrator_gate:`` fragment to override **min_score** / "
        "**enabled** / "
        "**project_tags** for preview; **Apply** (fo132 / fo140) merges only that subtree when "
        f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}`` is enabled and you confirm the profile stem.",
    )
    _iroot = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
    st.caption(f"Effective repo root: `{_iroot}`")
    _wf_keys = list_workflow_profile_keys(_iroot)
    if not _wf_keys:
        st.warning("No workflow profiles found under ``configs/workflows/``.")
        _wf_pick: str | None = None
    else:
        _wf_pick = st.selectbox(
            "Workflow profile (YAML stem)",
            options=_wf_keys,
            index=_wf_keys.index("default") if "default" in _wf_keys else 0,
            key="hermes_integrator_wf_profile",
        )
    with st.expander("Universal critique (workflow YAML, fo134)", expanded=False):
        st.caption(
            "Read-only: ``universal_critique`` from the **same** workflow profile as integrator "
            "preview — **yaml_only** is frozen file content; **effective_with_env** applies "
            "non-empty ``HERMES_*`` critique env overrides (same rules as the orchestrator). "
            "PLAN_GAP §14 #16."
        )
        _uc_expl = universal_critique_workflow_explainer_payload(
            _iroot,
            workflow_profile=_wf_pick,
        )
        _uc_expl_metrics = universal_critique_workflow_explainer_operator_metrics(_uc_expl)
        _uc_expl_metrics_cap = universal_critique_workflow_explainer_operator_metrics_caption(
            _uc_expl_metrics,
        )
        if _uc_expl_metrics_cap:
            st.caption(_uc_expl_metrics_cap)
        _uc_expl_metric_rows = universal_critique_workflow_explainer_operator_metrics_table_rows(
            _uc_expl_metrics,
        )
        if _uc_expl_metric_rows:
            st.dataframe(_uc_expl_metric_rows, use_container_width=True, hide_index=True)
        _uc_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _uc_expl_metrics_slug = (
            universal_critique_workflow_explainer_operator_metrics_export_filename_slug()
        )
        _uc_expl_metrics_json = universal_critique_workflow_explainer_operator_metrics_export_json(
            _uc_expl_metrics,
        )
        _uc_expl_metrics_csv = (
            universal_critique_workflow_explainer_operator_metrics_table_rows_csv(
                _uc_expl_metric_rows,
            )
        )
        _uc_expl_m_dl_json_col, _uc_expl_m_dl_csv_col = st.columns(2)
        with _uc_expl_m_dl_json_col:
            st.download_button(
                label="Download universal critique operator metrics JSON",
                data=_uc_expl_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_uc_expl_metrics_slug}_{_uc_expl_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_universal_critique_explainer_metrics_json",
            )
        with _uc_expl_m_dl_csv_col:
            if _uc_expl_metrics_csv:
                st.download_button(
                    label="Download universal critique operator metrics CSV",
                    data=_uc_expl_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_uc_expl_metrics_slug}_{_uc_expl_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_universal_critique_explainer_metrics_csv",
                )
        _uc_enabled_cap = universal_critique_enabled_stages_caption(_uc_expl)
        if _uc_enabled_cap:
            st.caption(_uc_enabled_cap)
        _uc_default_cap = universal_critique_default_enabled_caption(_uc_expl)
        if _uc_default_cap:
            st.caption(_uc_default_cap)
        _uc_present_cap = universal_critique_yaml_present_caption(_uc_expl)
        if _uc_present_cap:
            st.caption(_uc_present_cap)
        _uc_relpath_cap = universal_critique_workflow_yaml_relpath_caption(_uc_expl)
        if _uc_relpath_cap:
            st.caption(_uc_relpath_cap)
        _uc_bytes_cap = universal_critique_workflow_yaml_bytes_caption(_uc_expl)
        if _uc_bytes_cap:
            st.caption(_uc_bytes_cap)
        _uc_nonempty_cap = universal_critique_yaml_top_level_nonempty_count_caption(
            _uc_expl,
        )
        if _uc_nonempty_cap:
            st.caption(_uc_nonempty_cap)
        _uc_enabled_true_cap = universal_critique_yaml_top_level_enabled_true_count_caption(
            _uc_expl,
        )
        if _uc_enabled_true_cap:
            st.caption(_uc_enabled_true_cap)
        _uc_enabled_false_cap = universal_critique_yaml_top_level_enabled_false_count_caption(
            _uc_expl,
        )
        if _uc_enabled_false_cap:
            st.caption(_uc_enabled_false_cap)
        _uc_mapping_child_cap = universal_critique_yaml_top_level_mapping_child_count_caption(
            _uc_expl,
        )
        if _uc_mapping_child_cap:
            st.caption(_uc_mapping_child_cap)
        _uc_list_child_cap = universal_critique_yaml_top_level_list_child_count_caption(
            _uc_expl,
        )
        if _uc_list_child_cap:
            st.caption(_uc_list_child_cap)
        _uc_bucket_cap = universal_critique_yaml_enabled_bucket_caption(_uc_expl)
        if _uc_bucket_cap:
            st.caption(_uc_bucket_cap)
        _uc_stage_keys_cap = universal_critique_yaml_stage_keys_caption(_uc_expl)
        if _uc_stage_keys_cap:
            st.caption(_uc_stage_keys_cap)
        _uc_rows = [
            {
                "field": "universal_critique block in YAML",
                "value": str(_uc_expl.get("universal_critique_yaml_present")),
            },
            {
                "field": "universal_critique YAML top-level keys",
                "value": ", ".join(_uc_expl.get("universal_critique_yaml_top_level_keys") or [])
                or "—",
            },
            {
                "field": "universal_critique YAML top-level nonempty value count",
                "value": str(_uc_expl.get("universal_critique_yaml_top_level_nonempty_count")),
            },
            {
                "field": "universal_critique YAML top-level enabled: true subtree count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_enabled_true_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level enabled: false subtree count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_enabled_false_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level mapping child count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_mapping_child_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level scalar/null leaf count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_scalar_leaf_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level list child count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_list_child_count"),
                ),
            },
            {
                "field": "universal_critique YAML mapping children without enabled key",
                "value": str(
                    _uc_expl.get(
                        "universal_critique_yaml_top_level_enabled_unset_mapping_count",
                    ),
                ),
            },
            {
                "field": "workflow YAML file size (bytes, on disk)",
                "value": "—"
                if _uc_expl.get("universal_critique_workflow_yaml_bytes") is None
                else str(_uc_expl.get("universal_critique_workflow_yaml_bytes")),
            },
            {
                "field": "implementation LLM (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("impl_llm")),
            },
            {
                "field": "implementation stub (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("impl_stub")),
            },
            {
                "field": "test_writer enabled (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("tw_enabled")),
            },
            {
                "field": "planner enabled (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("pll_enabled")),
            },
        ]
        st.dataframe(_uc_rows, use_container_width=True, hide_index=True)
        _uc_delta = universal_critique_env_override_deltas(_uc_expl)
        if _uc_delta:
            st.caption("Env overrides vs frozen YAML (non-matching knobs only; §14 #16).")
            st.dataframe(_uc_delta, use_container_width=True, hide_index=True)
        _uc_delta_cap = universal_critique_env_override_summary_caption(_uc_expl)
        if _uc_delta_cap:
            st.caption(_uc_delta_cap)
        _uc_err = _uc_expl.get("load_error")
        if isinstance(_uc_err, str) and _uc_err.strip():
            st.warning(str(_uc_err))
        _uc_expl_rows = universal_critique_explainer_table_rows(_uc_expl)
        if _uc_expl_rows:
            _uc_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _uc_expl_slug = universal_critique_export_filename_slug()
            _uc_expl_json = universal_critique_explainer_export_json(_uc_expl)
            _uc_expl_csv = universal_critique_explainer_table_rows_csv(_uc_expl_rows)
            _uc_expl_dl_json_col, _uc_expl_dl_csv_col = st.columns(2)
            with _uc_expl_dl_json_col:
                st.download_button(
                    label="Download universal critique explainer JSON",
                    data=_uc_expl_json.encode("utf-8"),
                    file_name=f"hermes_{_uc_expl_slug}_explainer_{_uc_expl_ts}.json",
                    mime="application/json",
                    key="hermes_dl_universal_critique_explainer_json",
                )
            with _uc_expl_dl_csv_col:
                if _uc_expl_csv:
                    st.download_button(
                        label="Download universal critique explainer CSV",
                        data=_uc_expl_csv.encode("utf-8"),
                        file_name=f"hermes_{_uc_expl_slug}_explainer_{_uc_expl_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_explainer_csv",
                    )
        with st.expander("Raw universal critique explainer JSON", expanded=False):
            st.json(_uc_expl)
        st.caption(
            "Optional **workflow vs timeline** table: paste the top-level "
            "``universal_critique`` object **or** full **GET /v1/runs/{id}/timeline** JSON. "
            "Workflow counts are from the selected profile YAML; timeline values are "
            "observed gate rollups. PLAN_GAP §14 #16."
        )
        _uc_tl_raw = st.text_area(
            "Optional timeline or universal_critique JSON",
            value="",
            height=100,
            key="hermes_universal_critique_timeline_compare_json",
            placeholder='{"fail_count": 0, "stage_count": 2, "stages": [...]} or full timeline',
        )
        _uc_tl_uc: dict[str, Any] | None = None
        if _uc_tl_raw.strip():
            try:
                _uc_tl_parsed = json.loads(_uc_tl_raw)
                if isinstance(_uc_tl_parsed, dict):
                    _uc_tl_uc = universal_critique_snapshot_from_compare_paste(
                        _uc_tl_parsed,
                    )
                else:
                    st.warning(
                        "Timeline comparison JSON must be a single object (dict), "
                        "not a list or scalar.",
                    )
            except json.JSONDecodeError as exc:
                st.warning(f"Invalid JSON ({exc.msg}).")
        _uc_compare_rows = universal_critique_workflow_vs_timeline_rows(
            _uc_expl,
            _uc_tl_uc,
        )
        st.dataframe(_uc_compare_rows, use_container_width=True, hide_index=True)
        with st.expander("Raw universal_critique vs pasted timeline JSON", expanded=False):
            st.json(
                {
                    "workflow_explainer": _uc_expl,
                    "timeline_universal_critique": _uc_tl_uc,
                },
            )
    with st.expander("Self-refinement (workflow + policy, fo135)", expanded=False):
        st.caption(
            "Read-only: workflow ``self_refinement`` from the **same** profile stem vs "
            "``configs/self_refinement/policy.yaml`` — **marker_merge** mirrors "
            "``_maybe_emit_self_refinement_stage_marker`` (emit when policy **or** workflow "
            "enables; version/description workflow wins when set). Env "
            "``HERMES_SELF_REFINEMENT_STAGE_MARKER`` in ``0``/``false``/``no`` suppresses "
            "the ``self_refinement:policy`` stage marker. PLAN_GAP §14 #17."
        )
        _sr_expl = self_refinement_workflow_explainer_payload(
            _iroot,
            workflow_profile=_wf_pick,
        )
        _sr_expl_metrics = self_refinement_workflow_explainer_operator_metrics(_sr_expl)
        _sr_expl_metrics_cap = self_refinement_workflow_explainer_operator_metrics_caption(
            _sr_expl_metrics,
        )
        if _sr_expl_metrics_cap:
            st.caption(_sr_expl_metrics_cap)
        _sr_expl_metric_rows = self_refinement_workflow_explainer_operator_metrics_table_rows(
            _sr_expl_metrics,
        )
        if _sr_expl_metric_rows:
            st.dataframe(_sr_expl_metric_rows, use_container_width=True, hide_index=True)
        _sr_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _sr_expl_metrics_slug = (
            self_refinement_workflow_explainer_operator_metrics_export_filename_slug()
        )
        _sr_expl_metrics_json = self_refinement_workflow_explainer_operator_metrics_export_json(
            _sr_expl_metrics,
        )
        _sr_expl_metrics_csv = (
            self_refinement_workflow_explainer_operator_metrics_table_rows_csv(
                _sr_expl_metric_rows,
            )
        )
        _sr_expl_m_dl_json_col, _sr_expl_m_dl_csv_col = st.columns(2)
        with _sr_expl_m_dl_json_col:
            st.download_button(
                label="Download self-refinement operator metrics JSON",
                data=_sr_expl_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_sr_expl_metrics_slug}_{_sr_expl_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_self_refinement_explainer_metrics_json",
            )
        with _sr_expl_m_dl_csv_col:
            if _sr_expl_metrics_csv:
                st.download_button(
                    label="Download self-refinement operator metrics CSV",
                    data=_sr_expl_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_sr_expl_metrics_slug}_{_sr_expl_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_self_refinement_explainer_metrics_csv",
                )
        _sr_emit_cap = self_refinement_would_emit_marker_caption(
            _sr_expl.get("marker_merge"),
        )
        if _sr_emit_cap:
            st.caption(_sr_emit_cap)
        _sr_ver_cap = self_refinement_merged_version_caption(_sr_expl.get("marker_merge"))
        if _sr_ver_cap:
            st.caption(_sr_ver_cap)
        _sr_desc_cap = self_refinement_merged_description_preview_caption(
            _sr_expl.get("marker_merge"),
        )
        if _sr_desc_cap:
            st.caption(_sr_desc_cap)
        _sr_after_env_cap = self_refinement_would_emit_after_env_caption(
            _sr_expl.get("marker_merge"),
        )
        if _sr_after_env_cap:
            st.caption(_sr_after_env_cap)
        _sr_ungated_env_cap = self_refinement_ungated_loop_env_gate_caption(_sr_expl)
        if _sr_ungated_env_cap:
            st.caption(_sr_ungated_env_cap)
        _sr_disk_ver_cap = self_refinement_policy_yaml_disk_version_caption(_sr_expl)
        if _sr_disk_ver_cap:
            st.caption(_sr_disk_ver_cap)
        _sr_pol_bytes_cap = self_refinement_policy_yaml_file_bytes_caption(_sr_expl)
        if _sr_pol_bytes_cap:
            st.caption(_sr_pol_bytes_cap)
        _sr_raw_type_cap = self_refinement_workflow_yaml_raw_type_caption(_sr_expl)
        if _sr_raw_type_cap:
            st.caption(_sr_raw_type_cap)
        _sr_rows = [
            {
                "field": "self_refinement block in workflow YAML",
                "value": str(_sr_expl.get("self_refinement_yaml_present")),
            },
            {
                "field": "self_refinement (raw value Python type)",
                "value": "—"
                if _sr_expl.get("self_refinement_workflow_yaml_raw_type") is None
                else str(_sr_expl.get("self_refinement_workflow_yaml_raw_type")),
            },
            {
                "field": "self_refinement (mapping string-key count in YAML)",
                "value": "—"
                if _sr_expl.get("self_refinement_yaml_mapping_string_key_count") is None
                else str(_sr_expl.get("self_refinement_yaml_mapping_string_key_count")),
            },
            {
                "field": "policy.yaml on-disk size (bytes)",
                "value": "—"
                if _sr_expl.get("policy_yaml", {}).get("policy_yaml_file_bytes") is None
                else str(_sr_expl.get("policy_yaml", {}).get("policy_yaml_file_bytes")),
            },
            {
                "field": "policy.yaml top-level version (int, disk)",
                "value": "—"
                if _sr_expl.get("policy_yaml", {}).get("policy_yaml_top_level_version_int")
                is None
                else str(
                    _sr_expl.get("policy_yaml", {}).get("policy_yaml_top_level_version_int"),
                ),
            },
            {
                "field": "policy.yaml description length (chars)",
                "value": str(_sr_expl.get("policy_yaml", {}).get("description_char_len")),
            },
            {
                "field": "workflow self_refinement.enabled",
                "value": str(_sr_expl.get("workflow_self_refinement", {}).get("enabled")),
            },
            {
                "field": "policy.yaml enabled (disk)",
                "value": str(_sr_expl.get("policy_yaml", {}).get("enabled")),
            },
            {
                "field": "would_emit self_refinement:policy marker",
                "value": str(
                    _sr_expl.get("marker_merge", {}).get("would_emit_self_refinement_marker"),
                ),
            },
            {
                "field": "would_emit after env (effective)",
                "value": str(
                    _sr_expl.get("marker_merge", {}).get("would_emit_marker_after_env"),
                ),
            },
        ]
        st.dataframe(_sr_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Optional **marker_merge vs timeline** table: paste either the top-level "
            "``self_refinement`` object **or** the full **GET /v1/runs/{id}/timeline** JSON "
            "(``events`` + summaries); the console extracts ``self_refinement`` when needed. "
            "Explainer values are predictive for the workflow profile above; timeline values "
            "are the last observed snapshot. When present, **``marker_count``** matches the "
            "timeline read-model (Run detail / API). PLAN_GAP §14 #17."
        )
        _sr_tl_raw = st.text_area(
            "Optional timeline or self_refinement JSON",
            value="",
            height=100,
            key="hermes_self_refinement_timeline_compare_json",
            placeholder='{"version": 1, "description": "…"} or full timeline JSON',
        )
        _sr_tl_sr: dict[str, Any] | None = None
        if _sr_tl_raw.strip():
            try:
                _sr_tl_parsed = json.loads(_sr_tl_raw)
                if isinstance(_sr_tl_parsed, dict):
                    _sr_tl_sr = self_refinement_snapshot_from_compare_paste(_sr_tl_parsed)
                else:
                    st.warning(
                        "Timeline comparison JSON must be a single object (dict), "
                        "not a list or scalar.",
                    )
            except json.JSONDecodeError as exc:
                st.warning(f"Invalid JSON ({exc.msg}).")
        _sr_compare_rows = self_refinement_marker_merge_vs_timeline_rows(
            _sr_expl.get("marker_merge"),
            _sr_tl_sr,
        )
        st.dataframe(_sr_compare_rows, use_container_width=True, hide_index=True)
        _sr_marker_merge = _sr_expl.get("marker_merge")
        if isinstance(_sr_marker_merge, dict):
            _sr_compare_snap = self_refinement_marker_merge_compare_snapshot(
                _sr_marker_merge,
                _sr_tl_sr,
            )
            _sr_compare_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sr_compare_slug = self_refinement_marker_merge_compare_export_filename_slug()
            _sr_compare_json = self_refinement_marker_merge_compare_export_json(
                _sr_compare_snap,
            )
            _sr_compare_csv = self_refinement_marker_merge_compare_table_rows_csv(
                _sr_compare_rows,
            )
            _sr_compare_dl_json_col, _sr_compare_dl_csv_col = st.columns(2)
            with _sr_compare_dl_json_col:
                st.download_button(
                    label="Download marker compare JSON",
                    data=_sr_compare_json.encode("utf-8"),
                    file_name=f"hermes_{_sr_compare_slug}_{_sr_compare_ts}.json",
                    mime="application/json",
                    key="hermes_dl_self_refinement_marker_compare_json",
                )
            with _sr_compare_dl_csv_col:
                if _sr_compare_csv:
                    st.download_button(
                        label="Download marker compare CSV",
                        data=_sr_compare_csv.encode("utf-8"),
                        file_name=f"hermes_{_sr_compare_slug}_{_sr_compare_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_self_refinement_marker_compare_csv",
                    )
        with st.expander("Raw marker_merge vs pasted timeline JSON", expanded=False):
            st.json(
                {
                    "marker_merge": _sr_expl.get("marker_merge"),
                    "timeline_self_refinement": _sr_tl_sr,
                },
            )
        _sr_err = _sr_expl.get("load_error")
        if isinstance(_sr_err, str) and _sr_err.strip():
            st.warning(str(_sr_err))
        _sr_expl_rows = self_refinement_explainer_table_rows(_sr_expl)
        if _sr_expl_rows:
            _sr_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sr_expl_slug = self_refinement_export_filename_slug()
            _sr_expl_json = self_refinement_explainer_export_json(_sr_expl)
            _sr_expl_csv = self_refinement_explainer_table_rows_csv(_sr_expl_rows)
            _sr_expl_dl_json_col, _sr_expl_dl_csv_col = st.columns(2)
            with _sr_expl_dl_json_col:
                st.download_button(
                    label="Download self-refinement explainer JSON",
                    data=_sr_expl_json.encode("utf-8"),
                    file_name=f"hermes_{_sr_expl_slug}_explainer_{_sr_expl_ts}.json",
                    mime="application/json",
                    key="hermes_dl_self_refinement_explainer_json",
                )
            with _sr_expl_dl_csv_col:
                if _sr_expl_csv:
                    st.download_button(
                        label="Download self-refinement explainer CSV",
                        data=_sr_expl_csv.encode("utf-8"),
                        file_name=f"hermes_{_sr_expl_slug}_explainer_{_sr_expl_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_self_refinement_explainer_csv",
                    )
        with st.expander("Raw self-refinement explainer JSON", expanded=False):
            st.json(_sr_expl)
    with st.expander("Security scan metadata on verify (workflow + env, fo136)", expanded=False):
        st.caption(
            "Read-only: ``security_scan_metadata_on_verify`` from the **same** workflow profile vs "
            "``HERMES_ATTACH_SECURITY_SCAN_METADATA`` — **yaml_parsed_bool** is frozen YAML only; "
            "**effective_enabled** matches ``security_scan_metadata_on_verify_enabled`` "
            "(truthy env forces on; ``0`` / ``false`` / ``no`` kill-switch). PLAN_GAP §14 #18."
        )
        _ssm_expl = security_scan_metadata_workflow_explainer_payload(
            _iroot,
            workflow_profile=_wf_pick,
        )
        _ssm_expl_metrics = security_scan_metadata_workflow_explainer_operator_metrics(
            _ssm_expl,
        )
        _ssm_expl_metrics_cap = (
            security_scan_metadata_workflow_explainer_operator_metrics_caption(
                _ssm_expl_metrics,
            )
        )
        if _ssm_expl_metrics_cap:
            st.caption(_ssm_expl_metrics_cap)
        _ssm_expl_metric_rows = (
            security_scan_metadata_workflow_explainer_operator_metrics_table_rows(
                _ssm_expl_metrics,
            )
        )
        if _ssm_expl_metric_rows:
            st.dataframe(_ssm_expl_metric_rows, use_container_width=True, hide_index=True)
        _ssm_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _ssm_expl_metrics_slug = (
            security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug()
        )
        _ssm_expl_metrics_json = (
            security_scan_metadata_workflow_explainer_operator_metrics_export_json(
                _ssm_expl_metrics,
            )
        )
        _ssm_expl_metrics_csv = (
            security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv(
                _ssm_expl_metric_rows,
            )
        )
        _ssm_expl_m_dl_json_col, _ssm_expl_m_dl_csv_col = st.columns(2)
        with _ssm_expl_m_dl_json_col:
            st.download_button(
                label="Download security scan metadata operator metrics JSON",
                data=_ssm_expl_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_ssm_expl_metrics_slug}_{_ssm_expl_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_security_scan_metadata_explainer_metrics_json",
            )
        with _ssm_expl_m_dl_csv_col:
            if _ssm_expl_metrics_csv:
                st.download_button(
                    label="Download security scan metadata operator metrics CSV",
                    data=_ssm_expl_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_ssm_expl_metrics_slug}_{_ssm_expl_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_security_scan_metadata_explainer_metrics_csv",
                )
        _ssm_env = _ssm_expl.get("HERMES_ATTACH_SECURITY_SCAN_METADATA")
        _ssm_env_raw = ""
        if isinstance(_ssm_env, dict):
            _ssm_env_raw = str(_ssm_env.get("raw", ""))
        _ssm_yaml_val = _ssm_expl.get("security_scan_metadata_on_verify_yaml_value")
        _ssm_rows = [
            {
                "field": "workflow YAML top-level version (int)",
                "value": "—"
                if _ssm_expl.get("workflow_yaml_top_level_version_int") is None
                else str(_ssm_expl.get("workflow_yaml_top_level_version_int")),
            },
            {
                "field": "workflow YAML top-level string key count",
                "value": "—"
                if _ssm_expl.get("workflow_yaml_top_level_string_key_count") is None
                else str(_ssm_expl.get("workflow_yaml_top_level_string_key_count")),
            },
            {
                "field": "workflow YAML file size (bytes, on disk)",
                "value": "—"
                if _ssm_expl.get("workflow_yaml_file_bytes") is None
                else str(_ssm_expl.get("workflow_yaml_file_bytes")),
            },
            {
                "field": "security_scan_metadata_on_verify key in YAML",
                "value": str(_ssm_expl.get("security_scan_metadata_on_verify_yaml_key_present")),
            },
            {
                "field": "security_scan_metadata_on_verify (raw value)",
                "value": "—" if _ssm_yaml_val is None else repr(_ssm_yaml_val),
            },
            {
                "field": "security_scan_metadata_on_verify (raw value Python type)",
                "value": "—"
                if _ssm_expl.get("security_scan_metadata_on_verify_yaml_raw_type") is None
                else str(_ssm_expl.get("security_scan_metadata_on_verify_yaml_raw_type")),
            },
            {
                "field": "security_scan_metadata_on_verify (mapping string-key count)",
                "value": "—"
                if _ssm_expl.get("security_scan_metadata_on_verify_mapping_string_key_count")
                is None
                else str(
                    _ssm_expl.get("security_scan_metadata_on_verify_mapping_string_key_count"),
                ),
            },
            {
                "field": "yaml_parsed_bool (workflow file only)",
                "value": str(_ssm_expl.get("yaml_parsed_bool")),
            },
            {
                "field": "HERMES_ATTACH_SECURITY_SCAN_METADATA (raw)",
                "value": _ssm_env_raw if _ssm_env_raw else "(unset)",
            },
            {
                "field": "effective_enabled (YAML + env)",
                "value": str(_ssm_expl.get("effective_enabled")),
            },
            {
                "field": "yaml_parsed_bool matches effective_enabled",
                "value": str(
                    _ssm_expl.get("security_scan_metadata_yaml_parsed_bool_matches_effective"),
                ),
            },
        ]
        st.dataframe(_ssm_rows, use_container_width=True, hide_index=True)
        _ssm_relpath_cap = security_scan_metadata_workflow_yaml_relpath_caption(_ssm_expl)
        if _ssm_relpath_cap:
            st.caption(_ssm_relpath_cap)
        _ssm_bytes_cap = security_scan_metadata_workflow_yaml_file_bytes_caption(_ssm_expl)
        if _ssm_bytes_cap:
            st.caption(_ssm_bytes_cap)
        _ssm_version_cap = security_scan_metadata_workflow_yaml_version_caption(_ssm_expl)
        if _ssm_version_cap:
            st.caption(_ssm_version_cap)
        _ssm_str_keys_cap = security_scan_metadata_workflow_yaml_string_key_count_caption(
            _ssm_expl,
        )
        if _ssm_str_keys_cap:
            st.caption(_ssm_str_keys_cap)
        _ssm_raw_type_cap = security_scan_metadata_yaml_raw_type_caption(_ssm_expl)
        if _ssm_raw_type_cap:
            st.caption(_ssm_raw_type_cap)
        _ssm_eff_cap = security_scan_metadata_effective_enabled_caption(_ssm_expl)
        if _ssm_eff_cap:
            st.caption(_ssm_eff_cap)
        _ssm_env_cap = security_scan_metadata_env_gate_caption(_ssm_expl)
        if _ssm_env_cap:
            st.caption(_ssm_env_cap)
        _ssm_map_cap = security_scan_metadata_mapping_key_count_caption(_ssm_expl)
        if _ssm_map_cap:
            st.caption(_ssm_map_cap)
        _ssm_mis_cap = security_scan_metadata_yaml_effective_mismatch_caption(_ssm_expl)
        if _ssm_mis_cap:
            st.caption(_ssm_mis_cap)
        _ssm_err = _ssm_expl.get("load_error")
        if isinstance(_ssm_err, str) and _ssm_err.strip():
            st.warning(str(_ssm_err))
        _ssm_expl_rows = security_scan_metadata_explainer_table_rows(_ssm_expl)
        if _ssm_expl_rows:
            _ssm_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ssm_expl_slug = security_scan_metadata_export_filename_slug()
            _ssm_expl_json = security_scan_metadata_explainer_export_json(_ssm_expl)
            _ssm_expl_csv = security_scan_metadata_explainer_table_rows_csv(_ssm_expl_rows)
            _ssm_expl_dl_json_col, _ssm_expl_dl_csv_col = st.columns(2)
            with _ssm_expl_dl_json_col:
                st.download_button(
                    label="Download security scan metadata explainer JSON",
                    data=_ssm_expl_json.encode("utf-8"),
                    file_name=f"hermes_{_ssm_expl_slug}_explainer_{_ssm_expl_ts}.json",
                    mime="application/json",
                    key="hermes_dl_security_scan_metadata_explainer_json",
                )
            with _ssm_expl_dl_csv_col:
                if _ssm_expl_csv:
                    st.download_button(
                        label="Download security scan metadata explainer CSV",
                        data=_ssm_expl_csv.encode("utf-8"),
                        file_name=f"hermes_{_ssm_expl_slug}_explainer_{_ssm_expl_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_security_scan_metadata_explainer_csv",
                    )
        with st.expander("Raw security scan metadata explainer JSON", expanded=False):
            st.json(_ssm_expl)
    with st.expander("Escalation suppress (workflow YAML, fo137)", expanded=False):
        st.caption(
            "Read-only: ``escalation.suppress_automatic_escalation`` from the **same** profile "
            "stem — **suppress_automatic_escalation_effective** matches "
            "``parse_escalation_workflow_block`` (same boolean the pipeline uses in "
            "``_workflow_suppresses_automatic_escalation`` once the run profile resolves to "
            "this stem). Non-dict ``escalation:`` collapses to off. PLAN_GAP §14 #19."
        )
        _es_expl = escalation_suppress_workflow_explainer_payload(
            _iroot,
            workflow_profile=_wf_pick,
        )
        _es_expl_metrics = escalation_suppress_workflow_explainer_operator_metrics(_es_expl)
        _es_expl_metrics_cap = escalation_suppress_workflow_explainer_operator_metrics_caption(
            _es_expl_metrics,
        )
        if _es_expl_metrics_cap:
            st.caption(_es_expl_metrics_cap)
        _es_expl_metric_rows = (
            escalation_suppress_workflow_explainer_operator_metrics_table_rows(
                _es_expl_metrics,
            )
        )
        if _es_expl_metric_rows:
            st.dataframe(_es_expl_metric_rows, use_container_width=True, hide_index=True)
        _es_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _es_expl_metrics_slug = (
            escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug()
        )
        _es_expl_metrics_json = (
            escalation_suppress_workflow_explainer_operator_metrics_export_json(
                _es_expl_metrics,
            )
        )
        _es_expl_metrics_csv = (
            escalation_suppress_workflow_explainer_operator_metrics_table_rows_csv(
                _es_expl_metric_rows,
            )
        )
        _es_expl_m_dl_json_col, _es_expl_m_dl_csv_col = st.columns(2)
        with _es_expl_m_dl_json_col:
            st.download_button(
                label="Download escalation suppress operator metrics JSON",
                data=_es_expl_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_es_expl_metrics_slug}_{_es_expl_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_escalation_suppress_explainer_metrics_json",
            )
        with _es_expl_m_dl_csv_col:
            if _es_expl_metrics_csv:
                st.download_button(
                    label="Download escalation suppress operator metrics CSV",
                    data=_es_expl_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_es_expl_metrics_slug}_{_es_expl_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_escalation_suppress_explainer_metrics_csv",
                )
        _sup_raw = _es_expl.get("suppress_automatic_escalation_yaml_raw")
        _pol_keys = _es_expl.get("escalation_policy_yaml_top_level_keys_sample")
        _pol_keys_s = (
            "—"
            if not isinstance(_pol_keys, list) or not _pol_keys
            else ", ".join(str(x) for x in _pol_keys)
        )
        _es_rows = [
            {
                "field": "workflow YAML top-level version (int)",
                "value": "—"
                if _es_expl.get("workflow_yaml_top_level_version_int") is None
                else str(_es_expl.get("workflow_yaml_top_level_version_int")),
            },
            {
                "field": "configs/escalation/policy.yaml (on disk)",
                "value": str(_es_expl.get("escalation_policy_yaml_path_exists")),
            },
            {
                "field": "escalation policy YAML (repo-relative)",
                "value": "—"
                if not _es_expl.get("escalation_policy_yaml_relpath")
                else str(_es_expl.get("escalation_policy_yaml_relpath")),
            },
            {
                "field": "escalation policy YAML on-disk size (bytes)",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_file_bytes") is None
                else str(_es_expl.get("escalation_policy_yaml_file_bytes")),
            },
            {
                "field": "escalation policy top-level key count",
                "value": str(_es_expl.get("escalation_policy_yaml_top_level_key_count")),
            },
            {
                "field": "escalation policy top-level keys (sample, max 12)",
                "value": _pol_keys_s,
            },
            {
                "field": "policy.yaml has top-level verification mapping",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_has_verification_mapping") is None
                else str(_es_expl.get("escalation_policy_yaml_has_verification_mapping")),
            },
            {
                "field": "policy.yaml has top-level anti_deadlock mapping",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_has_anti_deadlock_mapping") is None
                else str(_es_expl.get("escalation_policy_yaml_has_anti_deadlock_mapping")),
            },
            {
                "field": "policy.yaml max_retries_per_stage (int)",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_max_retries_per_stage") is None
                else str(_es_expl.get("escalation_policy_yaml_max_retries_per_stage")),
            },
            {
                "field": "policy.yaml deadlock_escalation_after_minutes (int)",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_deadlock_escalation_after_minutes")
                is None
                else str(
                    _es_expl.get("escalation_policy_yaml_deadlock_escalation_after_minutes"),
                ),
            },
            {
                "field": "policy.yaml version (int)",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_version") is None
                else str(_es_expl.get("escalation_policy_yaml_version")),
            },
            {
                "field": "policy.yaml anti_deadlock.enabled (bool)",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_anti_deadlock_enabled") is None
                else str(_es_expl.get("escalation_policy_yaml_anti_deadlock_enabled")),
            },
            {
                "field": "policy.yaml anti_deadlock.min_progress_events (int)",
                "value": "—"
                if _es_expl.get("escalation_policy_yaml_anti_deadlock_min_progress_events")
                is None
                else str(
                    _es_expl.get("escalation_policy_yaml_anti_deadlock_min_progress_events"),
                ),
            },
            {
                "field": "escalation key in YAML",
                "value": str(_es_expl.get("escalation_yaml_key_present")),
            },
            {
                "field": "escalation block (snapshot)",
                "value": "—"
                if _es_expl.get("escalation_yaml_value") is None
                else repr(_es_expl.get("escalation_yaml_value")),
            },
            {
                "field": "suppress_automatic_escalation (raw in block)",
                "value": "—" if _sup_raw is None else repr(_sup_raw),
            },
            {
                "field": "suppress_automatic_escalation raw JSON type",
                "value": "—"
                if _es_expl.get("suppress_automatic_escalation_yaml_raw_type") is None
                else str(_es_expl.get("suppress_automatic_escalation_yaml_raw_type")),
            },
            {
                "field": "suppress_automatic_escalation_effective",
                "value": str(_es_expl.get("suppress_automatic_escalation_effective")),
            },
        ]
        st.dataframe(_es_rows, use_container_width=True, hide_index=True)
        _es_yaml_key_cap = escalation_yaml_key_present_caption(_es_expl)
        if _es_yaml_key_cap:
            st.caption(_es_yaml_key_cap)
        _es_kinds_caption = escalation_policy_yaml_top_level_kinds_caption(_es_expl)
        if _es_kinds_caption:
            st.caption(_es_kinds_caption)
        _es_kinds_rows = escalation_policy_yaml_top_level_kinds_table_rows(_es_expl)
        if _es_kinds_rows:
            _es_kinds_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _es_kinds_slug = escalation_policy_export_filename_slug()
            _es_kinds_json = escalation_policy_yaml_top_level_kinds_export_json(
                _es_kinds_rows,
            )
            _es_kinds_csv = escalation_policy_yaml_top_level_kinds_table_rows_csv(
                _es_kinds_rows,
            )
            _es_kinds_dl_json_col, _es_kinds_dl_csv_col = st.columns(2)
            with _es_kinds_dl_json_col:
                st.download_button(
                    label="Download escalation policy kinds JSON",
                    data=_es_kinds_json.encode("utf-8"),
                    file_name=f"hermes_{_es_kinds_slug}_kinds_{_es_kinds_ts}.json",
                    mime="application/json",
                    key="hermes_dl_escalation_policy_kinds_json",
                )
            with _es_kinds_dl_csv_col:
                if _es_kinds_csv:
                    st.download_button(
                        label="Download escalation policy kinds CSV",
                        data=_es_kinds_csv.encode("utf-8"),
                        file_name=f"hermes_{_es_kinds_slug}_kinds_{_es_kinds_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_escalation_policy_kinds_csv",
                    )
        _es_ver_shape = escalation_policy_yaml_verification_shape_caption(_es_expl)
        if _es_ver_shape:
            st.caption(_es_ver_shape)
        _es_ad_shape = escalation_policy_yaml_anti_deadlock_shape_caption(_es_expl)
        if _es_ad_shape:
            st.caption(_es_ad_shape)
        _es_deadlock_min_cap = escalation_policy_yaml_deadlock_minutes_caption(_es_expl)
        if _es_deadlock_min_cap:
            st.caption(_es_deadlock_min_cap)
        _es_ad_min_progress_cap = escalation_policy_yaml_anti_deadlock_min_progress_caption(
            _es_expl,
        )
        if _es_ad_min_progress_cap:
            st.caption(_es_ad_min_progress_cap)
        _es_key_count_caption = escalation_policy_yaml_key_count_caption(_es_expl)
        if _es_key_count_caption:
            st.caption(_es_key_count_caption)
        _es_policy_ver_cap = escalation_policy_yaml_version_caption(_es_expl)
        if _es_policy_ver_cap:
            st.caption(_es_policy_ver_cap)
        _es_max_retries_cap = escalation_policy_yaml_max_retries_caption(_es_expl)
        if _es_max_retries_cap:
            st.caption(_es_max_retries_cap)
        _es_keys_sample_caption = escalation_policy_yaml_keys_sample_caption(_es_expl)
        if _es_keys_sample_caption:
            st.caption(_es_keys_sample_caption)
        _es_key_count = _es_expl.get("escalation_policy_yaml_top_level_key_count")
        _es_keys_all_rows = escalation_policy_yaml_keys_all_table_rows(_es_expl)
        if (
            _es_keys_all_rows
            and type(_es_key_count) is int
            and _es_key_count > 12
        ):
            _es_keys_all_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _es_keys_all_slug = escalation_policy_export_filename_slug()
            _es_keys_all_json = escalation_policy_yaml_keys_all_export_json(
                _es_keys_all_rows,
            )
            _es_keys_all_csv = escalation_policy_yaml_keys_all_table_rows_csv(
                _es_keys_all_rows,
            )
            _es_keys_all_dl_json_col, _es_keys_all_dl_csv_col = st.columns(2)
            with _es_keys_all_dl_json_col:
                st.download_button(
                    label="Download escalation policy keys (full) JSON",
                    data=_es_keys_all_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_es_keys_all_slug}_keys_full_{_es_keys_all_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_escalation_policy_keys_full_json",
                )
            with _es_keys_all_dl_csv_col:
                if _es_keys_all_csv:
                    st.download_button(
                        label="Download escalation policy keys (full) CSV",
                        data=_es_keys_all_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_es_keys_all_slug}_keys_full_{_es_keys_all_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_escalation_policy_keys_full_csv",
                    )
        _es_relpath_caption = escalation_policy_yaml_relpath_caption(_es_expl)
        if _es_relpath_caption:
            st.caption(_es_relpath_caption)
        _es_mtime_caption = escalation_policy_yaml_mtime_caption(_es_expl)
        if _es_mtime_caption:
            st.caption(_es_mtime_caption)
        _es_age_cap = escalation_policy_yaml_age_caption(_es_expl)
        if _es_age_cap:
            st.caption(_es_age_cap)
        _es_pol_bytes_cap = escalation_policy_yaml_file_bytes_caption(_es_expl)
        if _es_pol_bytes_cap:
            st.caption(_es_pol_bytes_cap)
        _es_flag_caption = escalation_suppress_flag_caption(_es_expl)
        if _es_flag_caption:
            st.caption(_es_flag_caption)
        _es_err = _es_expl.get("load_error")
        if isinstance(_es_err, str) and _es_err.strip():
            st.warning(str(_es_err))
        _es_pol_err = _es_expl.get("escalation_policy_yaml_load_error")
        if isinstance(_es_pol_err, str) and _es_pol_err.strip():
            st.warning(
                "``configs/escalation/policy.yaml`` failed to parse: " + str(_es_pol_err),
            )
        _es_expl_rows = escalation_suppress_explainer_table_rows(_es_expl)
        if _es_expl_rows:
            _es_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _es_expl_slug = escalation_suppress_export_filename_slug()
            _es_expl_json = escalation_suppress_explainer_export_json(_es_expl)
            _es_expl_csv = escalation_suppress_explainer_table_rows_csv(_es_expl_rows)
            _es_expl_dl_json_col, _es_expl_dl_csv_col = st.columns(2)
            with _es_expl_dl_json_col:
                st.download_button(
                    label="Download escalation suppress explainer JSON",
                    data=_es_expl_json.encode("utf-8"),
                    file_name=f"hermes_{_es_expl_slug}_explainer_{_es_expl_ts}.json",
                    mime="application/json",
                    key="hermes_dl_escalation_suppress_explainer_json",
                )
            with _es_expl_dl_csv_col:
                if _es_expl_csv:
                    st.download_button(
                        label="Download escalation suppress explainer CSV",
                        data=_es_expl_csv.encode("utf-8"),
                        file_name=f"hermes_{_es_expl_slug}_explainer_{_es_expl_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_escalation_suppress_explainer_csv",
                    )
        with st.expander("Raw escalation suppress explainer JSON", expanded=False):
            st.json(_es_expl)
    with st.expander("Agent evaluator (workflow + env, fo139)", expanded=False):
        st.caption(
            "Read-only: ``agent_evaluator`` from the **same** profile stem vs "
            "``HERMES_AGENT_EVALUATOR`` — **yaml_parsed_*** is frozen YAML; "
            "**would_emit_stage_started** matches ``_maybe_emit_agent_evaluator_stage`` "
            "before create-run persona checks (kill-switch ``0``/``false``/``no``; "
            "``1``/``true``/``yes`` forces on). **persona_id** is always from the parsed "
            "workflow block when a stage would emit. PLAN_GAP §14 #15."
        )
        _ae_expl = agent_evaluator_workflow_explainer_payload(
            _iroot,
            workflow_profile=_wf_pick,
        )
        _ae_expl_metrics = agent_evaluator_workflow_explainer_operator_metrics(_ae_expl)
        _ae_expl_metrics_cap = agent_evaluator_workflow_explainer_operator_metrics_caption(
            _ae_expl_metrics,
        )
        if _ae_expl_metrics_cap:
            st.caption(_ae_expl_metrics_cap)
        _ae_expl_metric_rows = (
            agent_evaluator_workflow_explainer_operator_metrics_table_rows(_ae_expl_metrics)
        )
        if _ae_expl_metric_rows:
            st.dataframe(_ae_expl_metric_rows, use_container_width=True, hide_index=True)
        _ae_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _ae_expl_metrics_slug = (
            agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug()
        )
        _ae_expl_metrics_json = (
            agent_evaluator_workflow_explainer_operator_metrics_export_json(_ae_expl_metrics)
        )
        _ae_expl_metrics_csv = (
            agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv(
                _ae_expl_metric_rows,
            )
        )
        _ae_expl_m_dl_json_col, _ae_expl_m_dl_csv_col = st.columns(2)
        with _ae_expl_m_dl_json_col:
            st.download_button(
                label="Download agent evaluator operator metrics JSON",
                data=_ae_expl_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_ae_expl_metrics_slug}_{_ae_expl_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_agent_evaluator_explainer_metrics_json",
            )
        with _ae_expl_m_dl_csv_col:
            if _ae_expl_metrics_csv:
                st.download_button(
                    label="Download agent evaluator operator metrics CSV",
                    data=_ae_expl_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_ae_expl_metrics_slug}_{_ae_expl_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_agent_evaluator_explainer_metrics_csv",
                )
        _ae_env = _ae_expl.get("HERMES_AGENT_EVALUATOR")
        _ae_env_raw = ""
        if isinstance(_ae_env, dict):
            _ae_env_raw = str(_ae_env.get("raw", ""))
        _ae_yaml = _ae_expl.get("agent_evaluator_yaml_value")
        _ae_rows = [
            {
                "field": "workflow YAML top-level version (int)",
                "value": "—"
                if _ae_expl.get("workflow_yaml_top_level_version_int") is None
                else str(_ae_expl.get("workflow_yaml_top_level_version_int")),
            },
            {
                "field": "agent_evaluator key in YAML",
                "value": str(_ae_expl.get("agent_evaluator_yaml_key_present")),
            },
            {
                "field": "agent_evaluator block (snapshot)",
                "value": "—" if _ae_yaml is None else repr(_ae_yaml),
            },
            {
                "field": "agent_evaluator (raw value Python type)",
                "value": "—"
                if _ae_expl.get("agent_evaluator_yaml_raw_type") is None
                else str(_ae_expl.get("agent_evaluator_yaml_raw_type")),
            },
            {
                "field": "agent_evaluator (mapping string-key count)",
                "value": "—"
                if _ae_expl.get("agent_evaluator_yaml_mapping_string_key_count") is None
                else str(_ae_expl.get("agent_evaluator_yaml_mapping_string_key_count")),
            },
            {
                "field": "agent_evaluator (top-level True bool values)",
                "value": "—"
                if _ae_expl.get("agent_evaluator_yaml_true_bool_value_count") is None
                else str(_ae_expl.get("agent_evaluator_yaml_true_bool_value_count")),
            },
            {
                "field": "agent_evaluator (top-level False bool values)",
                "value": "—"
                if _ae_expl.get("agent_evaluator_yaml_false_bool_value_count") is None
                else str(_ae_expl.get("agent_evaluator_yaml_false_bool_value_count")),
            },
            {
                "field": "yaml_parsed_enabled",
                "value": str(_ae_expl.get("yaml_parsed_enabled")),
            },
            {
                "field": "yaml_parsed_persona_id",
                "value": str(_ae_expl.get("yaml_parsed_persona_id")),
            },
            {
                "field": "HERMES_AGENT_EVALUATOR (raw)",
                "value": _ae_env_raw if _ae_env_raw else "(unset)",
            },
            {
                "field": "would_emit_stage_started (env + YAML gate)",
                "value": str(_ae_expl.get("would_emit_stage_started")),
            },
        ]
        st.dataframe(_ae_rows, use_container_width=True, hide_index=True)
        _ae_env_cap = agent_evaluator_env_gate_caption(_ae_expl)
        if _ae_env_cap:
            st.caption(_ae_env_cap)
        _ae_wf_ver_cap = agent_evaluator_workflow_yaml_version_caption(_ae_expl)
        if _ae_wf_ver_cap:
            st.caption(_ae_wf_ver_cap)
        _ae_raw_type_cap = agent_evaluator_yaml_raw_type_caption(_ae_expl)
        if _ae_raw_type_cap:
            st.caption(_ae_raw_type_cap)
        _ae_true_bool_cap = agent_evaluator_yaml_true_bool_count_caption(_ae_expl)
        if _ae_true_bool_cap:
            st.caption(_ae_true_bool_cap)
        _ae_promote_cap = agent_evaluator_auto_promote_env_gate_caption(_ae_expl)
        if _ae_promote_cap:
            st.caption(_ae_promote_cap)
        _ae_create_cap = agent_evaluator_auto_create_env_gate_caption(_ae_expl)
        if _ae_create_cap:
            st.caption(_ae_create_cap)
        _ae_yaml_key_cap = agent_evaluator_yaml_key_present_caption(_ae_expl)
        if _ae_yaml_key_cap:
            st.caption(_ae_yaml_key_cap)
        _ae_persona_cap = agent_evaluator_persona_id_caption(_ae_expl)
        if _ae_persona_cap:
            st.caption(_ae_persona_cap)
        _ae_enabled_cap = agent_evaluator_yaml_parsed_enabled_caption(_ae_expl)
        if _ae_enabled_cap:
            st.caption(_ae_enabled_cap)
        _ae_llm_cap = agent_evaluator_llm_evaluation_enabled_caption(_ae_expl)
        if _ae_llm_cap:
            st.caption(_ae_llm_cap)
        _ae_would_cap = agent_evaluator_would_emit_caption(_ae_expl)
        if _ae_would_cap:
            st.caption(_ae_would_cap)
        _ae_err = _ae_expl.get("load_error")
        if isinstance(_ae_err, str) and _ae_err.strip():
            st.warning(str(_ae_err))
        _ae_expl_rows = agent_evaluator_explainer_table_rows(_ae_expl)
        if _ae_expl_rows:
            _ae_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ae_expl_slug = agent_evaluator_export_filename_slug()
            _ae_expl_json = agent_evaluator_explainer_export_json(_ae_expl)
            _ae_expl_csv = agent_evaluator_explainer_table_rows_csv(_ae_expl_rows)
            _ae_expl_dl_json_col, _ae_expl_dl_csv_col = st.columns(2)
            with _ae_expl_dl_json_col:
                st.download_button(
                    label="Download agent evaluator explainer JSON",
                    data=_ae_expl_json.encode("utf-8"),
                    file_name=f"hermes_{_ae_expl_slug}_explainer_{_ae_expl_ts}.json",
                    mime="application/json",
                    key="hermes_dl_agent_evaluator_explainer_json",
                )
            with _ae_expl_dl_csv_col:
                if _ae_expl_csv:
                    st.download_button(
                        label="Download agent evaluator explainer CSV",
                        data=_ae_expl_csv.encode("utf-8"),
                        file_name=f"hermes_{_ae_expl_slug}_explainer_{_ae_expl_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_agent_evaluator_explainer_csv",
                    )
        with st.expander("Raw agent evaluator explainer JSON", expanded=False):
            st.json(_ae_expl)
    st.text_area(
        "Optional pasted ``integrator_gate`` YAML (full workflow with key, or flat mapping)",
        height=120,
        placeholder="integrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n",
        key="hermes_integrator_paste_yaml",
    )
    with st.expander("Integrator thresholds & gate emission (fo133)", expanded=False):
        st.caption(
            "Read-only: **pipeline** ``min_score_to_pass`` resolution (matches gate emission) vs "
            "**Streamlit preview** (pasted fragment can change preview only), plus whether a "
            "``gate.decision.emitted`` would be written given ``HERMES_EMIT_INTEGRATOR_GATE``, "
            "``configs/integrator/thresholds.yaml`` **enabled**, and workflow "
            "``integrator_gate.enabled``."
        )
        _thr_payload = integrator_threshold_explainer_payload(
            _iroot,
            workflow_profile=_wf_pick,
            pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
        )
        _thr_expl_metrics = integrator_threshold_explainer_operator_metrics(_thr_payload)
        _thr_expl_metrics_cap = integrator_threshold_explainer_operator_metrics_caption(
            _thr_expl_metrics,
        )
        if _thr_expl_metrics_cap:
            st.caption(_thr_expl_metrics_cap)
        _thr_expl_metric_rows = integrator_threshold_explainer_operator_metrics_table_rows(
            _thr_expl_metrics,
        )
        if _thr_expl_metric_rows:
            st.dataframe(_thr_expl_metric_rows, use_container_width=True, hide_index=True)
        _thr_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _thr_expl_metrics_slug = (
            integrator_threshold_explainer_operator_metrics_export_filename_slug()
        )
        _thr_expl_metrics_json = integrator_threshold_explainer_operator_metrics_export_json(
            _thr_expl_metrics,
        )
        _thr_expl_metrics_csv = (
            integrator_threshold_explainer_operator_metrics_table_rows_csv(
                _thr_expl_metric_rows,
            )
        )
        _thr_expl_m_dl_json_col, _thr_expl_m_dl_csv_col = st.columns(2)
        with _thr_expl_m_dl_json_col:
            st.download_button(
                label="Download integrator threshold operator metrics JSON",
                data=_thr_expl_metrics_json.encode("utf-8"),
                file_name=f"hermes_{_thr_expl_metrics_slug}_{_thr_expl_metrics_ts}.json",
                mime="application/json",
                key="hermes_dl_integrator_threshold_explainer_metrics_json",
            )
        with _thr_expl_m_dl_csv_col:
            if _thr_expl_metrics_csv:
                st.download_button(
                    label="Download integrator threshold operator metrics CSV",
                    data=_thr_expl_metrics_csv.encode("utf-8"),
                    file_name=f"hermes_{_thr_expl_metrics_slug}_{_thr_expl_metrics_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_integrator_threshold_explainer_metrics_csv",
                )
        _thr_emit_cap = integrator_threshold_gate_emission_caption(_thr_payload)
        if _thr_emit_cap:
            st.caption(_thr_emit_cap)
        _thr_min_cap = integrator_threshold_min_score_agreement_caption(_thr_payload)
        if _thr_min_cap:
            st.caption(_thr_min_cap)
        _thr_tags_cap = integrator_threshold_project_tags_caption(_thr_payload)
        if _thr_tags_cap:
            st.caption(_thr_tags_cap)
        _thr_paste_cap = integrator_threshold_paste_parse_caption(_thr_payload)
        if _thr_paste_cap:
            st.caption(_thr_paste_cap)
        _thr_thr_ver_cap = integrator_threshold_thresholds_yaml_version_caption(
            _thr_payload,
        )
        if _thr_thr_ver_cap:
            st.caption(_thr_thr_ver_cap)
        _thr_ty = _thr_payload.get("thresholds_yaml")
        _thr_ver = (
            "—"
            if not isinstance(_thr_ty, dict)
            or _thr_ty.get("top_level_version_int") is None
            else str(_thr_ty.get("top_level_version_int"))
        )
        _thr_bytes = (
            "—"
            if not isinstance(_thr_ty, dict)
            or _thr_ty.get("thresholds_yaml_file_bytes") is None
            else str(_thr_ty.get("thresholds_yaml_file_bytes"))
        )
        _thr_rows = [
            {
                "field": "configs/integrator/thresholds.yaml version (int)",
                "value": _thr_ver,
            },
            {
                "field": "configs/integrator/thresholds.yaml on-disk size (bytes)",
                "value": _thr_bytes,
            },
            {
                "field": "pipeline effective min_score_to_pass",
                "value": str(_thr_payload.get("pipeline_effective_min_score_to_pass")),
            },
            {
                "field": "streamlit preview effective min_score_to_pass",
                "value": str(_thr_payload.get("streamlit_preview_effective_min_score_to_pass")),
            },
            {
                "field": "would_emit integrator gate event",
                "value": str(
                    _thr_payload.get("gate_event_emission", {}).get(
                        "would_emit_integrator_gate_event",
                    ),
                ),
            },
            {
                "field": "workflow integrator_gate project_tags list length",
                "value": "—"
                if _thr_payload.get("workflow_integrator_gate", {}).get(
                    "project_tags_list_length",
                )
                is None
                else str(
                    _thr_payload.get("workflow_integrator_gate", {}).get(
                        "project_tags_list_length",
                    ),
                ),
            },
        ]
        st.dataframe(_thr_rows, use_container_width=True, hide_index=True)
        _thr_expl_rows = integrator_threshold_explainer_table_rows(_thr_payload)
        if _thr_expl_rows:
            _thr_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _thr_expl_slug = integrator_threshold_export_filename_slug()
            _thr_expl_json = integrator_threshold_explainer_export_json(_thr_payload)
            _thr_expl_csv = integrator_threshold_explainer_table_rows_csv(_thr_expl_rows)
            _thr_expl_dl_json_col, _thr_expl_dl_csv_col = st.columns(2)
            with _thr_expl_dl_json_col:
                st.download_button(
                    label="Download integrator threshold explainer JSON",
                    data=_thr_expl_json.encode("utf-8"),
                    file_name=f"hermes_{_thr_expl_slug}_explainer_{_thr_expl_ts}.json",
                    mime="application/json",
                    key="hermes_dl_integrator_threshold_explainer_json",
                )
            with _thr_expl_dl_csv_col:
                if _thr_expl_csv:
                    st.download_button(
                        label="Download integrator threshold explainer CSV",
                        data=_thr_expl_csv.encode("utf-8"),
                        file_name=f"hermes_{_thr_expl_slug}_explainer_{_thr_expl_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_integrator_threshold_explainer_csv",
                    )
        with st.expander("Raw threshold explainer JSON", expanded=False):
            st.json(_thr_payload)
    st.text_input(
        "Bundle id (catalog ``bundles[].id``)",
        value="auth-rbac-starter",
        key="hermes_integrator_bundle_id",
    )
    st.text_area(
        "Synthetic ``tags`` JSON array (optional; overrides workflow ``project_tags`` when set)",
        value="[]",
        height=68,
        key="hermes_integrator_tags_json",
    )
    if st.button("Run integrator preview", key="hermes_integrator_preview_btn"):
        try:
            st.session_state[_LAST_INTEGRATOR_PREVIEW] = integrator_preview_payload(
                _iroot,
                workflow_profile=_wf_pick,
                pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                bundle_id=str(st.session_state.get("hermes_integrator_bundle_id", "")),
                synthetic_tags_json=str(
                    st.session_state.get("hermes_integrator_tags_json", "[]"),
                ),
            )
        except (OSError, ValueError) as _ix_exc:
            st.session_state.pop(_LAST_INTEGRATOR_PREVIEW, None)
            st.error(f"Preview failed: {_ix_exc}")
    _ip = st.session_state.get(_LAST_INTEGRATOR_PREVIEW)
    if isinstance(_ip, dict):
        _rows = [
            {"field": "workflow_profile", "value": str(_ip.get("workflow_profile"))},
            {
                "field": "disk integrator_gate.enabled",
                "value": str(_ip.get("disk_integrator_gate_enabled")),
            },
            {
                "field": "thresholds.yaml enabled (catalog)",
                "value": str(_ip.get("catalog_thresholds_enabled")),
            },
            {
                "field": "pasted enabled (preview only)",
                "value": str(_ip.get("pasted_enabled_preview")),
            },
            {
                "field": "effective min_score_to_pass",
                "value": str(_ip.get("effective_min_score_to_pass")),
            },
            {"field": "bundle_id", "value": str(_ip.get("bundle_id"))},
            {"field": "score_fit", "value": str(_ip.get("score_fit"))},
            {"field": "passes_gate", "value": str(_ip.get("passes_gate"))},
        ]
        _iperr = _ip.get("validation_errors")
        if isinstance(_iperr, list) and _iperr:
            for _e in _iperr:
                st.warning(str(_e))
        st.dataframe(_rows, use_container_width=True, hide_index=True)
        with st.expander("Raw integrator preview JSON", expanded=False):
            st.json(_ip)
    _integrator_write_ok = workflow_yaml_write_enabled()
    st.caption(
        "Workflow YAML disk writes (**fo132** ``integrator_gate``, "
        "**fo140** ``agent_evaluator``, **§14 #13** full-profile merge): "
        f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}`` is "
        f"{'**enabled**' if _integrator_write_ok else '**disabled** — no disk writes'}."
    )
    st.text_input(
        "Confirm profile stem for disk apply (type exactly the selected workflow profile)",
        key="hermes_integrator_confirm_profile",
    )
    with st.expander("Apply integrator_gate to disk (fo132)", expanded=False):
        st.caption(
            "Merges the pasted ``integrator_gate`` block into the **selected** workflow profile "
            "via ``atomic_write_yaml`` (other YAML keys preserved). Requires "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on) in the Streamlit process env."
        )
        if st.button("Dry-run merge (no write)", key="hermes_integrator_dry_run_btn"):
            if not _wf_pick:
                st.error("Select a workflow profile first.")
            else:
                _mrg, _b4, _af, _merr = prepare_integrator_gate_apply(
                    _iroot,
                    profile_stem=str(_wf_pick),
                    pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                )
                st.session_state[_LAST_INTEGRATOR_MERGE_DRY] = {
                    "profile": str(_wf_pick),
                    "before_gate": _b4,
                    "after_gate": _af,
                    "errors": _merr,
                    "merged_ok": _mrg is not None,
                }
        _dry = st.session_state.get(_LAST_INTEGRATOR_MERGE_DRY)
        if isinstance(_dry, dict) and _dry.get("merged_ok"):
            st.caption("Dry-run ``integrator_gate`` (before → after)")
            _c1, _c2 = st.columns(2)
            with _c1:
                st.json(_dry.get("before_gate"))
            with _c2:
                st.json(_dry.get("after_gate"))
        elif isinstance(_dry, dict) and _dry.get("errors"):
            for _me in _dry["errors"]:
                st.warning(str(_me))
        _confirm = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
        _can_apply = bool(
            _integrator_write_ok and _wf_pick and _confirm and _confirm == str(_wf_pick).strip(),
        )
        if st.button(
            "Apply merge to disk",
            disabled=not _can_apply,
            key="hermes_integrator_apply_disk_btn",
        ):
            _ok_ap, _merged_doc, _ap_errs = apply_integrator_gate_yaml(
                _iroot,
                profile_stem=str(_wf_pick),
                pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                confirm_profile_stem=_confirm,
            )
            if _ok_ap:
                st.success("Wrote workflow YAML.")
                st.session_state.pop(_LAST_INTEGRATOR_MERGE_DRY, None)
            else:
                for _ap_e in _ap_errs:
                    st.error(str(_ap_e))
    with st.expander("Apply agent_evaluator to disk (fo140)", expanded=False):
        st.caption(
            "Merges the pasted ``agent_evaluator`` block into the **selected** workflow profile "
            "via ``atomic_write_yaml`` (other YAML keys preserved). Accepts a full workflow root "
            "with ``agent_evaluator:`` or a flat ``enabled`` / ``persona_id`` map. Requires "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on) in the Streamlit process env. "
            "Uses the **same** profile-stem confirmation field as **fo132** above."
        )
        st.text_area(
            "Optional pasted ``agent_evaluator`` YAML (full workflow with key, or flat mapping)",
            height=120,
            placeholder="agent_evaluator:\n  enabled: true\n  persona_id: default\n",
            key="hermes_integrator_paste_agent_evaluator_yaml",
        )
        if st.button("Dry-run merge (no write)", key="hermes_integrator_ae_dry_run_btn"):
            if not _wf_pick:
                st.error("Select a workflow profile first.")
            else:
                _mrg_ae, _b4_ae, _af_ae, _merr_ae = prepare_agent_evaluator_apply(
                    _iroot,
                    profile_stem=str(_wf_pick),
                    pasted_yaml=str(
                        st.session_state.get("hermes_integrator_paste_agent_evaluator_yaml", ""),
                    ),
                )
                st.session_state[_LAST_AGENT_EVALUATOR_MERGE_DRY] = {
                    "profile": str(_wf_pick),
                    "before_ae": _b4_ae,
                    "after_ae": _af_ae,
                    "errors": _merr_ae,
                    "merged_ok": _mrg_ae is not None,
                }
        _dry_ae = st.session_state.get(_LAST_AGENT_EVALUATOR_MERGE_DRY)
        if isinstance(_dry_ae, dict) and _dry_ae.get("merged_ok"):
            st.caption("Dry-run ``agent_evaluator`` (before → after)")
            _ac1, _ac2 = st.columns(2)
            with _ac1:
                st.json(_dry_ae.get("before_ae"))
            with _ac2:
                st.json(_dry_ae.get("after_ae"))
        elif isinstance(_dry_ae, dict) and _dry_ae.get("errors"):
            for _me_ae in _dry_ae["errors"]:
                st.warning(str(_me_ae))
        _confirm_ae = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
        _can_apply_ae = bool(
            _integrator_write_ok
            and _wf_pick
            and _confirm_ae
            and _confirm_ae == str(_wf_pick).strip(),
        )
        if st.button(
            "Apply agent_evaluator merge to disk",
            disabled=not _can_apply_ae,
            key="hermes_integrator_ae_apply_disk_btn",
        ):
            _ok_ae, _merged_ae, _ap_errs_ae = apply_agent_evaluator_yaml(
                _iroot,
                profile_stem=str(_wf_pick),
                pasted_yaml=str(
                    st.session_state.get("hermes_integrator_paste_agent_evaluator_yaml", ""),
                ),
                confirm_profile_stem=_confirm_ae,
            )
            if _ok_ae:
                st.success("Wrote workflow YAML.")
                st.session_state.pop(_LAST_AGENT_EVALUATOR_MERGE_DRY, None)
            else:
                for _ap_e_ae in _ap_errs_ae:
                    st.error(str(_ap_e_ae))
    with st.expander("Apply full workflow profile to disk (§14 #13)", expanded=False):
        st.caption(
            "Paste a **full** workflow root (same allowed top-level keys as shipped "
            "``configs/workflows/*.yaml`` profiles). Validates keys + ``integrator_gate`` / "
            "``agent_evaluator`` blocks; **shallow-merges** each pasted top-level key over the "
            "on-disk file (keys you omit from the paste are unchanged). Requires "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on). Uses the **same** "
            "profile-stem confirmation field as **fo132** / **fo140** above."
        )
        st.text_area(
            "Pasted full workflow YAML",
            height=260,
            placeholder="version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n",
            key="hermes_full_workflow_paste_yaml",
        )
        if st.button("Dry-run full merge (no write)", key="hermes_full_workflow_dry_run_btn"):
            if not _wf_pick:
                st.error("Select a workflow profile first.")
            else:
                _mrg_fw, _b4_fw, _merr_fw = prepare_full_workflow_apply(
                    _iroot,
                    profile_stem=str(_wf_pick),
                    pasted_yaml=str(
                        st.session_state.get("hermes_full_workflow_paste_yaml", ""),
                    ),
                )
                st.session_state[_LAST_FULL_WORKFLOW_MERGE_DRY] = {
                    "profile": str(_wf_pick),
                    "before_disk": _b4_fw,
                    "merged": _mrg_fw,
                    "errors": _merr_fw,
                    "merged_ok": _mrg_fw is not None,
                }
        _dry_fw = st.session_state.get(_LAST_FULL_WORKFLOW_MERGE_DRY)
        if isinstance(_dry_fw, dict) and _dry_fw.get("merged_ok"):
            st.caption("Dry-run full profile (on-disk before vs merged preview)")
            _b4_d = _dry_fw.get("before_disk")
            _mrg_d = _dry_fw.get("merged")
            _paste_live, _ = parse_full_workflow_yaml_paste(
                str(st.session_state.get("hermes_full_workflow_paste_yaml", "")),
            )
            _diff_fw = (
                full_workflow_merge_diff(
                    _b4_d,
                    _mrg_d,
                    pasted_root=_paste_live if isinstance(_paste_live, dict) else None,
                )
                if isinstance(_b4_d, dict) and isinstance(_mrg_d, dict)
                else None
            )
            with st.expander("Top-level merge diff summary", expanded=False):
                if isinstance(_diff_fw, dict) and _diff_fw.get("error"):
                    st.warning(str(_diff_fw["error"]))
                elif isinstance(_diff_fw, dict):
                    st.dataframe(
                        [
                            {
                                "bucket": "added_top_level",
                                "keys": ", ".join(_diff_fw.get("added_top_level_keys", []))
                                or "—",
                            },
                            {
                                "bucket": "removed_top_level",
                                "keys": ", ".join(_diff_fw.get("removed_top_level_keys", []))
                                or "—",
                            },
                            {
                                "bucket": "changed_top_level",
                                "keys": ", ".join(_diff_fw.get("changed_top_level_keys", []))
                                or "—",
                            },
                            {
                                "bucket": "unchanged_top_level",
                                "keys": ", ".join(_diff_fw.get("unchanged_top_level_keys", []))
                                or "—",
                            },
                            {
                                "bucket": "disk_only_top_level",
                                "keys": ", ".join(_diff_fw.get("disk_only_top_level_keys", []))
                                or "—",
                            },
                            {
                                "bucket": "paste_only_top_level",
                                "keys": ", ".join(_diff_fw.get("paste_only_top_level_keys", []))
                                or "—",
                            },
                            {
                                "bucket": "pasted_top_level",
                                "keys": ", ".join(_diff_fw.get("pasted_top_level_keys", []))
                                or "—",
                            },
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                    _overview_fw = full_workflow_merge_overview_caption(_diff_fw)
                    if _overview_fw:
                        st.caption(_overview_fw)
                    _churn_n_fw = full_workflow_merge_top_level_churn_count_caption(_diff_fw)
                    if _churn_n_fw:
                        st.caption(_churn_n_fw)
                    _fw_fp = full_workflow_merge_diff_audit_fingerprint_caption(_diff_fw)
                    if _fw_fp:
                        st.caption(_fw_fp)
                    _unchurn_uc = full_workflow_merge_unchanged_with_churn_caption(_diff_fw)
                    if _unchurn_uc:
                        st.caption(_unchurn_uc)
                    _unchanged_fw = full_workflow_merge_unchanged_top_level_caption(
                        _diff_fw,
                    )
                    if _unchanged_fw:
                        st.caption(_unchanged_fw)
                    _changed_fw = full_workflow_merge_changed_top_level_caption(
                        _diff_fw,
                    )
                    if _changed_fw:
                        st.caption(_changed_fw)
                    _added_fw = full_workflow_merge_added_top_level_caption(
                        _diff_fw,
                    )
                    if _added_fw:
                        st.caption(_added_fw)
                    _removed_fw = full_workflow_merge_removed_top_level_caption(
                        _diff_fw,
                    )
                    if _removed_fw:
                        st.caption(_removed_fw)
                    _disk_only_fw = full_workflow_merge_disk_only_top_level_caption(
                        _diff_fw,
                    )
                    if _disk_only_fw:
                        st.caption(_disk_only_fw)
                    _paste_only_fw = full_workflow_merge_paste_only_top_level_caption(
                        _diff_fw,
                    )
                    if _paste_only_fw:
                        st.caption(_paste_only_fw)
                    _pasted_top_fw = full_workflow_merge_pasted_top_level_caption(_diff_fw)
                    if _pasted_top_fw:
                        st.caption(_pasted_top_fw)
                    _att_fw = full_workflow_merge_attention_rows(_diff_fw)
                    if _att_fw:
                        _att_fw_metrics = full_workflow_merge_attention_operator_metrics(_diff_fw)
                        _att_fw_metrics_cap = (
                            full_workflow_merge_attention_operator_metrics_caption(
                                _att_fw_metrics,
                            )
                        )
                        if _att_fw_metrics_cap:
                            st.caption(_att_fw_metrics_cap)
                        _att_fw_metric_rows = (
                            full_workflow_merge_attention_operator_metrics_table_rows(
                                _att_fw_metrics,
                            )
                        )
                        if _att_fw_metric_rows:
                            st.dataframe(
                                _att_fw_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                        _att_fw_metrics_ts = datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ",
                        )
                        _att_fw_metrics_slug = (
                            full_workflow_merge_attention_operator_metrics_export_filename_slug()
                        )
                        _att_fw_metrics_json = (
                            full_workflow_merge_attention_operator_metrics_export_json(
                                _att_fw_metrics,
                            )
                        )
                        _att_fw_metrics_csv = (
                            full_workflow_merge_attention_operator_metrics_table_rows_csv(
                                _att_fw_metric_rows,
                            )
                        )
                        _att_fw_m_dl_json_col, _att_fw_m_dl_csv_col = st.columns(2)
                        with _att_fw_m_dl_json_col:
                            st.download_button(
                                label="Download merge attention operator metrics JSON",
                                data=_att_fw_metrics_json.encode("utf-8"),
                                file_name=(
                                    f"hermes_{_att_fw_metrics_slug}_{_att_fw_metrics_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_full_workflow_merge_attention_metrics_json",
                            )
                        with _att_fw_m_dl_csv_col:
                            if _att_fw_metrics_csv:
                                st.download_button(
                                    label="Download merge attention operator metrics CSV",
                                    data=_att_fw_metrics_csv.encode("utf-8"),
                                    file_name=(
                                        f"hermes_{_att_fw_metrics_slug}_"
                                        f"{_att_fw_metrics_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_full_workflow_merge_attention_metrics_csv",
                                )
                        st.caption("Full-profile merge attention (read-only hints; §14 #13).")
                        st.dataframe(_att_fw, use_container_width=True, hide_index=True)
                        _att_fw_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _att_fw_slug = full_workflow_merge_attention_export_filename_slug()
                        _att_fw_json = full_workflow_merge_attention_export_json(_att_fw)
                        _att_fw_csv = full_workflow_merge_attention_table_rows_csv(_att_fw)
                        _att_fw_dl_json_col, _att_fw_dl_csv_col = st.columns(2)
                        with _att_fw_dl_json_col:
                            st.download_button(
                                label="Download full-workflow merge attention JSON",
                                data=_att_fw_json.encode("utf-8"),
                                file_name=f"hermes_{_att_fw_slug}_{_att_fw_ts}.json",
                                mime="application/json",
                                key="hermes_dl_full_workflow_merge_attention_json",
                            )
                        with _att_fw_dl_csv_col:
                            if _att_fw_csv:
                                st.download_button(
                                    label="Download full-workflow merge attention CSV",
                                    data=_att_fw_csv.encode("utf-8"),
                                    file_name=f"hermes_{_att_fw_slug}_{_att_fw_ts}.csv",
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_full_workflow_merge_attention_csv",
                                )
                    _sub_fw = _diff_fw.get("subtree_field_diffs")
                    if isinstance(_sub_fw, dict) and _sub_fw:
                        st.caption(
                            "Shallow field churn (``integrator_gate`` / ``agent_evaluator`` only; "
                            "see raw JSON for before/after values)."
                        )
                        _sub_overview_fw = full_workflow_merge_subtree_overview_caption(
                            _diff_fw,
                        )
                        if _sub_overview_fw:
                            st.caption(_sub_overview_fw)
                        _sub_changed_fields_fw = (
                            full_workflow_merge_subtree_changed_fields_caption(_diff_fw)
                        )
                        if _sub_changed_fields_fw:
                            st.caption(_sub_changed_fields_fw)
                        _sub_added_fields_fw = full_workflow_merge_subtree_added_fields_caption(
                            _diff_fw,
                        )
                        if _sub_added_fields_fw:
                            st.caption(_sub_added_fields_fw)
                        _sub_removed_fields_fw = (
                            full_workflow_merge_subtree_removed_fields_caption(_diff_fw)
                        )
                        if _sub_removed_fields_fw:
                            st.caption(_sub_removed_fields_fw)
                        _rows_sub: list[dict[str, str]] = []
                        for _name, _blk in _sub_fw.items():
                            if not isinstance(_blk, dict):
                                continue
                            _rows_sub.append(
                                {
                                    "subtree": str(_name),
                                    "added": ", ".join(_blk.get("added_keys", [])) or "—",
                                    "removed": ", ".join(_blk.get("removed_keys", [])) or "—",
                                    "changed": ", ".join(_blk.get("changed_keys", [])) or "—",
                                    "unchanged": ", ".join(_blk.get("unchanged_keys", [])) or "—",
                                },
                            )
                        if _rows_sub:
                            st.dataframe(_rows_sub, use_container_width=True, hide_index=True)
                else:
                    st.caption("No diff payload (unexpected).")
            if isinstance(_diff_fw, dict) and not _diff_fw.get("error"):
                _diff_fw_metrics = full_workflow_merge_diff_operator_metrics(_diff_fw)
                _diff_fw_metrics_cap = full_workflow_merge_diff_operator_metrics_caption(
                    _diff_fw_metrics,
                )
                if _diff_fw_metrics_cap:
                    st.caption(_diff_fw_metrics_cap)
                _diff_fw_metric_rows = full_workflow_merge_diff_operator_metrics_table_rows(
                    _diff_fw_metrics,
                )
                if _diff_fw_metric_rows:
                    st.dataframe(
                        _diff_fw_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                _diff_fw_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _diff_fw_metrics_slug = (
                    full_workflow_merge_diff_operator_metrics_export_filename_slug()
                )
                _diff_fw_metrics_json = full_workflow_merge_diff_operator_metrics_export_json(
                    _diff_fw_metrics,
                )
                _diff_fw_metrics_csv = (
                    full_workflow_merge_diff_operator_metrics_table_rows_csv(
                        _diff_fw_metric_rows,
                    )
                )
                _diff_fw_m_dl_json_col, _diff_fw_m_dl_csv_col = st.columns(2)
                with _diff_fw_m_dl_json_col:
                    st.download_button(
                        label="Download merge diff operator metrics JSON",
                        data=_diff_fw_metrics_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_diff_fw_metrics_slug}_{_diff_fw_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_full_workflow_merge_diff_metrics_json",
                    )
                with _diff_fw_m_dl_csv_col:
                    if _diff_fw_metrics_csv:
                        st.download_button(
                            label="Download merge diff operator metrics CSV",
                            data=_diff_fw_metrics_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_diff_fw_metrics_slug}_{_diff_fw_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_full_workflow_merge_diff_metrics_csv",
                        )
                _diff_fw_rows = full_workflow_merge_diff_table_rows(_diff_fw)
                if _diff_fw_rows:
                    _diff_fw_slug = full_workflow_merge_diff_export_filename_slug()
                    _diff_fw_json = full_workflow_merge_diff_export_json(_diff_fw)
                    _diff_fw_csv = full_workflow_merge_diff_table_rows_csv(_diff_fw_rows)
                    _diff_fw_dl_json_col, _diff_fw_dl_csv_col = st.columns(2)
                    with _diff_fw_dl_json_col:
                        st.download_button(
                            label="Download full-workflow merge diff JSON",
                            data=_diff_fw_json.encode("utf-8"),
                            file_name=(
                                f"hermes_{_diff_fw_slug}_"
                                f"{_diff_fw_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_full_workflow_merge_diff_json",
                        )
                    with _diff_fw_dl_csv_col:
                        if _diff_fw_csv:
                            st.download_button(
                                label="Download full-workflow merge diff CSV",
                                data=_diff_fw_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_{_diff_fw_slug}_"
                                    f"{_diff_fw_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_full_workflow_merge_diff_csv",
                            )
            with st.expander("Raw full-workflow merge diff JSON", expanded=False):
                st.json(_diff_fw if isinstance(_diff_fw, dict) else {})
            _fc1, _fc2 = st.columns(2)
            with _fc1:
                st.json(_dry_fw.get("before_disk"))
            with _fc2:
                st.json(_dry_fw.get("merged"))
            with st.expander("Raw merged full-workflow JSON", expanded=False):
                st.json(_dry_fw.get("merged"))
        elif isinstance(_dry_fw, dict) and _dry_fw.get("errors"):
            for _me_fw in _dry_fw["errors"]:
                st.warning(str(_me_fw))
        _confirm_fw = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
        _can_apply_fw = bool(
            _integrator_write_ok
            and _wf_pick
            and _confirm_fw
            and _confirm_fw == str(_wf_pick).strip(),
        )
        if st.button(
            "Apply full workflow merge to disk",
            disabled=not _can_apply_fw,
            key="hermes_full_workflow_apply_disk_btn",
        ):
            _ok_fw, _merged_fw, _ap_errs_fw = apply_full_workflow_yaml(
                _iroot,
                profile_stem=str(_wf_pick),
                pasted_yaml=str(
                    st.session_state.get("hermes_full_workflow_paste_yaml", ""),
                ),
                confirm_profile_stem=_confirm_fw,
            )
            if _ok_fw:
                st.success("Wrote workflow YAML.")
                st.session_state.pop(_LAST_FULL_WORKFLOW_MERGE_DRY, None)
            else:
                for _ap_e_fw in _ap_errs_fw:
                    st.error(str(_ap_e_fw))
with st.expander("Persona shelves (local repo)", expanded=False):
    st.caption(
        "Read-only: same ``PersonaShelf`` + ``configs/personas/shelves.yaml`` shape as "
        "**GET /v1/personas** (``HERMES_REPO_ROOT`` / frozen repo root). No API call.",
    )
    st.caption(persona_catalog_taxonomy_scope_frozen_caption())
    _proot = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
    st.caption(f"Effective repo root: `{_proot}`")
    _cp_sum = critique_pairings_operator_summary(_proot)
    _cp_metrics = critique_pairings_operator_summary_operator_metrics(_cp_sum)
    _cp_metrics_cap = critique_pairings_operator_summary_operator_metrics_caption(_cp_metrics)
    if _cp_metrics_cap:
        st.caption(_cp_metrics_cap)
    _cp_metric_rows = critique_pairings_operator_summary_operator_metrics_table_rows(
        _cp_metrics,
    )
    if _cp_metric_rows:
        st.dataframe(_cp_metric_rows, use_container_width=True, hide_index=True)
    _cp_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _cp_metrics_slug = critique_pairings_operator_summary_operator_metrics_export_filename_slug()
    _cp_metrics_json = critique_pairings_operator_summary_operator_metrics_export_json(
        _cp_metrics,
    )
    _cp_metrics_csv = critique_pairings_operator_summary_operator_metrics_table_rows_csv(
        _cp_metric_rows,
    )
    _cp_m_dl_json_col, _cp_m_dl_csv_col = st.columns(2)
    with _cp_m_dl_json_col:
        st.download_button(
            label="Download critique pairings operator metrics JSON",
            data=_cp_metrics_json.encode("utf-8"),
            file_name=f"hermes_{_cp_metrics_slug}_{_cp_metrics_ts}.json",
            mime="application/json",
            key="hermes_dl_critique_pairings_operator_metrics_json",
        )
    with _cp_m_dl_csv_col:
        if _cp_metrics_csv:
            st.download_button(
                label="Download critique pairings operator metrics CSV",
                data=_cp_metrics_csv.encode("utf-8"),
                file_name=f"hermes_{_cp_metrics_slug}_{_cp_metrics_ts}.csv",
                mime="text/csv; charset=utf-8",
                key="hermes_dl_critique_pairings_operator_metrics_csv",
            )
    if _cp_sum.get("has_critique_pairings_yaml"):
        st.caption(
            "Read-only **critique_pairings.yaml**: "
            f"version `{_cp_sum.get('version')!r}`, "
            f"{_cp_sum.get('producer_taxonomy_key_count')} producer taxonomy key(s)."
        )
        _cp_total_cap = persona_catalog_critique_pairings_total_caption(_cp_sum)
        if _cp_total_cap:
            st.caption(_cp_total_cap)
        sample = _cp_sum.get("producer_taxonomy_keys_sample") or []
        if isinstance(sample, list) and sample:
            vis = ", ".join(f"``{x}``" for x in sample if isinstance(x, str) and x.strip())
            if vis:
                st.caption("Sample producer keys: " + vis + ".")
        _cp_prod_rows = critique_pairings_producer_keys_table_rows(_cp_sum)
        if _cp_prod_rows:
            _cp_prod_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _cp_prod_slug = critique_pairings_export_filename_slug()
            _cp_prod_json = critique_pairings_producer_keys_export_json(_cp_prod_rows)
            _cp_prod_csv = critique_pairings_producer_keys_table_rows_csv(_cp_prod_rows)
            _cp_prod_dl_json_col, _cp_prod_dl_csv_col = st.columns(2)
            with _cp_prod_dl_json_col:
                st.download_button(
                    label="Download critique pairings producer keys JSON",
                    data=_cp_prod_json.encode("utf-8"),
                    file_name=f"hermes_{_cp_prod_slug}_producer_keys_{_cp_prod_ts}.json",
                    mime="application/json",
                    key="hermes_dl_critique_pairings_producer_keys_json",
                )
            with _cp_prod_dl_csv_col:
                if _cp_prod_csv:
                    st.download_button(
                        label="Download critique pairings producer keys CSV",
                        data=_cp_prod_csv.encode("utf-8"),
                        file_name=f"hermes_{_cp_prod_slug}_producer_keys_{_cp_prod_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_producer_keys_csv",
                    )
        _cp_prod_key_count = _cp_sum.get("producer_taxonomy_key_count")
        _cp_prod_all_rows = critique_pairings_producer_keys_all_table_rows(_cp_sum)
        if (
            _cp_prod_all_rows
            and type(_cp_prod_key_count) is int
            and _cp_prod_key_count > 12
        ):
            _cp_prod_all_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _cp_prod_all_slug = critique_pairings_export_filename_slug()
            _cp_prod_all_json = critique_pairings_producer_keys_all_export_json(
                _cp_prod_all_rows,
            )
            _cp_prod_all_csv = critique_pairings_producer_keys_all_table_rows_csv(
                _cp_prod_all_rows,
            )
            _cp_prod_all_dl_json_col, _cp_prod_all_dl_csv_col = st.columns(2)
            with _cp_prod_all_dl_json_col:
                st.download_button(
                    label="Download critique pairings producer keys (full) JSON",
                    data=_cp_prod_all_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_cp_prod_all_slug}_producer_keys_full_{_cp_prod_all_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_critique_pairings_producer_keys_full_json",
                )
            with _cp_prod_all_dl_csv_col:
                if _cp_prod_all_csv:
                    st.download_button(
                        label="Download critique pairings producer keys (full) CSV",
                        data=_cp_prod_all_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_cp_prod_all_slug}_producer_keys_full_{_cp_prod_all_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_producer_keys_full_csv",
                    )
        _cp_total = _cp_sum.get("critique_pairing_critic_role_entries_total")
        if type(_cp_total) is int and _cp_total > 0:
            st.caption(
                "Critique pairings: **"
                + str(_cp_total)
                + "** critic role list entr(y/ies) across producers (non-empty strings)."
            )
        _cp_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _cp_slug = critique_pairings_export_filename_slug()
        _cp_json = critique_pairings_operator_summary_export_json(_cp_sum)
        st.download_button(
            label="Download critique pairings summary JSON",
            data=_cp_json.encode("utf-8"),
            file_name=f"hermes_{_cp_slug}_{_cp_ts}.json",
            mime="application/json",
            key="hermes_dl_critique_pairings_summary_json",
        )
        _cp_critic_rows = critique_pairings_critic_counts_table_rows(_cp_sum)
        if _cp_critic_rows:
            _cp_critic_json = critique_pairings_critic_counts_export_json(_cp_critic_rows)
            _cp_critic_csv = critique_pairings_critic_counts_table_rows_csv(_cp_critic_rows)
            _cp_critic_dl_json_col, _cp_critic_dl_csv_col = st.columns(2)
            with _cp_critic_dl_json_col:
                st.download_button(
                    label="Download critique pairings critic counts JSON",
                    data=_cp_critic_json.encode("utf-8"),
                    file_name=f"hermes_{_cp_slug}_critic_counts_{_cp_ts}.json",
                    mime="application/json",
                    key="hermes_dl_critique_pairings_critic_counts_json",
                )
            with _cp_critic_dl_csv_col:
                if _cp_critic_csv:
                    st.download_button(
                        label="Download critique pairings critic counts CSV",
                        data=_cp_critic_csv.encode("utf-8"),
                        file_name=f"hermes_{_cp_slug}_critic_counts_{_cp_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_critic_counts_csv",
                    )
        _cp_critic_all_rows = critique_pairings_critic_counts_all_table_rows(_cp_sum)
        _cp_critic_sample_rows = critique_pairings_critic_counts_table_rows(_cp_sum)
        if _cp_critic_all_rows and len(_cp_critic_all_rows) > len(_cp_critic_sample_rows):
            _cp_critic_all_json = critique_pairings_critic_counts_all_export_json(
                _cp_critic_all_rows,
            )
            _cp_critic_all_csv = critique_pairings_critic_counts_all_table_rows_csv(
                _cp_critic_all_rows,
            )
            _cp_critic_all_dl_json_col, _cp_critic_all_dl_csv_col = st.columns(2)
            with _cp_critic_all_dl_json_col:
                st.download_button(
                    label="Download critique pairings critic counts (full) JSON",
                    data=_cp_critic_all_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_cp_slug}_critic_counts_full_{_cp_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_critique_pairings_critic_counts_full_json",
                )
            with _cp_critic_all_dl_csv_col:
                if _cp_critic_all_csv:
                    st.download_button(
                        label="Download critique pairings critic counts (full) CSV",
                        data=_cp_critic_all_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_cp_slug}_critic_counts_full_{_cp_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_critic_counts_full_csv",
                    )
        err = _cp_sum.get("load_error")
        if isinstance(err, str) and err.strip():
            st.warning(f"Could not parse critique_pairings.yaml: {err}")
        else:
            with st.expander("critique_pairings.yaml (operator summary)", expanded=False):
                st.caption(
                    "JSON-safe snapshot of the frozen YAML (§14 #14); not an API payload."
                )
                st.json(_cp_sum)
    if st.button("Load persona shelves", key="hermes_persona_load_btn"):
        try:
            st.session_state[_LAST_PERSONA_CATALOG_JSON] = load_persona_shelves_catalog(_proot)
        except FileNotFoundError as exc:
            st.error(str(exc))
        except ValueError as exc:
            st.error(f"Invalid persona shelves YAML: {exc}")
    _persona_blob = st.session_state.get(_LAST_PERSONA_CATALOG_JSON)
    if isinstance(_persona_blob, dict) and _persona_blob:
        st.json(_persona_blob)
        _p_dn_cap = persona_catalog_display_name_length_caption(_persona_blob)
        if _p_dn_cap:
            st.caption(_p_dn_cap)
        _p_id_cap = persona_catalog_persona_id_length_caption(_persona_blob)
        if _p_id_cap:
            st.caption(_p_id_cap)
        _psum = persona_catalog_operator_summary(_persona_blob)
        _p_empty_id_cap = persona_catalog_empty_id_operator_caption(_psum)
        if _p_empty_id_cap:
            st.caption(_p_empty_id_cap)
        _p_dup_dn_cap = persona_catalog_display_name_duplicates_operator_caption(_psum)
        if _p_dup_dn_cap:
            st.caption(_p_dup_dn_cap)
        _p_dup_id_cap = persona_catalog_persona_id_duplicates_operator_caption(_psum)
        if _p_dup_id_cap:
            st.caption(_p_dup_id_cap)
        _p_prob_cap = persona_catalog_probation_breakdown_caption(_psum)
        if _p_prob_cap:
            st.caption(_p_prob_cap)
        _p_woi_cap = persona_catalog_without_instructions_caption(_psum)
        if _p_woi_cap:
            st.caption(_p_woi_cap)
        _p_wocp_cap = persona_catalog_without_capability_profile_caption(_psum)
        if _p_wocp_cap:
            st.caption(_p_wocp_cap)
        with st.expander("Operator summary (fo141)", expanded=False):
            st.caption(
                "Read-only counts: shelf sizes, total entries, and how many personas "
                "populate optional fo127 fields."
            )
            _p_op_sum_metrics = persona_catalog_operator_summary_operator_metrics(_psum)
            _p_op_sum_metrics_cap = (
                persona_catalog_operator_summary_operator_metrics_caption(_p_op_sum_metrics)
            )
            if _p_op_sum_metrics_cap:
                st.caption(_p_op_sum_metrics_cap)
            _p_op_sum_metric_rows = (
                persona_catalog_operator_summary_operator_metrics_table_rows(
                    _p_op_sum_metrics,
                )
            )
            if _p_op_sum_metric_rows:
                st.dataframe(
                    _p_op_sum_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _p_op_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _p_op_sum_metrics_slug = (
                persona_catalog_operator_summary_operator_metrics_export_filename_slug()
            )
            _p_op_sum_metrics_json = (
                persona_catalog_operator_summary_operator_metrics_export_json(
                    _p_op_sum_metrics,
                )
            )
            _p_op_sum_metrics_csv = (
                persona_catalog_operator_summary_operator_metrics_table_rows_csv(
                    _p_op_sum_metric_rows,
                )
            )
            _p_op_sum_m_dl_json_col, _p_op_sum_m_dl_csv_col = st.columns(2)
            with _p_op_sum_m_dl_json_col:
                st.download_button(
                    label="Download operator summary metrics JSON",
                    data=_p_op_sum_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_p_op_sum_metrics_slug}_{_p_op_sum_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_persona_operator_summary_metrics_json",
                )
            with _p_op_sum_m_dl_csv_col:
                if _p_op_sum_metrics_csv:
                    st.download_button(
                        label="Download operator summary metrics CSV",
                        data=_p_op_sum_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_p_op_sum_metrics_slug}_{_p_op_sum_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_operator_summary_metrics_csv",
                    )
            _p_op_sum_json = persona_catalog_operator_summary_export_json(_psum)
            _p_op_sum_csv = persona_catalog_operator_summary_table_rows_csv(_psum)
            _p_op_sum_dl_json_col, _p_op_sum_dl_csv_col = st.columns(2)
            with _p_op_sum_dl_json_col:
                st.download_button(
                    label="Download operator summary JSON",
                    data=_p_op_sum_json.encode("utf-8"),
                    file_name=f"hermes_persona_operator_summary_{_p_op_sum_ts}.json",
                    mime="application/json",
                    key="hermes_dl_persona_operator_summary_json",
                )
            with _p_op_sum_dl_csv_col:
                if _p_op_sum_csv:
                    st.download_button(
                        label="Download operator summary CSV",
                        data=_p_op_sum_csv.encode("utf-8"),
                        file_name=f"hermes_persona_operator_summary_{_p_op_sum_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_operator_summary_csv",
                    )
            st.json(_psum)
        _p_other_rows = persona_probation_other_examples_by_shelf_table_rows(_psum)
        if _p_other_rows:
            st.caption(
                "Non-canonical **probation_status** strings by shelf (deduped sample; §14 #14)."
            )
            st.dataframe(_p_other_rows, use_container_width=True, hide_index=True)
            _p_other_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _p_other_slug = persona_probation_other_export_filename_slug()
            _p_other_json = persona_probation_other_by_shelf_export_json(_p_other_rows)
            _p_other_csv = persona_probation_other_by_shelf_table_rows_csv(_p_other_rows)
            _p_other_dl_csv_col, _p_other_dl_json_col = st.columns(2)
            with _p_other_dl_csv_col:
                if _p_other_csv:
                    st.download_button(
                        label="Download probation other examples CSV",
                        data=_p_other_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_persona_probation_other_{_p_other_slug}_{_p_other_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_probation_other_csv",
                    )
            with _p_other_dl_json_col:
                st.download_button(
                    label="Download probation other examples JSON",
                    data=_p_other_json.encode("utf-8"),
                    file_name=(
                        f"hermes_persona_probation_other_{_p_other_slug}_{_p_other_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_persona_probation_other_json",
                )
        _prows = persona_catalog_flat_rows(_persona_blob)
        if _prows:
            st.text_input(
                "Filter table: id / display_name substring (case-insensitive)",
                key="hermes_persona_catalog_filter_q",
            )
            st.selectbox(
                "Shelf filter",
                options=("all", "business_area", "development_role"),
                key="hermes_persona_catalog_filter_shelf",
            )
            st.selectbox(
                "Probation status filter",
                options=("all", "probation", "promoted", "shelved", "(unset)"),
                key="hermes_persona_catalog_filter_probation",
            )
            _p_tool_opts = ("all", *persona_catalog_distinct_allowed_tools(_persona_blob))
            st.selectbox(
                "Allowed tool filter (interim tags UX)",
                options=_p_tool_opts,
                key="hermes_persona_catalog_filter_allowed_tool",
            )
            _pq = str(st.session_state.get("hermes_persona_catalog_filter_q", "")).strip()
            _psel = str(st.session_state.get("hermes_persona_catalog_filter_shelf", "all"))
            _shelf_arg = None if _psel == "all" else _psel
            _pprob = str(
                st.session_state.get("hermes_persona_catalog_filter_probation", "all"),
            ).strip()
            _ptool = str(
                st.session_state.get("hermes_persona_catalog_filter_allowed_tool", "all"),
            ).strip()
            _pview = filter_persona_catalog_flat_rows(
                _prows,
                query=_pq,
                shelf=_shelf_arg,
                probation_status=_pprob,
                allowed_tool=_ptool,
            )
            _p_tool_cap = persona_catalog_allowed_tool_filter_caption(
                _ptool,
                match_count=len(_pview),
                total_count=len(_prows),
            )
            if _p_tool_cap:
                st.caption(_p_tool_cap)
            st.caption("Entries (table view — filtered)")
            st.dataframe(_pview, use_container_width=True)
            _pts_flat = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pflat_slug = persona_catalog_flat_export_filename_slug()
            _csv_body = persona_catalog_flat_rows_csv(_pview)
            _json_body = persona_catalog_flat_rows_export_json(_pview)
            _pflat_dl_csv_col, _pflat_dl_json_col = st.columns(2)
            with _pflat_dl_csv_col:
                if _csv_body:
                    st.download_button(
                        label="Download filtered table as CSV",
                        data=_csv_body.encode("utf-8"),
                        file_name=f"hermes_persona_shelves_flat_{_pflat_slug}_{_pts_flat}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_catalog_csv",
                    )
            with _pflat_dl_json_col:
                if _pview:
                    st.download_button(
                        label="Download filtered table as JSON",
                        data=_json_body.encode("utf-8"),
                        file_name=f"hermes_persona_shelves_flat_{_pflat_slug}_{_pts_flat}.json",
                        mime="application/json",
                        key="hermes_dl_persona_catalog_flat_json",
                    )
        _pts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        st.download_button(
            label="Download persona shelves JSON",
            data=json.dumps(_persona_blob, indent=2).encode("utf-8"),
            file_name=f"hermes_persona_shelves_{_pts}.json",
            mime="application/json",
            key="hermes_dl_persona_catalog_json",
        )
with st.expander("Persona editor (writes via API)", expanded=False):
    st.caption(
        "Edits go through PATCH / PUT / POST / DELETE ``/v1/personas`` (writes "
        "shelves.yaml atomically; emits ``persona.shelf.updated`` audit event). "
        "Requires the ``X-Hermes-Admin-Token`` value below. "
        "Use 'Reload from API' to refresh the local snapshot before saving."
    )
    _admin_token = st.text_input(
        "X-Hermes-Admin-Token",
        key="hermes_persona_edit_token",
        type="password",
    )
    if st.button("Reload from API", key="hermes_persona_edit_reload_btn"):
        try:
            _r = httpx.get(f"{API_BASE}/personas", timeout=10.0)
            _r.raise_for_status()
            st.session_state["hermes_persona_edit_catalog"] = _r.json()
            st.success("Loaded persona catalog from API.")
        except httpx.HTTPError as _exc:
            st.error(f"API error: {_exc}")
    _editor_catalog = st.session_state.get("hermes_persona_edit_catalog")
    if not isinstance(_editor_catalog, dict):
        st.caption("Click 'Reload from API' to load the catalog before editing.")
    else:
        _shelf = st.selectbox(
            "Shelf",
            options=["business_area", "development_role"],
            key="hermes_persona_edit_shelf",
        )
        _shelf_cap = persona_editor_selected_shelf_caption(_shelf)
        if _shelf_cap:
            st.caption(_shelf_cap)
        _ids = [
            str(e.get("id", ""))
            for e in (_editor_catalog.get(_shelf) or [])
            if isinstance(e, dict) and e.get("id")
        ]
        _selected = st.selectbox(
            "Persona (existing) — or pick '(new)' to create a new entry",
            options=["(new)", *_ids],
            key="hermes_persona_edit_select",
        )
        _existing = (
            find_persona_in_catalog(_editor_catalog, _shelf, _selected)
            if _selected != "(new)"
            else None
        )
        _snapshot: dict[str, Any] = dict(_existing) if _existing else {}
        st.text_input(
            "id",
            value=str(_snapshot.get("id", "")),
            key="hermes_persona_edit_id",
            disabled=_existing is not None,
            help="Cannot be changed after creation; use DELETE + POST to rename.",
        )
        st.text_input(
            "display_name",
            value=str(_snapshot.get("display_name", "")),
            key="hermes_persona_edit_display_name",
        )
        _dn_cap = persona_editor_display_name_draft_caption(
            st.session_state.get("hermes_persona_edit_display_name", ""),
        )
        if _dn_cap:
            st.caption(_dn_cap)
        st.text_area(
            "instructions (system prompt; up to 8000 chars)",
            value=str(_snapshot.get("instructions", "")),
            key="hermes_persona_edit_instructions",
            height=200,
        )
        _ins_cap = persona_editor_instructions_metrics_caption(
            st.session_state.get("hermes_persona_edit_instructions", ""),
        )
        if _ins_cap:
            st.caption(_ins_cap)
        st.text_area(
            "capability_profile (up to 2000 chars)",
            value=str(_snapshot.get("capability_profile", "")),
            key="hermes_persona_edit_capability_profile",
            height=120,
        )
        st.text_area(
            "boundary_statement (up to 2000 chars)",
            value=str(_snapshot.get("boundary_statement", "")),
            key="hermes_persona_edit_boundary_statement",
            height=120,
        )
        _multi_cap = persona_editor_multiline_field_metrics_caption(
            st.session_state.get("hermes_persona_edit_capability_profile", ""),
            st.session_state.get("hermes_persona_edit_boundary_statement", ""),
        )
        if _multi_cap:
            st.caption(_multi_cap)
        st.text_area(
            "allowed_tools (one per line, up to 50)",
            value="\n".join(_snapshot.get("allowed_tools") or []),
            key="hermes_persona_edit_allowed_tools",
            height=100,
        )
        st.text_area(
            "success_metrics (one per line, up to 20)",
            value="\n".join(_snapshot.get("success_metrics") or []),
            key="hermes_persona_edit_success_metrics",
            height=100,
        )
        _list_fields_cap = persona_list_field_line_counts_caption(
            st.session_state.get("hermes_persona_edit_allowed_tools", ""),
            st.session_state.get("hermes_persona_edit_success_metrics", ""),
        )
        if _list_fields_cap:
            st.caption(_list_fields_cap)
        st.selectbox(
            "probation_status",
            options=["promoted", "probation", "shelved"],
            index=["promoted", "probation", "shelved"].index(
                str(_snapshot.get("probation_status") or "promoted"),
            ),
            key="hermes_persona_edit_probation_status",
        )
        _prob_draft_cap = persona_editor_probation_status_draft_caption(
            st.session_state.get("hermes_persona_edit_probation_status"),
        )
        if _prob_draft_cap:
            st.caption(_prob_draft_cap)
        st.text_input(
            "actor (optional; recorded in the audit event)",
            key="hermes_persona_edit_actor",
        )

        def _split_lines(raw: str) -> list[str]:
            return [ln.strip() for ln in raw.splitlines() if ln.strip()]

        _edited: dict[str, Any] = {
            "id": st.session_state["hermes_persona_edit_id"].strip(),
            "display_name": st.session_state["hermes_persona_edit_display_name"].strip()
            or None,
            "instructions": st.session_state["hermes_persona_edit_instructions"]
            or None,
            "capability_profile": st.session_state[
                "hermes_persona_edit_capability_profile"
            ]
            or None,
            "boundary_statement": st.session_state[
                "hermes_persona_edit_boundary_statement"
            ]
            or None,
            "allowed_tools": _split_lines(
                st.session_state["hermes_persona_edit_allowed_tools"],
            )
            or None,
            "success_metrics": _split_lines(
                st.session_state["hermes_persona_edit_success_metrics"],
            )
            or None,
            "probation_status": st.session_state[
                "hermes_persona_edit_probation_status"
            ],
        }
        _diff = diff_summary(_snapshot, _edited) if _existing else []
        if _existing:
            _prob_cap = persona_editor_probation_status_caption(_snapshot)
            if _prob_cap:
                st.caption(_prob_cap)
            _ver_cap = persona_editor_expected_version_caption(_snapshot)
            if _ver_cap:
                st.caption(_ver_cap)
            _diff_cap = persona_editor_diff_summary_caption(_snapshot, _edited)
            if _diff_cap:
                st.caption(_diff_cap)
        if _diff:
            with st.expander("Diff preview", expanded=False):
                for line in _diff:
                    st.write(f"- {line}")

        _validation_issues = persona_editor_validation_issues(
            _edited,
            require_non_empty_id=_existing is None,
        )
        _validation_cap = persona_editor_validation_blocking_caption(
            _validation_issues,
        )
        if _validation_cap:
            st.caption(_validation_cap)
        _validation_rows = persona_editor_validation_table_rows(_validation_issues)
        if _validation_rows:
            st.dataframe(_validation_rows, use_container_width=True)
        _write_blocked = bool(_validation_issues)

        _actor = st.session_state["hermes_persona_edit_actor"].strip() or None
        _headers = (
            {"X-Hermes-Admin-Token": _admin_token} if _admin_token else {}
        )
        _col_save, _col_replace, _col_delete, _col_create = st.columns(4)

        def _handle_write_response(label: str, r: httpx.Response) -> None:
            try:
                body = r.json() if r.content else None
            except json.JSONDecodeError:
                body = None
            parsed = parse_write_response(r.status_code, body)
            if parsed["ok"]:
                st.session_state["hermes_persona_edit_catalog"] = parsed["catalog"]
                st.success(f"{label}: 2xx (catalog refreshed).")
            elif parsed.get("version_conflict"):
                st.warning(
                    f"{label}: 409 version conflict — reload from API and retry."
                )
            else:
                st.error(
                    f"{label}: {parsed['status']} {parsed['code']} — {parsed['message']}"
                )

        with _col_save:
            if st.button(
                "Save (PATCH)",
                key="hermes_persona_edit_save_btn",
                disabled=_existing is None or _write_blocked,
            ):
                req = build_patch_request(_snapshot, _edited, actor=_actor)
                try:
                    _resp = httpx.patch(
                        f"{API_BASE}/personas/{_shelf}/{_selected}",
                        json=req,
                        headers=_headers,
                        timeout=10.0,
                    )
                    _handle_write_response("PATCH", _resp)
                except httpx.HTTPError as _exc:
                    st.error(f"API error: {_exc}")
        with _col_replace:
            if st.button(
                "Replace (PUT)",
                key="hermes_persona_edit_replace_btn",
                disabled=_existing is None or _write_blocked,
            ):
                entry_body = {k: v for k, v in _edited.items() if v is not None}
                entry_body["id"] = _snapshot.get("id", _selected)
                put_body = {
                    "entry": entry_body,
                    "expected_version": int(_snapshot.get("version", 1) or 1),
                    "actor": _actor,
                }
                try:
                    _resp = httpx.put(
                        f"{API_BASE}/personas/{_shelf}/{_selected}",
                        json=put_body,
                        headers=_headers,
                        timeout=10.0,
                    )
                    _handle_write_response("PUT", _resp)
                except httpx.HTTPError as _exc:
                    st.error(f"API error: {_exc}")
        with _col_delete:
            if st.button(
                "Delete",
                key="hermes_persona_edit_delete_btn",
                disabled=_existing is None,
            ):
                try:
                    _resp = httpx.delete(
                        f"{API_BASE}/personas/{_shelf}/{_selected}",
                        params={
                            "expected_version": int(
                                _snapshot.get("version", 1) or 1,
                            ),
                            **({"actor": _actor} if _actor else {}),
                        },
                        headers=_headers,
                        timeout=10.0,
                    )
                    _handle_write_response("DELETE", _resp)
                except httpx.HTTPError as _exc:
                    st.error(f"API error: {_exc}")
        with _col_create:
            if st.button(
                "Create (POST)",
                key="hermes_persona_edit_create_btn",
                disabled=_existing is not None or _write_blocked,
            ):
                new_id = st.session_state["hermes_persona_edit_id"].strip()
                if not new_id:
                    st.error("Set a non-empty id before creating.")
                elif _write_blocked:
                    pass
                else:
                    entry_body = {
                        k: v for k, v in _edited.items() if v is not None
                    }
                    entry_body["id"] = new_id
                    post_body = {"entry": entry_body, "actor": _actor}
                    try:
                        _resp = httpx.post(
                            f"{API_BASE}/personas/{_shelf}",
                            json=post_body,
                            headers=_headers,
                            timeout=10.0,
                        )
                        _handle_write_response("POST", _resp)
                    except httpx.HTTPError as _exc:
                        st.error(f"API error: {_exc}")
_PRUNE_STATUS_PATH = _resolve_prune_status_path()
if _PRUNE_STATUS_PATH is not None:
    with st.expander("Prune status (scraper artifacts)", expanded=False):
        st.caption(
            "Reads the JSON file written by ``scripts/prune_scraper_artifacts.py "
            "--summary-path`` (or ``HERMES_PRUNE_STATUS_PATH``). Same shape as the "
            "``--json-summary`` stdout line plus a UTC ``wrote_at`` timestamp. "
            "Surfaces ``retention_alert_level``, ``retention_execution_mode``, "
            "object-store mirror prune counts, and ``retention_lifecycle_state`` when present."
        )
        st.caption(f"Effective status file: `{_PRUNE_STATUS_PATH}`")
        st.caption(prune_scraper_artifact_prune_workflow_caption())
        _prune_status = load_prune_status(_PRUNE_STATUS_PATH)
        _prune_schema_cap = prune_status_schema_version_caption(_prune_status)
        if _prune_schema_cap:
            st.caption(_prune_schema_cap)
        st.caption(prune_status_freshness_caption(_prune_status))
        _prune_age_cap = prune_status_age_since_wrote_at_caption(_prune_status)
        if _prune_age_cap:
            st.caption(_prune_age_cap)
        _prune_pat_cap = prune_status_pattern_filter_caption(_prune_status)
        if _prune_pat_cap:
            st.caption(_prune_pat_cap)
        _prune_max_age_cap = prune_status_max_age_days_caption(_prune_status)
        if _prune_max_age_cap:
            st.caption(_prune_max_age_cap)
        _prune_ret_alert_cap = prune_status_retention_alert_caption(_prune_status)
        if _prune_ret_alert_cap:
            st.caption(_prune_ret_alert_cap)
        _prune_ret_exec_cap = prune_status_retention_execution_caption(_prune_status)
        if _prune_ret_exec_cap:
            st.caption(_prune_ret_exec_cap)
        _prune_ret_policy_cap = prune_status_retention_policy_caption(_prune_status)
        if _prune_ret_policy_cap:
            st.caption(_prune_ret_policy_cap)
        _prune_os_cap = prune_status_object_store_prune_caption(_prune_status)
        if _prune_os_cap:
            st.caption(_prune_os_cap)
        _prune_dry_cap = prune_status_dry_run_caption(_prune_status)
        if _prune_dry_cap:
            st.caption(_prune_dry_cap)
        _prune_wrote_cap = prune_status_wrote_at_caption(_prune_status)
        if _prune_wrote_cap:
            st.caption(_prune_wrote_cap)
        _prune_outcome_cap = prune_status_pruned_outcome_caption(_prune_status)
        if _prune_outcome_cap:
            st.caption(_prune_outcome_cap)
        _prune_base_cap = prune_status_base_dir_caption(_prune_status)
        if _prune_base_cap:
            st.caption(_prune_base_cap)
        _prune_metrics = prune_status_operator_metrics(_prune_status)
        _prune_metrics_cap = prune_status_operator_metrics_caption(_prune_metrics)
        if _prune_metrics_cap:
            st.caption(_prune_metrics_cap)
        _prune_metric_rows = prune_status_operator_metrics_table_rows(_prune_metrics)
        _prune_rows = prune_status_summary_rows(_prune_status)
        _prune_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _prune_metrics_slug = prune_status_operator_metrics_export_filename_slug()
        if _prune_metric_rows:
            st.dataframe(
                _prune_metric_rows,
                use_container_width=True,
                hide_index=True,
            )
            _prune_metrics_json = prune_status_operator_metrics_export_json(
                _prune_metrics,
            )
            _prune_metrics_csv = prune_status_operator_metrics_table_rows_csv(
                _prune_metric_rows,
            )
            _prune_metrics_dl_json_col, _prune_metrics_dl_csv_col = st.columns(2)
            with _prune_metrics_dl_json_col:
                st.download_button(
                    label="Download prune status operator metrics JSON",
                    data=_prune_metrics_json.encode("utf-8"),
                    file_name=(
                        "hermes_prune_status_operator_metrics_"
                        f"{_prune_metrics_slug}_{_prune_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_prune_status_operator_metrics_json",
                )
            with _prune_metrics_dl_csv_col:
                if _prune_metrics_csv:
                    st.download_button(
                        label="Download prune status operator metrics CSV",
                        data=_prune_metrics_csv.encode("utf-8"),
                        file_name=(
                            "hermes_prune_status_operator_metrics_"
                            f"{_prune_metrics_slug}_{_prune_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_prune_status_operator_metrics_csv",
                    )
        if _prune_rows:
            st.dataframe(_prune_rows, use_container_width=True, hide_index=True)
        if _prune_status is not None:
            _prune_json = prune_status_export_json(_prune_status)
            _prune_csv = prune_status_summary_rows_csv(_prune_rows)
            _pr_dl1, _pr_dl2 = st.columns(2)
            with _pr_dl1:
                st.download_button(
                    label="Download prune status JSON",
                    data=_prune_json.encode("utf-8"),
                    file_name=f"hermes_prune_status_{_prune_ts}.json",
                    mime="application/json",
                    key="hermes_dl_prune_status_json",
                )
            with _pr_dl2:
                if _prune_csv:
                    st.download_button(
                        label="Download prune status summary CSV",
                        data=_prune_csv.encode("utf-8"),
                        file_name=f"hermes_prune_status_summary_{_prune_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_prune_status_summary_csv",
                    )
            with st.expander("Raw prune status JSON", expanded=False):
                st.json(_prune_status)
with st.container(border=True):
    st.subheader("Recent runs")
    st.caption(
        "Run list filters sync to the page URL (bookmark/share). Other query keys are left intact.",
    )
    st.text_input("List filter: workflow_profile (optional)", key=_SS_WF)
    st.text_input(
        "List filter: workflow_profile_prefix (optional; only if workflow_profile empty)",
        key=_SS_PFX,
    )
    st.selectbox(
        "List sort order",
        options=["newest_first", "oldest_first"],
        key=_SS_ORDER,
    )
    st.selectbox(
        "List filter: has_escalation (optional; matches GET /v1/runs)",
        options=["(not set)", "0", "1"],
        key=_SS_ESC,
        help="0 = without run.escalated; 1 = with run.escalated",
    )
    st.selectbox(
        "List filter: status (optional; replay-derived: created / running / terminal)",
        options=["(not set)", "created", "running", "terminal"],
        key=_SS_ST,
        help="Matches GET /v1/runs?status= (same semantics as run summaries).",
    )
    st.checkbox(
        "Include per-run summaries (sets limit=20; API cap for include_summary)",
        key=_SS_SUM,
    )
    st.text_input(
        "List filter: created_after (ISO-8601, optional; e.g. 2020-01-01T00:00:00Z)",
        key=_SS_CA,
    )
    st.text_input(
        "List filter: created_before (ISO-8601, optional)",
        key=_SS_CB,
    )
    col_off, col_lim = st.columns(2)
    with col_off:
        st.number_input("List offset", min_value=0, step=1, key=_SS_OFF)
    with col_lim:
        st.number_input(
            "List limit (1–200; max 20 when summaries on)",
            min_value=1,
            max_value=200,
            step=1,
            key=_SS_LIM,
        )

    st.text_input(
        "Keyset cursor (optional; paste ``next_cursor`` from API JSON; "
        "clears offset paging when set)",
        key=_SS_CUR,
        help=(
            "When non-empty, calls GET /v1/runs with cursor= and offset=0. "
            "Clear to use numeric offset again."
        ),
    )

    _snap = st.session_state.get(_LAST_LIST_PAGE)
    _can_next = bool(_snap and _snap.get("has_more") and _snap.get("n_ids", 0) > 0)
    _can_prev = bool(_snap and int(_snap.get("offset", 0)) > 0)
    _nc = _snap.get("next_cursor") if isinstance(_snap, dict) else None
    _can_next_keyset = bool(
        _snap and _snap.get("has_more") and isinstance(_nc, str) and len(_nc) > 0,
    )

    col_rf, col_rs, col_nx, col_nk, col_pr = st.columns([2, 1, 1, 1, 1])
    with col_rf:
        _refresh = st.button("Refresh run list")
    with col_rs:
        _reset_list = st.button(
            "Reset list filters",
            help=(
                "Clears list query params and session filters "
                "(bookmark URL resets for this block)."
            ),
        )
    with col_nx:
        _next_page = st.button("Next page", disabled=not _can_next)
    with col_nk:
        _next_keyset = st.button(
            "Next (keyset)",
            disabled=not _can_next_keyset,
            help="Sets cursor from last response ``next_cursor`` (matches API keyset paging).",
        )
    with col_pr:
        _prev_page = st.button("Prev page", disabled=not _can_prev)

    st.caption(
        "Next/Prev step the list **offset** (same as API **Link** ``rel=prev/next`` when not "
        "using keyset). **Next (keyset)** applies ``next_cursor`` and clears offset; clear the "
        "cursor field to return to offset paging. Refresh once after changing filters.",
    )
    if isinstance(_snap, dict) and (
        _snap.get("link")
        or _snap.get("next_cursor")
        or (
            isinstance(_snap.get("total"), int)
            and not isinstance(_snap.get("total"), bool)
        )
    ):
        with st.expander("Pagination (API)", expanded=False):
            st.caption("RFC 5988 ``Link`` from the last successful list response (copy below).")
            st.code(str(_snap.get("link") or ""), language=None)
            st.caption(
                "Opaque ``next_cursor`` from the JSON body (same value as **Next (keyset)**)."
            )
            st.code(str(_snap.get("next_cursor") or ""), language=None)
            _tot_snap = _snap.get("total")
            if isinstance(_tot_snap, int) and not isinstance(_tot_snap, bool):
                st.caption(f"``total`` from the same JSON body: **{_tot_snap}** (server-reported).")

    if _refresh:
        _run_list_fetch_and_display()
    elif _reset_list:
        _run_list_reset_defaults()
        _run_list_clear_query_params()
        st.rerun()
    elif _next_page and _snap:
        st.session_state[_SS_CUR] = ""
        st.session_state[_SS_OFF] = int(_snap["offset"]) + int(_snap["n_ids"])
        _run_list_fetch_and_display()
    elif _next_keyset and _snap:
        kc = _snap.get("next_cursor")
        if isinstance(kc, str) and kc:
            st.session_state[_SS_CUR] = kc
            st.session_state[_SS_OFF] = 0
            _run_list_fetch_and_display()
    elif _prev_page and _snap:
        st.session_state[_SS_CUR] = ""
        _lim_step = int(_snap["params"].get("limit", 50))
        st.session_state[_SS_OFF] = max(0, int(_snap["offset"]) - _lim_step)
        _run_list_fetch_and_display()

    with st.expander("Cross-run preflight trends (from last list)", expanded=False):
        st.caption(
            "Calls **GET /v1/preflight-history** (bounded fleet aggregation; same top-level "
            "``preflight`` projection as **Preflight history (from timeline)**). Requests "
            "``include_metrics_export=1`` for fleet SLI captions and a metrics-export JSON "
            "download when present. **run_index** follows API order (``1`` = first entry, "
            "usually newest when ``order=newest_first``). When the last run list had more "
            "ids than the cap, history may return fewer rows than the list page."
        )
        st.number_input(
            "Max runs to scan (cap)",
            min_value=1,
            max_value=15,
            value=10,
            step=1,
            key="hermes_preflight_trend_cap",
        )
        _list_for_trend = st.session_state.get(_LAST_LIST_JSON)
        _ids_trend: list[str] = []
        if isinstance(_list_for_trend, dict):
            _raw_ids = _list_for_trend.get("run_ids") or []
            if isinstance(_raw_ids, list):
                _ids_trend = [str(x).strip() for x in _raw_ids if str(x).strip()]
        if not _ids_trend:
            st.info("Refresh the run list above first so run_ids are available.")
        elif st.button("Load preflight trend", key="hermes_preflight_trend_btn"):
            _cap = int(st.session_state.get("hermes_preflight_trend_cap", 10))
            _cap = max(1, min(15, _cap))
            _slice = _ids_trend[:_cap]
            _trend_fetch_errs: list[str] = []
            try:
                _hist_body = fetch_preflight_history(
                    API_BASE,
                    limit=_cap,
                    include_metrics_export=True,
                )
                _pairs = preflight_pairs_from_history_response(_hist_body)
                st.session_state[_PREFLIGHT_TREND_HISTORY_BODY] = _hist_body
                st.session_state.pop(_PREFLIGHT_TREND_ERR, None)
            except httpx.HTTPError as _exc:
                _pairs = []
                _trend_fetch_errs.append(str(_exc))
                st.session_state.pop(_PREFLIGHT_TREND_HISTORY_BODY, None)
            _rows_t = preflight_cross_run_trend_rows(_pairs)
            st.session_state[_PREFLIGHT_TREND_ROWS] = _rows_t
            if _trend_fetch_errs:
                st.session_state[_PREFLIGHT_TREND_ERR] = _trend_fetch_errs
            else:
                st.session_state.pop(_PREFLIGHT_TREND_ERR, None)

        _trend_rows = st.session_state.get(_PREFLIGHT_TREND_ROWS)
        _trend_errs = st.session_state.get(_PREFLIGHT_TREND_ERR)
        if isinstance(_trend_errs, list) and _trend_errs:
            for _ln in _trend_errs[:8]:
                st.warning(str(_ln))
            if len(_trend_errs) > 8:
                st.caption(f"(+{len(_trend_errs) - 8} more preflight-history errors)")
        _hist_saved = st.session_state.get(_PREFLIGHT_TREND_HISTORY_BODY)
        if isinstance(_hist_saved, dict) and _ids_trend:
            _cap_saved = int(st.session_state.get("hermes_preflight_trend_cap", 10))
            _cap_saved = max(1, min(15, _cap_saved))
            _list_slice_len = min(len(_ids_trend), _cap_saved)
            _returned = len(_hist_saved.get("entries") or [])
            _api_lim = preflight_history_response_limit(_hist_saved)
            _pf_export_cap = preflight_history_response_metrics_export_caption(_hist_saved)
            if _pf_export_cap:
                st.caption(_pf_export_cap)
            _pf_sli_cap = preflight_history_response_sli_caption(_hist_saved)
            if _pf_sli_cap:
                st.caption(_pf_sli_cap)
            _pf_hist_export_json = preflight_history_metrics_export_download_json(
                _hist_saved,
            )
            if _pf_hist_export_json != "{}":
                _pf_hist_export_slug = (
                    preflight_history_metrics_export_download_filename_slug()
                )
                _pf_hist_export_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                st.download_button(
                    label="Download fleet preflight metrics export JSON",
                    data=_pf_hist_export_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_pf_hist_export_slug}_{_pf_hist_export_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_preflight_history_metrics_export_json",
                )
            if _returned < _list_slice_len:
                _lim_note = f" (API limit {_api_lim})" if _api_lim is not None else ""
                st.caption(
                    f"Preflight history returned **{_returned}** run(s) for a list slice of "
                    f"**{_list_slice_len}**{_lim_note}; fleet order may differ from the run list."
                )
        if isinstance(_trend_rows, list) and _trend_rows:
            _sum = preflight_cross_run_trend_summary(_trend_rows)
            st.caption(
                f"Scanned {_sum['runs']} runs — {_sum['with_preflight_projection']} with "
                f"preflight projection, {_sum['with_p95_latency']} with usable p95."
            )
            _sample_cov_cap = preflight_cross_run_latency_sample_count_coverage_caption(
                _trend_rows,
            )
            if _sample_cov_cap:
                st.caption(_sample_cov_cap)
            _checks_cov_cap = preflight_cross_run_checks_passed_coverage_caption(_trend_rows)
            if _checks_cov_cap:
                st.caption(_checks_cov_cap)
            _p95_spread_cap = preflight_cross_run_p95_spread_caption(_trend_rows)
            if _p95_spread_cap:
                st.caption(_p95_spread_cap)
            _multi_cap = preflight_cross_run_multisample_caption(_trend_rows)
            if _multi_cap:
                st.caption(_multi_cap)
            _vm_cov_cap = preflight_cross_run_validated_model_id_coverage_caption(_trend_rows)
            if _vm_cov_cap:
                st.caption(_vm_cov_cap)
            _depth_cap = preflight_cross_run_operator_depth_caption(_trend_rows)
            if _depth_cap:
                st.caption(_depth_cap)
            _pref_trend_metrics = preflight_cross_run_operator_metrics(_sum)
            _pref_trend_metrics_cap = preflight_cross_run_operator_metrics_caption(
                _pref_trend_metrics,
            )
            if _pref_trend_metrics_cap:
                st.caption(_pref_trend_metrics_cap)
            _pref_trend_metric_rows = preflight_cross_run_operator_metrics_table_rows(
                _pref_trend_metrics,
            )
            _pref_trend_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pref_trend_slug = preflight_cross_run_trend_export_filename_slug()
            _pref_trend_metrics_slug = (
                preflight_cross_run_operator_metrics_export_filename_slug()
            )
            if _pref_trend_metric_rows:
                st.dataframe(
                    _pref_trend_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _pref_trend_metrics_json = (
                    preflight_cross_run_operator_metrics_export_json(
                        _pref_trend_metrics,
                    )
                )
                _pref_trend_metrics_csv = (
                    preflight_cross_run_operator_metrics_table_rows_csv(
                        _pref_trend_metric_rows,
                    )
                )
                (
                    _pref_trend_metrics_dl_json_col,
                    _pref_trend_metrics_dl_csv_col,
                ) = st.columns(2)
                with _pref_trend_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download preflight cross-run operator "
                            "metrics JSON"
                        ),
                        data=_pref_trend_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_preflight_cross_run_operator_metrics_"
                            f"{_pref_trend_metrics_slug}_{_pref_trend_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_preflight_cross_run_operator_metrics_json",
                    )
                with _pref_trend_metrics_dl_csv_col:
                    if _pref_trend_metrics_csv:
                        st.download_button(
                            label=(
                                "Download preflight cross-run operator "
                                "metrics CSV"
                            ),
                            data=_pref_trend_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_preflight_cross_run_operator_metrics_"
                                f"{_pref_trend_metrics_slug}_{_pref_trend_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_preflight_cross_run_operator_metrics_csv",
                        )
            st.dataframe(_trend_rows, use_container_width=True, hide_index=True)
            _pref_trend_csv = preflight_cross_run_trend_rows_csv(_trend_rows)
            _pref_trend_json = preflight_cross_run_trend_export_json(_trend_rows)
            _pref_trend_dl_col, _pref_trend_dl_json_col = st.columns(2)
            with _pref_trend_dl_col:
                st.download_button(
                    label="Download preflight cross-run trend CSV",
                    data=_pref_trend_csv.encode("utf-8"),
                    file_name=f"hermes_preflight_cross_run_{_pref_trend_slug}_{_pref_trend_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_preflight_cross_run_csv",
                )
            with _pref_trend_dl_json_col:
                st.download_button(
                    label="Download preflight cross-run trend JSON",
                    data=_pref_trend_json.encode("utf-8"),
                    file_name=f"hermes_preflight_cross_run_{_pref_trend_slug}_{_pref_trend_ts}.json",
                    mime="application/json",
                    key="hermes_dl_preflight_cross_run_json",
                )
            _xs = [int(r["run_index"]) for r in _trend_rows if isinstance(r, dict)]
            _y_p95 = [
                float(r["p95_latency_ms"])
                if isinstance(r, dict) and isinstance(r.get("p95_latency_ms"), int)
                else math.nan
                for r in _trend_rows
            ]
            _y_sc = [
                float(r["sample_count"])
                if isinstance(r, dict) and isinstance(r.get("sample_count"), int)
                else math.nan
                for r in _trend_rows
            ]
            st.caption("p95 latency (ms) vs run_index (missing points are gaps in the line).")
            st.line_chart(
                {"run_index": _xs, "p95_latency_ms": _y_p95},
                x="run_index",
                y="p95_latency_ms",
            )
            st.caption("Preflight sample count vs run_index (when reported).")
            st.line_chart(
                {"run_index": _xs, "sample_count": _y_sc},
                x="run_index",
                y="sample_count",
            )
            with st.expander("Raw preflight trend rows JSON", expanded=False):
                st.json(_trend_rows)
st.divider()
with st.container(border=True):
    st.subheader("Run detail")
    run_id = st.text_input("Run ID (detail)", placeholder="uuid", key=_SS_DETAIL)

    if run_id.strip():
        rid = run_id.strip()
        st.markdown(
            "Artifact-style **read-only JSON** (existing API; no separate artifact store yet):"
        )
        st.caption("Copy full URL from a line below (select text or use your terminal).")
        st.code(f"{API_BASE}/runs/{rid}", language=None)
        st.code(f"{API_BASE}/runs/{rid}/timeline", language=None)
        st.code(f"{API_BASE}/runs/{rid}/findings", language=None)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Load run summary") and run_id.strip():
            try:
                r = httpx.get(f"{API_BASE}/runs/{run_id.strip()}", timeout=30.0)
                r.raise_for_status()
                st.subheader("Summary")
                data = r.json()
                c1m, c2m, c3m = st.columns(3)
                c1m.metric("Events", data.get("event_count", "—"))
                c2m.metric("Findings", data.get("findings_count", "—"))
                c3m.metric("Escalated", "yes" if data.get("has_escalation") else "no")
                _sum_metrics = run_detail_summary_operator_metrics(data)
                _sum_metrics_cap = run_detail_summary_operator_metrics_caption(_sum_metrics)
                if _sum_metrics_cap:
                    st.caption(_sum_metrics_cap)
                _sum_metric_rows = run_detail_summary_operator_metrics_table_rows(
                    _sum_metrics,
                )
                if _sum_metric_rows:
                    st.dataframe(
                        _sum_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                _sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _sum_metrics_slug = run_detail_summary_operator_metrics_export_filename_slug()
                _sum_metrics_json = run_detail_summary_operator_metrics_export_json(
                    _sum_metrics,
                )
                _sum_metrics_csv = run_detail_summary_operator_metrics_table_rows_csv(
                    _sum_metric_rows,
                )
                _sum_m_dl_json_col, _sum_m_dl_csv_col = st.columns(2)
                with _sum_m_dl_json_col:
                    st.download_button(
                        label="Download run summary operator metrics JSON",
                        data=_sum_metrics_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_sum_metrics_slug}_"
                            f"{run_detail_summary_export_filename_slug(run_id.strip())}_"
                            f"{_sum_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_run_summary_metrics_json",
                    )
                with _sum_m_dl_csv_col:
                    if _sum_metrics_csv:
                        st.download_button(
                            label="Download run summary operator metrics CSV",
                            data=_sum_metrics_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_sum_metrics_slug}_"
                                f"{run_detail_summary_export_filename_slug(run_id.strip())}_"
                                f"{_sum_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_run_summary_metrics_csv",
                        )
                _sum_slug = run_detail_summary_export_filename_slug(run_id.strip())
                _sum_json = run_detail_summary_export_json(data)
                st.download_button(
                    label="Download run summary JSON",
                    data=_sum_json.encode("utf-8"),
                    file_name=f"hermes_run_summary_{_sum_slug}_{_sum_ts}.json",
                    mime="application/json",
                    key="hermes_dl_run_summary_json",
                )
                with st.expander("Raw summary JSON", expanded=False):
                    st.json(data)
            except httpx.HTTPError as exc:
                st.error(f"API error: {exc}")
        if st.button("Load timeline") and run_id.strip():
            try:
                r = httpx.get(f"{API_BASE}/runs/{run_id.strip()}/timeline", timeout=30.0)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPError as exc:
                st.error(f"API error: {exc}")
            else:
                events = timeline_events_from_body(data)
                st.subheader("Timeline")
                _tl_metrics = timeline_events_operator_metrics(events)
                _tl_metrics_cap = timeline_events_operator_metrics_caption(_tl_metrics)
                if _tl_metrics_cap:
                    st.caption(_tl_metrics_cap)
                _tl_metric_rows = timeline_events_operator_metrics_table_rows(
                    _tl_metrics,
                )
                _tl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _tl_slug = timeline_events_export_filename_slug(run_id.strip())
                if _tl_metric_rows:
                    st.dataframe(
                        _tl_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _tl_metrics_json = timeline_events_operator_metrics_export_json(
                        _tl_metrics,
                    )
                    _tl_metrics_csv = timeline_events_operator_metrics_table_rows_csv(
                        _tl_metric_rows,
                    )
                    _tl_metrics_dl_json_col, _tl_metrics_dl_csv_col = st.columns(2)
                    with _tl_metrics_dl_json_col:
                        st.download_button(
                            label="Download timeline events operator metrics JSON",
                            data=_tl_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_timeline_events_operator_metrics_"
                                f"{_tl_slug}_{_tl_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_timeline_events_operator_metrics_json",
                        )
                    with _tl_metrics_dl_csv_col:
                        if _tl_metrics_csv:
                            st.download_button(
                                label="Download timeline events operator metrics CSV",
                                data=_tl_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_timeline_events_operator_metrics_"
                                    f"{_tl_slug}_{_tl_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_timeline_events_operator_metrics_csv",
                            )
                _tl_events_json = timeline_events_export_json(data)
                _tl_events_rows = timeline_events_table_rows(events)
                _tl_events_csv = timeline_events_table_rows_csv(_tl_events_rows)
                st.download_button(
                    label="Download timeline JSON",
                    data=json.dumps(data, indent=2).encode("utf-8"),
                    file_name=f"{run_id.strip()}_timeline.json",
                    mime="application/json",
                )
                _tl_dl_json_col, _tl_dl_csv_col = st.columns(2)
                with _tl_dl_json_col:
                    st.download_button(
                        label="Download timeline events JSON (subset)",
                        data=_tl_events_json.encode("utf-8"),
                        file_name=(
                            f"hermes_timeline_events_{_tl_slug}_{_tl_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_timeline_events_json",
                    )
                with _tl_dl_csv_col:
                    if _tl_events_csv:
                        st.download_button(
                            label="Download timeline events CSV",
                            data=_tl_events_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_timeline_events_{_tl_slug}_{_tl_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_timeline_events_csv",
                        )
                with st.expander("Raw timeline events JSON", expanded=False):
                    st.json(events)
                _ig = integrator_gate_from_timeline(data)
                _ig_rows = integrator_gate_summary_rows(_ig)
                with st.expander("Integrator gate (from timeline)", expanded=False):
                    if not _ig_rows:
                        st.caption(
                            "No integrator_gate summary on this timeline (no integrator "
                            "gate.decision.emitted yet, or gate disabled for this run)."
                        )
                    else:
                        st.caption(
                            "Latest bundle integrator gate.decision.emitted summary "
                            "(same top-level integrator_gate as GET …/timeline)."
                        )
                        st.dataframe(_ig_rows, use_container_width=True)
                        _ig_rank_cap = integrator_gate_compatibility_ranking_caption(_ig)
                        if _ig_rank_cap:
                            st.caption(_ig_rank_cap)
                        _ig_rank_rows = integrator_gate_compatibility_ranking_table_rows(_ig)
                        if _ig_rank_rows:
                            st.dataframe(
                                _ig_rank_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                        _ig_bundle_cap = integrator_gate_latest_bundle_id_caption(_ig)
                        if _ig_bundle_cap:
                            st.caption(_ig_bundle_cap)
                        _ig_margin_cap = integrator_gate_latest_score_margin_caption(_ig)
                        if _ig_margin_cap:
                            st.caption(_ig_margin_cap)
                        _ig_tag_cap = integrator_gate_latest_tag_overlap_caption(_ig)
                        if _ig_tag_cap:
                            st.caption(_ig_tag_cap)
                        _ig_latest_m = integrator_gate_latest_operator_metrics(_ig)
                        _ig_latest_metrics_cap = integrator_gate_latest_operator_metrics_caption(
                            _ig_latest_m,
                        )
                        if _ig_latest_metrics_cap:
                            st.caption(_ig_latest_metrics_cap)
                        _ig_latest_ts = datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ",
                        )
                        _ig_latest_slug = integrator_gate_latest_export_filename_slug(
                            run_id.strip(),
                        )
                        if _ig_latest_m.get("present"):
                            _ig_latest_rows = integrator_gate_latest_metrics_table_rows(
                                _ig_latest_m,
                            )
                            st.caption(
                                "Operator drill-down on **latest** gate: tag overlap, "
                                "failure reason when set, numeric score vs min pass."
                            )
                            st.dataframe(
                                _ig_latest_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            if _ig_latest_rows:
                                _ig_latest_metrics_json = (
                                    integrator_gate_latest_operator_metrics_export_json(
                                        _ig_latest_m,
                                    )
                                )
                                _ig_latest_metrics_csv = (
                                    integrator_gate_latest_operator_metrics_table_rows_csv(
                                        _ig_latest_rows,
                                    )
                                )
                                (
                                    _ig_latest_metrics_dl_json_col,
                                    _ig_latest_metrics_dl_csv_col,
                                ) = st.columns(2)
                                with _ig_latest_metrics_dl_json_col:
                                    st.download_button(
                                        label=(
                                            "Download integrator gate latest "
                                            "operator metrics JSON"
                                        ),
                                        data=_ig_latest_metrics_json.encode("utf-8"),
                                        file_name=(
                                            "hermes_integrator_gate_latest_operator_metrics_"
                                            f"{_ig_latest_slug}_{_ig_latest_ts}.json"
                                        ),
                                        mime="application/json",
                                        key=(
                                            "hermes_dl_integrator_gate_latest_"
                                            "operator_metrics_json"
                                        ),
                                    )
                                with _ig_latest_metrics_dl_csv_col:
                                    if _ig_latest_metrics_csv:
                                        st.download_button(
                                            label=(
                                                "Download integrator gate latest "
                                                "operator metrics CSV"
                                            ),
                                            data=_ig_latest_metrics_csv.encode("utf-8"),
                                            file_name=(
                                                "hermes_integrator_gate_latest_operator_metrics_"
                                                f"{_ig_latest_slug}_{_ig_latest_ts}.csv"
                                            ),
                                            mime="text/csv; charset=utf-8",
                                            key=(
                                                "hermes_dl_integrator_gate_latest_"
                                                "operator_metrics_csv"
                                            ),
                                        )
                            with st.expander(
                                "Raw integrator_gate latest operator metrics JSON",
                                expanded=False,
                            ):
                                st.json(_ig_latest_m)
                        _ig_latest_csv = integrator_gate_latest_summary_rows_csv(_ig_rows)
                        _ig_latest_json = integrator_gate_latest_export_json(_ig)
                        _ig_latest_dl_col, _ig_latest_dl_json_col = st.columns(2)
                        with _ig_latest_dl_col:
                            st.download_button(
                                label="Download integrator gate latest CSV",
                                data=_ig_latest_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_latest_"
                                    f"{_ig_latest_slug}_{_ig_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_integrator_gate_latest_csv",
                            )
                        with _ig_latest_dl_json_col:
                            st.download_button(
                                label="Download integrator gate latest JSON",
                                data=_ig_latest_json.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_latest_"
                                    f"{_ig_latest_slug}_{_ig_latest_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_integrator_gate_latest_json",
                            )
                        with st.expander("Raw integrator_gate JSON", expanded=False):
                            st.json(_ig)
                _ig_hist = integrator_gate_history_from_timeline(data)
                _ig_hist_rows = integrator_gate_history_table_rows(_ig_hist)
                with st.expander("Integrator gate history (from timeline)", expanded=False):
                    if not _ig_hist_rows:
                        st.caption(
                            "No ``integrator_gate_history`` on this timeline (same condition as "
                            "empty latest summary — no integrator gate decisions recorded)."
                        )
                    else:
                        st.caption(
                            "Chronological ``gate.decision.emitted`` rows with integrator metadata "
                            "(bounded on the API; latest row matches **Integrator gate** summary)."
                        )
                        _ig_hist_count_cap = integrator_gate_history_entry_count_caption(_ig_hist)
                        if _ig_hist_count_cap:
                            st.caption(_ig_hist_count_cap)
                        _ig_hist_fail_cap = integrator_gate_history_failure_reason_caption(
                            _ig_hist,
                        )
                        if _ig_hist_fail_cap:
                            st.caption(_ig_hist_fail_cap)
                        st.dataframe(_ig_hist_rows, use_container_width=True)
                        _ig_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _ig_hist_slug = integrator_gate_history_export_filename_slug(
                            run_id.strip(),
                        )
                        _ig_hist_csv = integrator_gate_history_table_rows_csv(_ig_hist_rows)
                        _ig_hist_json = integrator_gate_history_export_json(_ig_hist)
                        _ig_dl_col, _ig_dl_json_col = st.columns(2)
                        with _ig_dl_col:
                            st.download_button(
                                label="Download integrator gate history CSV",
                                data=_ig_hist_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_integrator_gate_history_{_ig_hist_slug}_{_ig_hist_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_integrator_gate_history_csv",
                            )
                        with _ig_dl_json_col:
                            st.download_button(
                                label="Download integrator gate history JSON",
                                data=_ig_hist_json.encode("utf-8"),
                                file_name=(
                                    f"hermes_integrator_gate_history_{_ig_hist_slug}_{_ig_hist_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_integrator_gate_history_json",
                            )
                        _ig_hist_metrics = integrator_gate_history_operator_metrics(_ig_hist)
                        _ig_hist_metrics_cap = integrator_gate_history_operator_metrics_caption(
                            _ig_hist_metrics,
                        )
                        if _ig_hist_metrics_cap:
                            st.caption(_ig_hist_metrics_cap)
                        _ig_hist_verdict_cap = integrator_gate_history_verdict_tally_caption(
                            _ig_hist_metrics,
                        )
                        if _ig_hist_verdict_cap:
                            st.caption(_ig_hist_verdict_cap)
                        _ig_hist_bundles_cap = integrator_gate_history_distinct_bundles_caption(
                            _ig_hist_metrics,
                        )
                        if _ig_hist_bundles_cap:
                            st.caption(_ig_hist_bundles_cap)
                        _ig_hist_score_cap = integrator_gate_history_score_range_caption(
                            _ig_hist_metrics,
                        )
                        if _ig_hist_score_cap:
                            st.caption(_ig_hist_score_cap)
                        _ig_hist_margin_cap = integrator_gate_history_latest_margin_caption(
                            _ig_hist_metrics,
                        )
                        if _ig_hist_margin_cap:
                            st.caption(_ig_hist_margin_cap)
                        _ig_hist_metric_rows = integrator_gate_history_metrics_table_rows(
                            _ig_hist_metrics,
                        )
                        st.caption(
                            "Operator metrics over the **same** bounded history. "
                            "**Latest score minus min pass** is "
                            "``integrator_score - min_score_to_pass`` on the latest row only; "
                            "verdict may still reflect other rules."
                        )
                        st.dataframe(
                            _ig_hist_metric_rows,
                            use_container_width=True,
                            hide_index=True,
                        )
                        if _ig_hist_metric_rows:
                            _ig_hist_metrics_json = (
                                integrator_gate_history_operator_metrics_export_json(
                                    _ig_hist_metrics,
                                )
                            )
                            _ig_hist_metrics_csv = (
                                integrator_gate_history_operator_metrics_table_rows_csv(
                                    _ig_hist_metric_rows,
                                )
                            )
                            _ig_hist_metrics_dl_json_col, _ig_hist_metrics_dl_csv_col = (
                                st.columns(2)
                            )
                            with _ig_hist_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download integrator gate history "
                                        "operator metrics JSON"
                                    ),
                                    data=_ig_hist_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_integrator_gate_history_operator_metrics_"
                                        f"{_ig_hist_slug}_{_ig_hist_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_integrator_gate_history_operator_metrics_json",
                                )
                            with _ig_hist_metrics_dl_csv_col:
                                if _ig_hist_metrics_csv:
                                    st.download_button(
                                        label=(
                                        "Download integrator gate history "
                                        "operator metrics CSV"
                                    ),
                                        data=_ig_hist_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_integrator_gate_history_operator_metrics_"
                                            f"{_ig_hist_slug}_{_ig_hist_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_integrator_gate_history_operator_metrics_csv",
                                    )
                        with st.expander(
                            "Raw integrator_gate_history operator metrics JSON",
                            expanded=False,
                        ):
                            st.json(_ig_hist_metrics)
                        with st.expander("Raw integrator_gate_history JSON", expanded=False):
                            st.json(_ig_hist)
                _ig_delta = integrator_gate_delta_from_timeline(data)
                _ig_delta_rows = integrator_gate_delta_summary_rows(_ig_delta)
                with st.expander("Integrator gate delta (latest vs prior)", expanded=False):
                    if not _ig_delta_rows:
                        st.caption(
                            "No ``integrator_gate_delta`` — need at least two integrator "
                            "gate decisions on this timeline."
                        )
                    else:
                        st.caption(
                            "Diff between the last two ``gate.decision.emitted`` integrator rows "
                            "(same field as GET …/timeline ``integrator_gate_delta``)."
                        )
                        _ig_delta_cap = integrator_gate_delta_transition_caption(_ig_delta)
                        if _ig_delta_cap:
                            st.caption(_ig_delta_cap)
                        _ig_delta_verdict_cap = integrator_gate_delta_verdict_changed_caption(
                            _ig_delta,
                        )
                        if _ig_delta_verdict_cap:
                            st.caption(_ig_delta_verdict_cap)
                        _ig_delta_bundle_cap = integrator_gate_delta_bundle_changed_caption(
                            _ig_delta,
                        )
                        if _ig_delta_bundle_cap:
                            st.caption(_ig_delta_bundle_cap)
                        st.dataframe(_ig_delta_rows, use_container_width=True)
                        _ig_delta_ts = datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ",
                        )
                        _ig_delta_slug = integrator_gate_delta_export_filename_slug(
                            run_id.strip(),
                        )
                        _ig_d_m = integrator_gate_delta_operator_metrics(_ig_delta)
                        _ig_d_metrics_cap = integrator_gate_delta_operator_metrics_caption(
                            _ig_d_m,
                        )
                        if _ig_d_metrics_cap:
                            st.caption(_ig_d_metrics_cap)
                        if _ig_d_m.get("present"):
                            _ig_d_op_rows = integrator_gate_delta_operator_table_rows(_ig_d_m)
                            st.caption(
                                "Operator hints on **delta**: score direction, verdict transition, "
                                "bundle id change."
                            )
                            st.dataframe(
                                _ig_d_op_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            if _ig_d_op_rows:
                                _ig_d_metrics_json = (
                                    integrator_gate_delta_operator_metrics_export_json(
                                        _ig_d_m,
                                    )
                                )
                                _ig_d_metrics_csv = (
                                    integrator_gate_delta_operator_metrics_table_rows_csv(
                                        _ig_d_op_rows,
                                    )
                                )
                                _ig_d_metrics_dl_json_col, _ig_d_metrics_dl_csv_col = (
                                    st.columns(2)
                                )
                                with _ig_d_metrics_dl_json_col:
                                    st.download_button(
                                        label=(
                                            "Download integrator gate delta "
                                            "operator metrics JSON"
                                        ),
                                        data=_ig_d_metrics_json.encode("utf-8"),
                                        file_name=(
                                            "hermes_integrator_gate_delta_operator_metrics_"
                                            f"{_ig_delta_slug}_{_ig_delta_ts}.json"
                                        ),
                                        mime="application/json",
                                        key=(
                                            "hermes_dl_integrator_gate_delta_"
                                            "operator_metrics_json"
                                        ),
                                    )
                                with _ig_d_metrics_dl_csv_col:
                                    if _ig_d_metrics_csv:
                                        st.download_button(
                                            label=(
                                                "Download integrator gate delta "
                                                "operator metrics CSV"
                                            ),
                                            data=_ig_d_metrics_csv.encode("utf-8"),
                                            file_name=(
                                                "hermes_integrator_gate_delta_operator_metrics_"
                                                f"{_ig_delta_slug}_{_ig_delta_ts}.csv"
                                            ),
                                            mime="text/csv; charset=utf-8",
                                            key=(
                                                "hermes_dl_integrator_gate_delta_"
                                                "operator_metrics_csv"
                                            ),
                                        )
                            with st.expander(
                                "Raw integrator_gate_delta operator metrics JSON",
                                expanded=False,
                            ):
                                st.json(_ig_d_m)
                        _ig_delta_csv = integrator_gate_delta_summary_rows_csv(_ig_delta_rows)
                        _ig_delta_json = integrator_gate_delta_export_json(_ig_delta)
                        _ig_delta_dl_col, _ig_delta_dl_json_col = st.columns(2)
                        with _ig_delta_dl_col:
                            st.download_button(
                                label="Download integrator gate delta CSV",
                                data=_ig_delta_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_delta_"
                                    f"{_ig_delta_slug}_{_ig_delta_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_integrator_gate_delta_csv",
                            )
                        with _ig_delta_dl_json_col:
                            st.download_button(
                                label="Download integrator gate delta JSON",
                                data=_ig_delta_json.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_delta_"
                                    f"{_ig_delta_slug}_{_ig_delta_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_integrator_gate_delta_json",
                            )
                        with st.expander("Raw integrator_gate_delta JSON", expanded=False):
                            st.json(_ig_delta)
                _pa = persona_assignment_from_timeline(data)
                _pa_rows = persona_assignment_summary_rows(_pa)
                with st.expander("Persona assignment (from timeline)", expanded=False):
                    if not _pa_rows:
                        st.caption(
                            "No persona_assignment on this timeline (create_run did not "
                            "set business_area_persona_id / development_role_persona_id)."
                        )
                    else:
                        st.caption(
                            "Frozen composite persona from the first run.created "
                            "(same top-level persona_assignment as GET …/timeline)."
                        )
                        _pa_cap = persona_assignment_caption(_pa)
                        if _pa_cap:
                            st.caption(_pa_cap)
                        st.dataframe(_pa_rows, use_container_width=True)
                        _pa_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _pa_slug = run_id.strip().replace("/", "_")[:36] or "run"
                        _pa_csv = persona_assignment_timeline_table_rows_csv(_pa_rows)
                        _pa_json = persona_assignment_timeline_export_json(_pa)
                        _pa_dl_col, _pa_dl_json_col = st.columns(2)
                        with _pa_dl_col:
                            st.download_button(
                                label="Download persona assignment CSV",
                                data=_pa_csv.encode("utf-8"),
                                file_name=f"hermes_persona_assignment_{_pa_slug}_{_pa_ts}.csv",
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_persona_assignment_csv",
                            )
                        with _pa_dl_json_col:
                            st.download_button(
                                label="Download persona assignment JSON",
                                data=_pa_json.encode("utf-8"),
                                file_name=f"hermes_persona_assignment_{_pa_slug}_{_pa_ts}.json",
                                mime="application/json",
                                key="hermes_dl_persona_assignment_json",
                            )
                _ae = agent_evaluator_from_timeline(data)
                _ae_rows = agent_evaluator_summary_rows(_ae)
                with st.expander("Agent evaluator (from timeline)", expanded=False):
                    if not _ae_rows:
                        st.caption(
                            "No agent_evaluator summary on this timeline (no agent-evaluator "
                            "stage.started yet, or evaluator disabled for this run)."
                        )
                    else:
                        st.caption(
                            "Latest agent-evaluator stage.started summary (same top-level "
                            "agent_evaluator as GET …/timeline)."
                        )
                        _ae_session_cap = agent_evaluator_session_caption(_ae)
                        if _ae_session_cap:
                            st.caption(_ae_session_cap)
                        _ae_eval_cap = agent_evaluator_evaluation_caption(_ae)
                        if _ae_eval_cap:
                            st.caption(_ae_eval_cap)
                        _ae_actions_cap = agent_evaluator_auto_actions_caption(_ae)
                        if _ae_actions_cap:
                            st.caption(_ae_actions_cap)
                        _ae_metrics = agent_evaluator_operator_metrics(_ae)
                        _ae_metrics_cap = agent_evaluator_operator_metrics_caption(_ae_metrics)
                        if _ae_metrics_cap:
                            st.caption(_ae_metrics_cap)
                        _ae_metric_rows = agent_evaluator_operator_metrics_table_rows(
                            _ae_metrics,
                        )
                        _ae_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _ae_slug = agent_evaluator_timeline_export_filename_slug(run_id.strip())
                        if _ae_metric_rows:
                            st.dataframe(
                                _ae_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _ae_metrics_json = agent_evaluator_operator_metrics_export_json(
                                _ae_metrics,
                            )
                            _ae_metrics_csv = agent_evaluator_operator_metrics_table_rows_csv(
                                _ae_metric_rows,
                            )
                            (
                                _ae_metrics_dl_json_col,
                                _ae_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _ae_metrics_dl_json_col:
                                st.download_button(
                                    label="Download agent evaluator operator metrics JSON",
                                    data=_ae_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_agent_evaluator_operator_metrics_"
                                        f"{_ae_slug}_{_ae_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_agent_evaluator_operator_metrics_json",
                                )
                            with _ae_metrics_dl_csv_col:
                                if _ae_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download agent evaluator operator "
                                            "metrics CSV"
                                        ),
                                        data=_ae_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_agent_evaluator_operator_metrics_"
                                            f"{_ae_slug}_{_ae_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_agent_evaluator_operator_metrics_csv",
                                    )
                        st.dataframe(_ae_rows, use_container_width=True)
                        _ae_action_rows = agent_evaluator_auto_actions_table_rows(_ae)
                        if _ae_action_rows:
                            st.caption("Auto-promote / auto-create (flattened timeline fields)")
                            st.dataframe(_ae_action_rows, use_container_width=True)
                        _ae_csv = agent_evaluator_timeline_table_rows_csv(_ae)
                        _ae_json = agent_evaluator_timeline_export_json(_ae)
                        _ae_dl_col, _ae_dl_json_col = st.columns(2)
                        with _ae_dl_col:
                            st.download_button(
                                label="Download agent evaluator timeline CSV",
                                data=_ae_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_agent_evaluator_timeline_"
                                    f"{_ae_slug}_{_ae_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_agent_evaluator_timeline_csv",
                            )
                        with _ae_dl_json_col:
                            st.download_button(
                                label="Download agent evaluator timeline JSON",
                                data=_ae_json.encode("utf-8"),
                                file_name=(
                                    "hermes_agent_evaluator_timeline_"
                                    f"{_ae_slug}_{_ae_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_agent_evaluator_timeline_json",
                            )
                        with st.expander("Raw agent_evaluator JSON", expanded=False):
                            st.json(_ae)
                _sr = self_refinement_from_timeline(data)
                _sr_rows = self_refinement_summary_rows(_sr)
                with st.expander("Self-refinement (from timeline)", expanded=False):
                    if not _sr_rows:
                        st.caption(
                            "No self_refinement summary on this timeline (no "
                            "self_refinement:policy stage.started yet, or self-refinement "
                            "disabled for this run)."
                        )
                    else:
                        st.caption(
                            "Latest self-refinement policy marker summary (same top-level "
                            "self_refinement as GET …/timeline)."
                        )
                        st.dataframe(_sr_rows, use_container_width=True)
                        _sr_ver_att = self_refinement_version_attempt_caption(_sr)
                        if _sr_ver_att:
                            st.caption(_sr_ver_att)
                        _sr_expl = self_refinement_workflow_explainer_payload(
                            Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve(),
                            workflow_profile=_wf_pick,
                        )
                        _sr_att_cap = self_refinement_policy_attempt_caption(_sr, _sr_expl)
                        if _sr_att_cap:
                            st.caption(_sr_att_cap)
                        _sr_ver_cap = self_refinement_timeline_policy_version_caption(
                            _sr,
                            _sr_expl,
                        )
                        if _sr_ver_cap:
                            st.caption(_sr_ver_cap)
                        _sr_stage = self_refinement_stage_name_caption(_sr)
                        if _sr_stage:
                            st.caption(_sr_stage)
                        _sr_eval_cap = self_refinement_evaluation_caption(_sr)
                        if _sr_eval_cap:
                            st.caption(_sr_eval_cap)
                        _sr_iter_cap = self_refinement_iteration_caption(_sr)
                        if _sr_iter_cap:
                            st.caption(_sr_iter_cap)
                        _sr_promo_cap = self_refinement_auto_promote_caption(_sr)
                        if _sr_promo_cap:
                            st.caption(_sr_promo_cap)
                        _sr_prior_cap = self_refinement_prior_gate_verdict_caption(_sr)
                        if _sr_prior_cap:
                            st.caption(_sr_prior_cap)
                        _sr_phase_d_cap = self_refinement_phase_d_signal_caption(_sr)
                        if _sr_phase_d_cap:
                            st.caption(_sr_phase_d_cap)
                        _sr_llm_crit_cap = self_refinement_llm_critique_stage_caption(_sr)
                        if _sr_llm_crit_cap:
                            st.caption(_sr_llm_crit_cap)
                        _sr_ungated_cap = self_refinement_ungated_loop_caption(_sr)
                        if _sr_ungated_cap:
                            st.caption(_sr_ungated_cap)
                        _sr_latest_ts = datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ",
                        )
                        _sr_latest_slug = self_refinement_latest_export_filename_slug(
                            run_id.strip(),
                        )
                        _sr_m = self_refinement_timeline_operator_metrics(_sr)
                        if _sr_m.get("present"):
                            _sr_m_rows = self_refinement_timeline_metrics_table_rows(_sr_m)
                            st.caption(
                                "Operator metrics on the **same** marker payload: "
                                "description length, capped preview, version/attempt hints."
                            )
                            st.dataframe(
                                _sr_m_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            if _sr_m_rows:
                                _sr_metrics_json = (
                                    self_refinement_timeline_operator_metrics_export_json(
                                        _sr_m,
                                    )
                                )
                                _sr_metrics_csv = (
                                    self_refinement_timeline_operator_metrics_table_rows_csv(
                                        _sr_m_rows,
                                    )
                                )
                                _sr_metrics_dl_json_col, _sr_metrics_dl_csv_col = st.columns(2)
                                with _sr_metrics_dl_json_col:
                                    st.download_button(
                                        label=(
                                            "Download self-refinement timeline "
                                            "operator metrics JSON"
                                        ),
                                        data=_sr_metrics_json.encode("utf-8"),
                                        file_name=(
                                            "hermes_self_refinement_timeline_operator_metrics_"
                                            f"{_sr_latest_slug}_{_sr_latest_ts}.json"
                                        ),
                                        mime="application/json",
                                        key=(
                                            "hermes_dl_self_refinement_timeline_"
                                            "operator_metrics_json"
                                        ),
                                    )
                                with _sr_metrics_dl_csv_col:
                                    if _sr_metrics_csv:
                                        st.download_button(
                                            label=(
                                                "Download self-refinement timeline "
                                                "operator metrics CSV"
                                            ),
                                            data=_sr_metrics_csv.encode("utf-8"),
                                            file_name=(
                                                "hermes_self_refinement_timeline_operator_metrics_"
                                                f"{_sr_latest_slug}_{_sr_latest_ts}.csv"
                                            ),
                                            mime="text/csv; charset=utf-8",
                                            key=(
                                                "hermes_dl_self_refinement_timeline_"
                                                "operator_metrics_csv"
                                            ),
                                        )
                            _sr_session = self_refinement_session_caption(_sr)
                            if _sr_session:
                                st.caption(_sr_session)
                            _sr_first_last = self_refinement_marker_first_last_caption(_sr)
                            if _sr_first_last:
                                st.caption(_sr_first_last)
                            _sr_avg_int = self_refinement_marker_avg_interval_caption(_sr)
                            if _sr_avg_int:
                                st.caption(_sr_avg_int)
                            _sr_per_min = self_refinement_markers_per_minute_caption(_sr)
                            if _sr_per_min:
                                st.caption(_sr_per_min)
                            _sr_window = self_refinement_marker_window_caption(_sr)
                            if _sr_window:
                                st.caption(_sr_window)
                            _sr_desc_len = self_refinement_description_length_caption(_sr)
                            if _sr_desc_len:
                                st.caption(_sr_desc_len)
                            with st.expander(
                                "Raw self_refinement timeline operator metrics JSON",
                                expanded=False,
                            ):
                                st.json(_sr_m)
                        _sr_latest_csv = self_refinement_latest_summary_rows_csv(_sr_rows)
                        _sr_latest_json = self_refinement_latest_export_json(_sr)
                        _sr_latest_dl_col, _sr_latest_dl_json_col = st.columns(2)
                        with _sr_latest_dl_col:
                            st.download_button(
                                label="Download self-refinement latest CSV",
                                data=_sr_latest_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_self_refinement_latest_"
                                    f"{_sr_latest_slug}_{_sr_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_self_refinement_latest_csv",
                            )
                        with _sr_latest_dl_json_col:
                            st.download_button(
                                label="Download self-refinement latest JSON",
                                data=_sr_latest_json.encode("utf-8"),
                                file_name=(
                                    "hermes_self_refinement_latest_"
                                    f"{_sr_latest_slug}_{_sr_latest_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_self_refinement_latest_json",
                            )
                        with st.expander("Raw self_refinement JSON", expanded=False):
                            st.json(_sr)
                _sr_marker_hist = self_refinement_marker_history_from_timeline(data)
                _sr_marker_hist_rows = self_refinement_marker_history_table_rows(
                    _sr_marker_hist,
                )
                with st.expander(
                    "Self-refinement marker history (from timeline)",
                    expanded=False,
                ):
                    if not _sr_marker_hist_rows:
                        st.caption(
                            "No ``self_refinement_marker_history`` on this timeline "
                            "(no self_refinement:policy stage.started markers yet)."
                        )
                    else:
                        st.caption(
                            "Chronological policy markers (bounded on the API; latest "
                            "summary matches **Self-refinement** above)."
                        )
                        _sr_marker_hist_cap = (
                            self_refinement_marker_history_entry_count_caption(
                                _sr_marker_hist,
                            )
                        )
                        if _sr_marker_hist_cap:
                            st.caption(_sr_marker_hist_cap)
                        _sr_marker_hist_metrics = (
                            self_refinement_marker_history_operator_metrics(
                                _sr_marker_hist,
                            )
                        )
                        _sr_marker_hist_metrics_cap = (
                            self_refinement_marker_history_operator_metrics_caption(
                                _sr_marker_hist_metrics,
                            )
                        )
                        if _sr_marker_hist_metrics_cap:
                            st.caption(_sr_marker_hist_metrics_cap)
                        _sr_marker_hist_metric_rows = (
                            self_refinement_marker_history_operator_metrics_table_rows(
                                _sr_marker_hist_metrics,
                            )
                        )
                        _sr_marker_hist_ts = datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ",
                        )
                        _sr_marker_hist_slug = (
                            self_refinement_marker_history_export_filename_slug(
                                run_id.strip(),
                            )
                        )
                        if _sr_marker_hist_metric_rows:
                            st.dataframe(
                                _sr_marker_hist_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _sr_marker_hist_metrics_json = (
                                self_refinement_marker_history_operator_metrics_export_json(
                                    _sr_marker_hist_metrics,
                                )
                            )
                            _sr_marker_hist_metrics_csv = (
                                self_refinement_marker_history_operator_metrics_table_rows_csv(
                                    _sr_marker_hist_metric_rows,
                                )
                            )
                            (
                                _sr_marker_hist_metrics_dl_json_col,
                                _sr_marker_hist_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _sr_marker_hist_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download self-refinement marker history "
                                        "operator metrics JSON"
                                    ),
                                    data=_sr_marker_hist_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_self_refinement_marker_history_operator_metrics_"
                                        f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.json"
                                    ),
                                    mime="application/json",
                                    key=(
                                        "hermes_dl_self_refinement_marker_history_"
                                        "operator_metrics_json"
                                    ),
                                )
                            with _sr_marker_hist_metrics_dl_csv_col:
                                if _sr_marker_hist_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download self-refinement marker history "
                                            "operator metrics CSV"
                                        ),
                                        data=_sr_marker_hist_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_self_refinement_marker_history_operator_metrics_"
                                            f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key=(
                                            "hermes_dl_self_refinement_marker_history_"
                                            "operator_metrics_csv"
                                        ),
                                    )
                        st.dataframe(_sr_marker_hist_rows, use_container_width=True)
                        _sr_marker_hist_csv = self_refinement_marker_history_table_rows_csv(
                            _sr_marker_hist_rows,
                        )
                        _sr_marker_hist_json = self_refinement_marker_history_export_json(
                            _sr_marker_hist,
                        )
                        _sr_marker_dl_col, _sr_marker_dl_json_col = st.columns(2)
                        with _sr_marker_dl_col:
                            st.download_button(
                                label="Download marker history CSV",
                                data=_sr_marker_hist_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_self_refinement_marker_history_"
                                    f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_self_refinement_marker_history_csv",
                            )
                        with _sr_marker_dl_json_col:
                            st.download_button(
                                label="Download marker history JSON",
                                data=_sr_marker_hist_json.encode("utf-8"),
                                file_name=(
                                    "hermes_self_refinement_marker_history_"
                                    f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_self_refinement_marker_history_json",
                            )
                        with st.expander(
                            "Raw self_refinement_marker_history JSON",
                            expanded=False,
                        ):
                            st.json(_sr_marker_hist)
                _re = run_escalated_from_timeline(data)
                _re_rows = run_escalated_summary_rows(_re)
                with st.expander("Run escalated (from timeline)", expanded=False):
                    if not _re_rows:
                        st.caption(
                            "No run_escalated summary on this timeline (no run.escalated "
                            "events yet)."
                        )
                    else:
                        st.caption(
                            "Latest run.escalated summary (same top-level run_escalated as "
                            "GET …/timeline)."
                        )
                        st.dataframe(_re_rows, use_container_width=True)
                        _re_reason_cap = run_escalated_reason_summary_caption(_re)
                        if _re_reason_cap:
                            st.caption(_re_reason_cap)
                        _re_at_cap = run_escalated_occurred_at_caption(_re)
                        if _re_at_cap:
                            st.caption(_re_at_cap)
                        _re_event_cap = run_escalated_event_id_caption(_re)
                        if _re_event_cap:
                            st.caption(_re_event_cap)
                        _re_notes_cap = run_escalated_notes_preview_caption(_re)
                        if _re_notes_cap:
                            st.caption(_re_notes_cap)
                        _re_root = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
                        _re_cap = run_escalated_policy_cross_ref_caption(_re_root, _re)
                        if _re_cap:
                            st.caption(_re_cap)
                        _re_actor_notes = run_escalated_actor_without_notes_caption(_re)
                        if _re_actor_notes:
                            st.caption(_re_actor_notes)
                        _re_metrics = run_escalated_operator_metrics(_re)
                        _re_metrics_cap = run_escalated_operator_metrics_caption(
                            _re_metrics,
                        )
                        if _re_metrics_cap:
                            st.caption(_re_metrics_cap)
                        _re_metric_rows = run_escalated_operator_metrics_table_rows(
                            _re_metrics,
                        )
                        _re_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _re_slug = run_escalated_export_filename_slug(run_id.strip())
                        if _re_metric_rows:
                            st.dataframe(
                                _re_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _re_metrics_json = run_escalated_operator_metrics_export_json(
                                _re_metrics,
                            )
                            _re_metrics_csv = (
                                run_escalated_operator_metrics_table_rows_csv(
                                    _re_metric_rows,
                                )
                            )
                            _re_metrics_dl_json_col, _re_metrics_dl_csv_col = st.columns(2)
                            with _re_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download run escalated operator "
                                        "metrics JSON"
                                    ),
                                    data=_re_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_run_escalated_operator_metrics_"
                                        f"{_re_slug}_{_re_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_run_escalated_operator_metrics_json",
                                )
                            with _re_metrics_dl_csv_col:
                                if _re_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download run escalated operator "
                                            "metrics CSV"
                                        ),
                                        data=_re_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_run_escalated_operator_metrics_"
                                            f"{_re_slug}_{_re_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_run_escalated_operator_metrics_csv",
                                    )
                        _re_sum_csv = run_escalated_summary_rows_csv(_re_rows)
                        _re_sum_json = run_escalated_export_json(_re)
                        _re_sum_dl_col, _re_sum_dl_json_col = st.columns(2)
                        with _re_sum_dl_col:
                            if _re_sum_csv:
                                st.download_button(
                                    label="Download run escalated summary CSV",
                                    data=_re_sum_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_run_escalated_summary_"
                                        f"{_re_slug}_{_re_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_run_escalated_summary_csv",
                                )
                        with _re_sum_dl_json_col:
                            st.download_button(
                                label="Download run escalated summary JSON",
                                data=_re_sum_json.encode("utf-8"),
                                file_name=(
                                    "hermes_run_escalated_summary_"
                                    f"{_re_slug}_{_re_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_run_escalated_summary_json",
                            )
                        with st.expander("Raw run_escalated JSON", expanded=False):
                            st.json(_re)
                _re_hist = run_escalated_history_from_timeline(data)
                _re_hist_rows = run_escalated_history_table_rows(_re_hist)
                with st.expander("Run escalated history (from timeline)", expanded=False):
                    if not _re_hist_rows:
                        st.caption(
                            "No ``run_escalated_history`` on this timeline (no "
                            "run.escalated events recorded)."
                        )
                    else:
                        st.caption(
                            "Chronological ``run.escalated`` rows (bounded on the API; "
                            "latest row matches **Run escalated** summary)."
                        )
                        _re_hist_count_cap = run_escalated_history_entry_count_caption(
                            _re_hist,
                        )
                        if _re_hist_count_cap:
                            st.caption(_re_hist_count_cap)
                        _re_hist_metrics = run_escalated_history_operator_metrics(_re_hist)
                        _re_hist_metrics_cap = run_escalated_history_operator_metrics_caption(
                            _re_hist_metrics,
                        )
                        if _re_hist_metrics_cap:
                            st.caption(_re_hist_metrics_cap)
                        _re_hist_actors_cap = run_escalated_history_distinct_actors_caption(
                            _re_hist_metrics,
                        )
                        if _re_hist_actors_cap:
                            st.caption(_re_hist_actors_cap)
                        _re_hist_metric_rows = run_escalated_history_operator_metrics_table_rows(
                            _re_hist_metrics,
                        )
                        _re_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _re_hist_slug = run_escalated_history_export_filename_slug(
                            run_id.strip(),
                        )
                        if _re_hist_metric_rows:
                            st.dataframe(
                                _re_hist_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _re_hist_metrics_json = (
                                run_escalated_history_operator_metrics_export_json(
                                    _re_hist_metrics,
                                )
                            )
                            _re_hist_metrics_csv = (
                                run_escalated_history_operator_metrics_table_rows_csv(
                                    _re_hist_metric_rows,
                                )
                            )
                            (
                                _re_hist_metrics_dl_json_col,
                                _re_hist_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _re_hist_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download run escalated history operator "
                                        "metrics JSON"
                                    ),
                                    data=_re_hist_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_run_escalated_history_operator_metrics_"
                                        f"{_re_hist_slug}_{_re_hist_ts}.json"
                                    ),
                                    mime="application/json",
                                    key=(
                                        "hermes_dl_run_escalated_history_operator_"
                                        "metrics_json"
                                    ),
                                )
                            with _re_hist_metrics_dl_csv_col:
                                if _re_hist_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download run escalated history operator "
                                            "metrics CSV"
                                        ),
                                        data=_re_hist_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_run_escalated_history_operator_metrics_"
                                            f"{_re_hist_slug}_{_re_hist_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key=(
                                            "hermes_dl_run_escalated_history_operator_"
                                            "metrics_csv"
                                        ),
                                    )
                        st.dataframe(_re_hist_rows, use_container_width=True)
                        _re_hist_csv = run_escalated_history_table_rows_csv(_re_hist_rows)
                        _re_hist_json = run_escalated_history_export_json(_re_hist)
                        _re_hist_dl_col, _re_hist_dl_json_col = st.columns(2)
                        with _re_hist_dl_col:
                            st.download_button(
                                label="Download run escalated history CSV",
                                data=_re_hist_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_run_escalated_history_"
                                    f"{_re_hist_slug}_{_re_hist_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_run_escalated_history_csv",
                            )
                        with _re_hist_dl_json_col:
                            st.download_button(
                                label="Download run escalated history JSON",
                                data=_re_hist_json.encode("utf-8"),
                                file_name=(
                                    "hermes_run_escalated_history_"
                                    f"{_re_hist_slug}_{_re_hist_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_run_escalated_history_json",
                            )
                        with st.expander("Raw run_escalated_history JSON", expanded=False):
                            st.json(_re_hist)
                _re_delta = run_escalated_delta_from_timeline(data)
                with st.expander("Run escalated delta (latest vs prior)", expanded=False):
                    if not _re_delta:
                        st.caption(
                            "No ``run_escalated_delta`` — need at least two "
                            "run.escalated events on this timeline."
                        )
                    else:
                        st.caption(
                            "Diff between the last two ``run.escalated`` events "
                            "(same field as GET …/timeline ``run_escalated_delta``)."
                        )
                        _re_delta_cap = run_escalated_delta_transition_caption(_re_delta)
                        if _re_delta_cap:
                            st.caption(_re_delta_cap)
                        _re_delta_metrics = run_escalated_delta_operator_metrics(_re_delta)
                        _re_delta_metrics_cap = run_escalated_delta_operator_metrics_caption(
                            _re_delta_metrics,
                        )
                        if _re_delta_metrics_cap:
                            st.caption(_re_delta_metrics_cap)
                        _re_delta_metric_rows = run_escalated_delta_operator_metrics_table_rows(
                            _re_delta_metrics,
                        )
                        _re_delta_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _re_delta_slug = run_escalated_delta_export_filename_slug(
                            run_id.strip(),
                        )
                        if _re_delta_metric_rows:
                            st.dataframe(
                                _re_delta_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _re_delta_metrics_json = (
                                run_escalated_delta_operator_metrics_export_json(
                                    _re_delta_metrics,
                                )
                            )
                            _re_delta_metrics_csv = (
                                run_escalated_delta_operator_metrics_table_rows_csv(
                                    _re_delta_metric_rows,
                                )
                            )
                            (
                                _re_delta_metrics_dl_json_col,
                                _re_delta_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _re_delta_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download run escalated delta operator "
                                        "metrics JSON"
                                    ),
                                    data=_re_delta_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_run_escalated_delta_operator_metrics_"
                                        f"{_re_delta_slug}_{_re_delta_ts}.json"
                                    ),
                                    mime="application/json",
                                    key=(
                                        "hermes_dl_run_escalated_delta_operator_"
                                        "metrics_json"
                                    ),
                                )
                            with _re_delta_metrics_dl_csv_col:
                                if _re_delta_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download run escalated delta operator "
                                            "metrics CSV"
                                        ),
                                        data=_re_delta_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_run_escalated_delta_operator_metrics_"
                                            f"{_re_delta_slug}_{_re_delta_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key=(
                                            "hermes_dl_run_escalated_delta_operator_"
                                            "metrics_csv"
                                        ),
                                    )
                        _re_delta_sum_rows = run_escalated_delta_summary_rows(_re_delta)
                        _re_delta_csv = run_escalated_delta_table_rows_csv(_re_delta_sum_rows)
                        _re_delta_json = run_escalated_delta_export_json(_re_delta)
                        _re_delta_dl_col, _re_delta_dl_json_col = st.columns(2)
                        with _re_delta_dl_col:
                            st.download_button(
                                label="Download run escalated delta CSV",
                                data=_re_delta_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_run_escalated_delta_"
                                    f"{_re_delta_slug}_{_re_delta_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_run_escalated_delta_csv",
                            )
                        with _re_delta_dl_json_col:
                            st.download_button(
                                label="Download run escalated delta JSON",
                                data=_re_delta_json.encode("utf-8"),
                                file_name=(
                                    "hermes_run_escalated_delta_"
                                    f"{_re_delta_slug}_{_re_delta_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_run_escalated_delta_json",
                            )
                        with st.expander("Raw run_escalated_delta JSON", expanded=False):
                            st.json(_re_delta)
                _ss = security_scan_on_verify_from_timeline(data)
                _ss_rows = security_scan_on_verify_summary_rows(_ss)
                _ssm_align_payload = security_scan_metadata_workflow_explainer_payload(
                    _iroot,
                    workflow_profile=_wf_pick,
                )
                _ss_align_cap = security_scan_metadata_timeline_workflow_alignment_caption(
                    timeline_security_scan_on_verify=_ss,
                    explainer_payload=_ssm_align_payload,
                )
                with st.expander("Security scan on verify (from timeline)", expanded=False):
                    if _ss_align_cap:
                        st.caption(_ss_align_cap)
                    if not _ss_rows:
                        st.caption(
                            "No security_scan_on_verify summary on this timeline (no "
                            "finding.created with security_scan_* metadata yet)."
                        )
                    else:
                        st.caption(
                            "Latest finding.created with verifier security scan metadata "
                            "(same top-level security_scan_on_verify as GET …/timeline)."
                        )
                        st.dataframe(_ss_rows, use_container_width=True)
                        _ss_snip_len = security_scan_snippet_length_caption(_ss)
                        if _ss_snip_len:
                            st.caption(_ss_snip_len)
                        _ss_snip_lines = security_scan_snippet_line_count_caption(_ss)
                        if _ss_snip_lines:
                            st.caption(_ss_snip_lines)
                        _ss_ids_cap = security_scan_finding_event_ids_caption(_ss)
                        if _ss_ids_cap:
                            st.caption(_ss_ids_cap)
                        _ss_occ_age = security_scan_occurred_at_age_caption(_ss)
                        if _ss_occ_age:
                            st.caption(_ss_occ_age)
                        _ss_cat_sev = security_scan_category_severity_caption(_ss)
                        if _ss_cat_sev:
                            st.caption(_ss_cat_sev)
                        _ss_finding_metrics = (
                            security_scan_on_verify_latest_operator_metrics(_ss)
                        )
                        _ss_finding_metrics_cap = (
                            security_scan_on_verify_latest_operator_metrics_caption(
                                _ss_finding_metrics,
                            )
                        )
                        if _ss_finding_metrics_cap:
                            st.caption(_ss_finding_metrics_cap)
                        _ss_finding_metric_rows = (
                            security_scan_on_verify_latest_operator_metrics_table_rows(
                                _ss_finding_metrics,
                            )
                        )
                        _ss_latest_ts = datetime.now(timezone.utc).strftime(
                            "%Y%m%dT%H%M%SZ",
                        )
                        _ss_latest_slug = security_scan_on_verify_latest_export_filename_slug(
                            run_id.strip(),
                        )
                        if _ss_finding_metric_rows:
                            st.dataframe(
                                _ss_finding_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _ss_finding_metrics_json = (
                                security_scan_on_verify_latest_operator_metrics_export_json(
                                    _ss_finding_metrics,
                                )
                            )
                            _ss_finding_metrics_csv = (
                                security_scan_on_verify_latest_operator_metrics_table_rows_csv(
                                    _ss_finding_metric_rows,
                                )
                            )
                            (
                                _ss_finding_metrics_dl_json_col,
                                _ss_finding_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _ss_finding_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download security scan finding operator "
                                        "metrics JSON"
                                    ),
                                    data=_ss_finding_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_security_scan_finding_operator_metrics_"
                                        f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                                    ),
                                    mime="application/json",
                                    key=(
                                        "hermes_dl_security_scan_finding_operator_"
                                        "metrics_json"
                                    ),
                                )
                            with _ss_finding_metrics_dl_csv_col:
                                if _ss_finding_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download security scan finding operator "
                                            "metrics CSV"
                                        ),
                                        data=_ss_finding_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_security_scan_finding_operator_metrics_"
                                            f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key=(
                                            "hermes_dl_security_scan_finding_operator_"
                                            "metrics_csv"
                                        ),
                                    )
                        _ss_lint = security_scan_linter_nonzero_caption(_ss)
                        if _ss_lint:
                            st.caption(_ss_lint)
                        _ss_linter_rows = security_scan_linter_status_rows(_ss)
                        if _ss_linter_rows:
                            st.caption("Per-linter status (Ruff / Bandit)")
                            st.dataframe(
                                _ss_linter_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _ss_linter_summary = (
                                security_scan_linter_status_summary_caption(_ss)
                            )
                            if _ss_linter_summary:
                                st.caption(_ss_linter_summary)
                            _ss_worst = security_scan_linter_worst_status_caption(_ss)
                            if _ss_worst:
                                st.caption(_ss_worst)
                            _ss_exits = security_scan_linter_exit_codes_caption(_ss)
                            if _ss_exits:
                                st.caption(_ss_exits)
                            _ss_failed = security_scan_linter_failed_linters_caption(_ss)
                            if _ss_failed:
                                st.caption(_ss_failed)
                            _ss_ok = security_scan_linter_ok_linters_caption(_ss)
                            if _ss_ok:
                                st.caption(_ss_ok)
                            _ss_missing = security_scan_linter_missing_linters_caption(_ss)
                            if _ss_missing:
                                st.caption(_ss_missing)
                            _ss_latest_ts = datetime.now(timezone.utc).strftime(
                                "%Y%m%dT%H%M%SZ",
                            )
                            _ss_latest_slug = (
                                security_scan_on_verify_latest_export_filename_slug(
                                    run_id.strip(),
                                )
                            )
                            _ss_linter_metrics = security_scan_linter_operator_metrics(_ss)
                            _ss_linter_metrics_cap = security_scan_linter_operator_metrics_caption(
                                _ss_linter_metrics,
                            )
                            if _ss_linter_metrics_cap:
                                st.caption(_ss_linter_metrics_cap)
                            _ss_linter_metric_rows = (
                                security_scan_linter_operator_metrics_table_rows(
                                    _ss_linter_metrics,
                                )
                            )
                            if _ss_linter_metric_rows:
                                st.dataframe(
                                    _ss_linter_metric_rows,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                _ss_linter_metrics_json = (
                                    security_scan_linter_operator_metrics_export_json(
                                        _ss_linter_metrics,
                                    )
                                )
                                _ss_linter_metrics_csv = (
                                    security_scan_linter_operator_metrics_table_rows_csv(
                                        _ss_linter_metric_rows,
                                    )
                                )
                                _ss_linter_metrics_dl_json_col, _ss_linter_metrics_dl_csv_col = (
                                    st.columns(2)
                                )
                                with _ss_linter_metrics_dl_json_col:
                                    st.download_button(
                                        label=(
                                            "Download security scan linter "
                                            "operator metrics JSON"
                                        ),
                                        data=_ss_linter_metrics_json.encode("utf-8"),
                                        file_name=(
                                            "hermes_security_scan_linter_operator_metrics_"
                                            f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                                        ),
                                        mime="application/json",
                                        key=(
                                            "hermes_dl_security_scan_linter_"
                                            "operator_metrics_json"
                                        ),
                                    )
                                with _ss_linter_metrics_dl_csv_col:
                                    if _ss_linter_metrics_csv:
                                        st.download_button(
                                            label=(
                                                "Download security scan linter "
                                                "operator metrics CSV"
                                            ),
                                            data=_ss_linter_metrics_csv.encode("utf-8"),
                                            file_name=(
                                                "hermes_security_scan_linter_operator_metrics_"
                                                f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                                            ),
                                            mime="text/csv; charset=utf-8",
                                            key=(
                                                "hermes_dl_security_scan_linter_"
                                                "operator_metrics_csv"
                                            ),
                                        )
                            with st.expander(
                                "Raw linter operator metrics JSON",
                                expanded=False,
                            ):
                                st.json(_ss_linter_metrics)
                        _ss_latest_csv = security_scan_on_verify_latest_summary_rows_csv(
                            _ss_rows,
                        )
                        _ss_latest_json = security_scan_on_verify_latest_export_json(_ss)
                        _ss_latest_dl_col, _ss_latest_dl_json_col = st.columns(2)
                        with _ss_latest_dl_col:
                            st.download_button(
                                label="Download security scan on verify latest CSV",
                                data=_ss_latest_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_security_scan_on_verify_latest_"
                                    f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_security_scan_on_verify_latest_csv",
                            )
                        with _ss_latest_dl_json_col:
                            st.download_button(
                                label="Download security scan on verify latest JSON",
                                data=_ss_latest_json.encode("utf-8"),
                                file_name=(
                                    "hermes_security_scan_on_verify_latest_"
                                    f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_security_scan_on_verify_latest_json",
                            )
                        with st.expander("Raw security_scan_on_verify JSON", expanded=False):
                            st.json(_ss)
                _ss_hist = security_scan_history_from_timeline(data)
                _ss_hist_rows = security_scan_history_table_rows(_ss_hist)
                with st.expander(
                    "Security scan history (from timeline)",
                    expanded=False,
                ):
                    if not _ss_hist_rows:
                        st.caption(
                            "No ``security_scan_on_verify_history`` on this timeline "
                            "(no finding.created with security_scan_* metadata yet)."
                        )
                    else:
                        st.caption(
                            "Chronological verifier scan findings (bounded on the API; "
                            "latest row matches **Security scan on verify** summary)."
                        )
                        _ss_hist_cap = security_scan_history_entry_count_caption(_ss_hist)
                        if _ss_hist_cap:
                            st.caption(_ss_hist_cap)
                        _ss_hist_metrics = security_scan_history_operator_metrics(_ss_hist)
                        _ss_hist_metrics_cap = security_scan_history_operator_metrics_caption(
                            _ss_hist_metrics,
                        )
                        if _ss_hist_metrics_cap:
                            st.caption(_ss_hist_metrics_cap)
                        _ss_hist_sev_cap = security_scan_history_severity_sample_caption(
                            _ss_hist,
                        )
                        if _ss_hist_sev_cap:
                            st.caption(_ss_hist_sev_cap)
                        _ss_hist_metric_rows = security_scan_history_operator_metrics_table_rows(
                            _ss_hist_metrics,
                        )
                        _ss_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _ss_hist_slug = security_scan_history_export_filename_slug(
                            run_id.strip(),
                        )
                        if _ss_hist_metric_rows:
                            st.dataframe(
                                _ss_hist_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _ss_hist_metrics_json = (
                                security_scan_history_operator_metrics_export_json(
                                    _ss_hist_metrics,
                                )
                            )
                            _ss_hist_metrics_csv = (
                                security_scan_history_operator_metrics_table_rows_csv(
                                    _ss_hist_metric_rows,
                                )
                            )
                            (
                                _ss_hist_metrics_dl_json_col,
                                _ss_hist_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _ss_hist_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download security scan history operator "
                                        "metrics JSON"
                                    ),
                                    data=_ss_hist_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_security_scan_history_operator_metrics_"
                                        f"{_ss_hist_slug}_{_ss_hist_ts}.json"
                                    ),
                                    mime="application/json",
                                    key=(
                                        "hermes_dl_security_scan_history_operator_"
                                        "metrics_json"
                                    ),
                                )
                            with _ss_hist_metrics_dl_csv_col:
                                if _ss_hist_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download security scan history operator "
                                            "metrics CSV"
                                        ),
                                        data=_ss_hist_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_security_scan_history_operator_metrics_"
                                            f"{_ss_hist_slug}_{_ss_hist_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key=(
                                            "hermes_dl_security_scan_history_operator_"
                                            "metrics_csv"
                                        ),
                                    )
                        st.dataframe(_ss_hist_rows, use_container_width=True)
                        _ss_hist_csv = security_scan_history_table_rows_csv(_ss_hist_rows)
                        _ss_hist_json = security_scan_history_export_json(_ss_hist)
                        _ss_hist_dl_col, _ss_hist_dl_json_col = st.columns(2)
                        with _ss_hist_dl_col:
                            st.download_button(
                                label="Download security scan history CSV",
                                data=_ss_hist_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_security_scan_history_{_ss_hist_slug}_{_ss_hist_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_security_scan_history_csv",
                            )
                        with _ss_hist_dl_json_col:
                            st.download_button(
                                label="Download security scan history JSON",
                                data=_ss_hist_json.encode("utf-8"),
                                file_name=(
                                    f"hermes_security_scan_history_{_ss_hist_slug}_{_ss_hist_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_security_scan_history_json",
                            )
                        with st.expander(
                            "Raw security_scan_on_verify_history JSON",
                            expanded=False,
                        ):
                            st.json(_ss_hist)
                _uc_tl = universal_critique_from_timeline(data)
                _uc_tl_rows = universal_critique_timeline_stage_rows(_uc_tl)
                with st.expander("Universal critique (from timeline)", expanded=False):
                    if not _uc_tl_rows:
                        st.caption(
                            "No universal_critique summary on this timeline (no "
                            "``*.critique`` gate.decision.emitted events yet)."
                        )
                    else:
                        st.caption(
                            "Latest gate decision per critique stage (same top-level "
                            "universal_critique as GET …/timeline)."
                        )
                        _uc_tl_fail_cap = universal_critique_timeline_fail_count_caption(
                            _uc_tl,
                        )
                        if _uc_tl_fail_cap:
                            st.caption(_uc_tl_fail_cap)
                        _uc_tl_metrics = universal_critique_timeline_operator_metrics(_uc_tl)
                        _uc_tl_metrics_cap = (
                            universal_critique_timeline_operator_metrics_caption(
                                _uc_tl_metrics,
                            )
                        )
                        if _uc_tl_metrics_cap:
                            st.caption(_uc_tl_metrics_cap)
                        _uc_tl_metric_rows = (
                            universal_critique_timeline_operator_metrics_table_rows(
                                _uc_tl_metrics,
                            )
                        )
                        _uc_tl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _uc_tl_slug = universal_critique_timeline_export_filename_slug(
                            run_id.strip(),
                        )
                        if _uc_tl_metric_rows:
                            st.dataframe(
                                _uc_tl_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _uc_tl_metrics_json = (
                                universal_critique_timeline_operator_metrics_export_json(
                                    _uc_tl_metrics,
                                )
                            )
                            _uc_tl_metrics_csv = (
                                universal_critique_timeline_operator_metrics_table_rows_csv(
                                    _uc_tl_metric_rows,
                                )
                            )
                            (
                                _uc_tl_metrics_dl_json_col,
                                _uc_tl_metrics_dl_csv_col,
                            ) = st.columns(2)
                            with _uc_tl_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download universal critique operator "
                                        "metrics JSON"
                                    ),
                                    data=_uc_tl_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_universal_critique_operator_metrics_"
                                        f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                                    ),
                                    mime="application/json",
                                    key=(
                                        "hermes_dl_universal_critique_operator_"
                                        "metrics_json"
                                    ),
                                )
                            with _uc_tl_metrics_dl_csv_col:
                                if _uc_tl_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download universal critique operator "
                                            "metrics CSV"
                                        ),
                                        data=_uc_tl_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_universal_critique_operator_metrics_"
                                            f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key=(
                                            "hermes_dl_universal_critique_operator_"
                                            "metrics_csv"
                                        ),
                                    )
                        st.dataframe(_uc_tl_rows, use_container_width=True)
                        _uc_tl_fail_rows = universal_critique_timeline_fail_stage_rows(_uc_tl)
                        _uc_tl_fail_cap_stages = universal_critique_timeline_fail_stage_caption(
                            _uc_tl,
                        )
                        if _uc_tl_fail_cap_stages:
                            st.caption(_uc_tl_fail_cap_stages)
                        if _uc_tl_fail_rows:
                            st.caption("FAIL stages only (subset of table above)")
                            st.dataframe(
                                _uc_tl_fail_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                        _uc_tl_json = universal_critique_timeline_export_json(_uc_tl)
                        _uc_stages_csv = universal_critique_timeline_stage_rows_csv(
                            _uc_tl_rows,
                        )
                        if _uc_tl_fail_rows:
                            _uc_fail_csv = universal_critique_fail_stage_rows_csv(_uc_tl_fail_rows)
                            (
                                _uc_dl_stages_col,
                                _uc_dl_csv_col,
                                _uc_dl_json_col,
                            ) = st.columns(3)
                            with _uc_dl_stages_col:
                                st.download_button(
                                    label="Download universal critique all stages CSV",
                                    data=_uc_stages_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_universal_critique_stages_"
                                        f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_universal_critique_stages_csv",
                                )
                            with _uc_dl_csv_col:
                                st.download_button(
                                    label="Download universal critique FAIL stages CSV",
                                    data=_uc_fail_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_universal_critique_fail_stages_"
                                        f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_universal_critique_fail_csv",
                                )
                            with _uc_dl_json_col:
                                st.download_button(
                                    label="Download universal critique timeline JSON",
                                    data=_uc_tl_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_universal_critique_timeline_"
                                        f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_universal_critique_timeline_json",
                                )
                        else:
                            _uc_dl_stages_col, _uc_dl_json_col = st.columns(2)
                            with _uc_dl_stages_col:
                                st.download_button(
                                    label="Download universal critique all stages CSV",
                                    data=_uc_stages_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_universal_critique_stages_"
                                        f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_universal_critique_stages_csv",
                                )
                            with _uc_dl_json_col:
                                st.download_button(
                                    label="Download universal critique timeline JSON",
                                    data=_uc_tl_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_universal_critique_timeline_"
                                        f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_universal_critique_timeline_json",
                                )
                        with st.expander("Raw universal_critique JSON", expanded=False):
                            st.json(_uc_tl)
                _sf = scraper_fetch_from_timeline(data)
                _sf_rows = scraper_fetch_summary_rows(_sf)
                with st.expander("Scraper fetch (from timeline)", expanded=False):
                    if not _sf_rows:
                        st.caption(
                            "No scraper_fetch summary on this timeline (no terminal "
                            "scraper:fetch stage.passed / stage.failed yet)."
                        )
                    else:
                        st.caption(
                            "Latest scraper:fetch terminal stage summary (same top-level "
                            "scraper_fetch as GET …/timeline)."
                        )
                        _sf_outcome_cap = scraper_fetch_outcome_caption(_sf)
                        if _sf_outcome_cap:
                            st.caption(_sf_outcome_cap)
                        _sf_fail_cap = scraper_fetch_failure_reason_caption(_sf)
                        if _sf_fail_cap:
                            st.caption(_sf_fail_cap)
                        _sf_metrics = scraper_fetch_operator_metrics(_sf)
                        _sf_metrics_cap = scraper_fetch_operator_metrics_caption(_sf_metrics)
                        if _sf_metrics_cap:
                            st.caption(_sf_metrics_cap)
                        _sf_metric_rows = scraper_fetch_operator_metrics_table_rows(
                            _sf_metrics,
                        )
                        _sf_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _sf_sum_slug = scraper_fetch_summary_export_filename_slug(
                            run_id.strip(),
                        )
                        if _sf_metric_rows:
                            st.dataframe(
                                _sf_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _sf_metrics_json = scraper_fetch_operator_metrics_export_json(
                                _sf_metrics,
                            )
                            _sf_metrics_csv = scraper_fetch_operator_metrics_table_rows_csv(
                                _sf_metric_rows,
                            )
                            _sf_metrics_dl_json_col, _sf_metrics_dl_csv_col = st.columns(2)
                            with _sf_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download scraper fetch operator "
                                        "metrics JSON"
                                    ),
                                    data=_sf_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_scraper_fetch_operator_metrics_"
                                        f"{_sf_sum_slug}_{_sf_sum_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_scraper_fetch_operator_metrics_json",
                                )
                            with _sf_metrics_dl_csv_col:
                                if _sf_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download scraper fetch operator "
                                            "metrics CSV"
                                        ),
                                        data=_sf_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_scraper_fetch_operator_metrics_"
                                            f"{_sf_sum_slug}_{_sf_sum_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_scraper_fetch_operator_metrics_csv",
                                    )
                        st.dataframe(_sf_rows, use_container_width=True)
                        _sf_fetch_rows = scraper_fetch_fetches_table_rows(_sf)
                        if _sf_fetch_rows:
                            st.caption("Per-URL fetches (from timeline ``scraper_fetch.fetches``)")
                            _sf_artifacts_cap = scraper_fetch_artifacts_caption(_sf)
                            if _sf_artifacts_cap:
                                st.caption(_sf_artifacts_cap)
                            st.dataframe(_sf_fetch_rows, use_container_width=True)
                            _sf_fetch_ts = datetime.now(timezone.utc).strftime(
                                "%Y%m%dT%H%M%SZ",
                            )
                            _sf_fetch_slug = scraper_fetch_fetches_export_filename_slug(
                                run_id.strip(),
                            )
                            _sf_fetch_csv = scraper_fetch_fetches_table_rows_csv(
                                _sf_fetch_rows,
                            )
                            _sf_fetch_json = scraper_fetch_fetches_export_json(_sf)
                            _sf_fetch_dl_col, _sf_fetch_dl_json_col = st.columns(2)
                            with _sf_fetch_dl_col:
                                st.download_button(
                                    label="Download scraper fetches CSV",
                                    data=_sf_fetch_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_scraper_fetch_fetches_"
                                        f"{_sf_fetch_slug}_{_sf_fetch_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_scraper_fetch_fetches_csv",
                                )
                            with _sf_fetch_dl_json_col:
                                st.download_button(
                                    label="Download scraper fetches JSON",
                                    data=_sf_fetch_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_scraper_fetch_fetches_"
                                        f"{_sf_fetch_slug}_{_sf_fetch_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_scraper_fetch_fetches_json",
                                )
                        _sf_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _sf_sum_slug = scraper_fetch_summary_export_filename_slug(
                            run_id.strip(),
                        )
                        _sf_sum_csv = scraper_fetch_summary_rows_csv(_sf_rows)
                        _sf_sum_json = scraper_fetch_summary_export_json(_sf)
                        _sf_sum_dl_col, _sf_sum_dl_json_col = st.columns(2)
                        with _sf_sum_dl_col:
                            st.download_button(
                                label="Download scraper fetch summary CSV",
                                data=_sf_sum_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_scraper_fetch_summary_"
                                    f"{_sf_sum_slug}_{_sf_sum_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_scraper_fetch_summary_csv",
                            )
                        with _sf_sum_dl_json_col:
                            st.download_button(
                                label="Download scraper fetch summary JSON",
                                data=_sf_sum_json.encode("utf-8"),
                                file_name=(
                                    "hermes_scraper_fetch_summary_"
                                    f"{_sf_sum_slug}_{_sf_sum_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_scraper_fetch_summary_json",
                            )
                        with st.expander("Raw scraper_fetch JSON", expanded=False):
                            st.json(_sf)
                _pf = preflight_history_from_timeline(data)
                _pf_rows = preflight_history_summary_rows(_pf)
                with st.expander("Preflight history (from timeline)", expanded=False):
                    if not _pf_rows:
                        st.caption(
                            "No preflight summary on this timeline (no "
                            "model.preflight.passed yet, or skipped via "
                            "HERMES_SKIP_PREFLIGHT)."
                        )
                    else:
                        st.caption(
                            "Latest model.preflight.passed summary (same top-level "
                            "preflight as GET …/timeline). Histogram bucket edges: "
                            "50 / 100 / 250 / 500 / 1000 / 2500 / 5000 / 10000 ms."
                        )
                        _pf_metrics = preflight_history_operator_metrics(_pf)
                        _pf_metrics_cap = preflight_history_operator_metrics_caption(
                            _pf_metrics,
                        )
                        if _pf_metrics_cap:
                            st.caption(_pf_metrics_cap)
                        _pf_metric_rows = preflight_history_operator_metrics_table_rows(
                            _pf_metrics,
                        )
                        _pf_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _pf_slug = preflight_history_export_filename_slug(run_id.strip())
                        if _pf_metric_rows:
                            st.dataframe(
                                _pf_metric_rows,
                                use_container_width=True,
                                hide_index=True,
                            )
                            _pf_metrics_json = preflight_history_operator_metrics_export_json(
                                _pf_metrics,
                            )
                            _pf_metrics_csv = preflight_history_operator_metrics_table_rows_csv(
                                _pf_metric_rows,
                            )
                            _pf_metrics_dl_json_col, _pf_metrics_dl_csv_col = st.columns(2)
                            with _pf_metrics_dl_json_col:
                                st.download_button(
                                    label=(
                                        "Download preflight history operator "
                                        "metrics JSON"
                                    ),
                                    data=_pf_metrics_json.encode("utf-8"),
                                    file_name=(
                                        "hermes_preflight_history_operator_metrics_"
                                        f"{_pf_slug}_{_pf_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_preflight_history_operator_metrics_json",
                                )
                            with _pf_metrics_dl_csv_col:
                                if _pf_metrics_csv:
                                    st.download_button(
                                        label=(
                                            "Download preflight history operator "
                                            "metrics CSV"
                                        ),
                                        data=_pf_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            "hermes_preflight_history_operator_metrics_"
                                            f"{_pf_slug}_{_pf_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_preflight_history_operator_metrics_csv",
                                    )
                        st.dataframe(_pf_rows, use_container_width=True)
                        _pf_hist_mode_cap = preflight_history_histogram_mode_caption(_pf)
                        if _pf_hist_mode_cap:
                            st.caption(_pf_hist_mode_cap)
                        _pf_samples_cap = preflight_history_samples_table_caption(_pf)
                        if _pf_samples_cap:
                            st.caption(_pf_samples_cap)
                        _pf_sample_rows = preflight_history_latency_samples_table_rows(
                            _pf,
                        )
                        if _pf_sample_rows:
                            st.dataframe(_pf_sample_rows, use_container_width=True)
                        _pf_p95_src_cap = preflight_history_p95_source_caption(_pf)
                        if _pf_p95_src_cap:
                            st.caption(_pf_p95_src_cap)
                        _pf_p95_ms_cap = preflight_history_p95_latency_caption(_pf)
                        if _pf_p95_ms_cap:
                            st.caption(_pf_p95_ms_cap)
                        _pf_event_cap = preflight_history_event_id_caption(_pf)
                        if _pf_event_cap:
                            st.caption(_pf_event_cap)
                        _pf_checks_cap = preflight_history_checks_passed_caption(_pf)
                        if _pf_checks_cap:
                            st.caption(_pf_checks_cap)
                        _pf_vm_cap = preflight_history_validated_model_caption(_pf)
                        if _pf_vm_cap:
                            st.caption(_pf_vm_cap)
                        _pf_provider_cap = preflight_history_provider_caption(_pf)
                        if _pf_provider_cap:
                            st.caption(_pf_provider_cap)
                        _pf_sc_cap = preflight_history_sample_count_caption(_pf)
                        if _pf_sc_cap:
                            st.caption(_pf_sc_cap)
                        _pf_ctx_cap = preflight_history_context_tokens_caption(_pf)
                        if _pf_ctx_cap:
                            st.caption(_pf_ctx_cap)
                        _hist = preflight_history_histogram_payload(_pf)
                        if _hist and _hist.get("count"):
                            _bars = [
                                {
                                    "bucket": (
                                        f"<={b['le_ms']}ms"
                                        if b["le_ms"] is not None
                                        else ">10000ms"
                                    ),
                                    "count": b["count"],
                                }
                                for b in _hist["buckets"]
                            ]
                            st.bar_chart(
                                _bars,
                                x="bucket",
                                y="count",
                                use_container_width=True,
                            )
                        _pf_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        _pf_slug = preflight_history_export_filename_slug(run_id.strip())
                        _pf_csv = preflight_history_summary_rows_csv(_pf_rows)
                        _pf_json = preflight_history_export_json(_pf)
                        _pf_dl_col, _pf_dl_json_col = st.columns(2)
                        with _pf_dl_col:
                            st.download_button(
                                label="Download preflight timeline CSV",
                                data=_pf_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_preflight_timeline_"
                                    f"{_pf_slug}_{_pf_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_preflight_timeline_csv",
                            )
                        with _pf_dl_json_col:
                            st.download_button(
                                label="Download preflight timeline JSON",
                                data=_pf_json.encode("utf-8"),
                                file_name=(
                                    "hermes_preflight_timeline_"
                                    f"{_pf_slug}_{_pf_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_preflight_timeline_json",
                            )
                        with st.expander("Raw preflight JSON", expanded=False):
                            st.json(_pf)
                _crit_rows = critic_matrix_rows_from_events(events)
                st.subheader("Critic matrix (extracted)")
                if not _crit_rows:
                    st.dataframe([{"note": "no critic.verdict.emitted events"}])
                else:
                    _crit_metrics = critic_matrix_operator_metrics(_crit_rows)
                    _crit_cap = critic_matrix_operator_metrics_caption(_crit_metrics)
                    if _crit_cap:
                        st.caption(_crit_cap)
                    _crit_metric_rows = critic_matrix_operator_metrics_table_rows(
                        _crit_metrics,
                    )
                    _crit_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    _crit_slug = critic_matrix_export_filename_slug(run_id.strip())
                    if _crit_metric_rows:
                        st.dataframe(
                            _crit_metric_rows,
                            use_container_width=True,
                            hide_index=True,
                        )
                        _crit_metrics_json = critic_matrix_operator_metrics_export_json(
                            _crit_metrics,
                        )
                        _crit_metrics_csv = (
                            critic_matrix_operator_metrics_table_rows_csv(
                                _crit_metric_rows,
                            )
                        )
                        (
                            _crit_metrics_dl_json_col,
                            _crit_metrics_dl_csv_col,
                        ) = st.columns(2)
                        with _crit_metrics_dl_json_col:
                            st.download_button(
                                label="Download critic matrix operator metrics JSON",
                                data=_crit_metrics_json.encode("utf-8"),
                                file_name=(
                                    "hermes_critic_matrix_operator_metrics_"
                                    f"{_crit_slug}_{_crit_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_critic_matrix_operator_metrics_json",
                            )
                        with _crit_metrics_dl_csv_col:
                            if _crit_metrics_csv:
                                st.download_button(
                                    label=(
                                        "Download critic matrix operator metrics CSV"
                                    ),
                                    data=_crit_metrics_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_critic_matrix_operator_metrics_"
                                        f"{_crit_slug}_{_crit_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_critic_matrix_operator_metrics_csv",
                                )
                    st.dataframe(_crit_rows, use_container_width=True, hide_index=True)
                    _crit_json = critic_matrix_export_json(_crit_rows)
                    _crit_csv = critic_matrix_table_rows_csv(_crit_rows)
                    _crit_dl_json_col, _crit_dl_csv_col = st.columns(2)
                    with _crit_dl_json_col:
                        st.download_button(
                            label="Download critic matrix JSON",
                            data=_crit_json.encode("utf-8"),
                            file_name=(
                                f"hermes_critic_matrix_{_crit_slug}_{_crit_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_critic_matrix_json",
                        )
                    with _crit_dl_csv_col:
                        if _crit_csv:
                            st.download_button(
                                label="Download critic matrix CSV",
                                data=_crit_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_critic_matrix_{_crit_slug}_{_crit_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_critic_matrix_csv",
                            )
    with c2:
        if st.button("Load findings") and run_id.strip():
            try:
                r = httpx.get(f"{API_BASE}/runs/{run_id.strip()}/findings", timeout=30.0)
                r.raise_for_status()
                st.subheader("Findings")
                _find_body = r.json()
                _find_list = findings_list_from_response(_find_body)
                if not _find_list:
                    st.caption(findings_empty_caption())
                else:
                    _find_metrics = findings_operator_metrics(_find_list)
                    _find_metrics_cap = findings_operator_metrics_caption(_find_metrics)
                    if _find_metrics_cap:
                        st.caption(_find_metrics_cap)
                    _find_metric_rows = findings_operator_metrics_table_rows(
                        _find_metrics,
                    )
                    _find_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    _find_slug = findings_export_filename_slug(run_id.strip())
                    if _find_metric_rows:
                        st.dataframe(
                            _find_metric_rows,
                            use_container_width=True,
                            hide_index=True,
                        )
                        _find_metrics_json = findings_operator_metrics_export_json(
                            _find_metrics,
                        )
                        _find_metrics_csv = findings_operator_metrics_table_rows_csv(
                            _find_metric_rows,
                        )
                        (
                            _find_metrics_dl_json_col,
                            _find_metrics_dl_csv_col,
                        ) = st.columns(2)
                        with _find_metrics_dl_json_col:
                            st.download_button(
                                label="Download findings operator metrics JSON",
                                data=_find_metrics_json.encode("utf-8"),
                                file_name=(
                                    "hermes_findings_operator_metrics_"
                                    f"{_find_slug}_{_find_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_findings_operator_metrics_json",
                            )
                        with _find_metrics_dl_csv_col:
                            if _find_metrics_csv:
                                st.download_button(
                                    label="Download findings operator metrics CSV",
                                    data=_find_metrics_csv.encode("utf-8"),
                                    file_name=(
                                        "hermes_findings_operator_metrics_"
                                        f"{_find_slug}_{_find_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_findings_operator_metrics_csv",
                                )
                    _find_table_rows = findings_table_rows(_find_list)
                    st.dataframe(
                        _find_table_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _find_json = findings_export_json(_find_body)
                    _find_csv = findings_table_rows_csv(_find_table_rows)
                    _find_dl_json_col, _find_dl_csv_col = st.columns(2)
                    with _find_dl_json_col:
                        st.download_button(
                            label="Download findings JSON",
                            data=_find_json.encode("utf-8"),
                            file_name=(
                                f"hermes_findings_{_find_slug}_{_find_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_findings_json",
                        )
                    with _find_dl_csv_col:
                        if _find_csv:
                            st.download_button(
                                label="Download findings CSV",
                                data=_find_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_findings_{_find_slug}_{_find_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_findings_csv",
                            )
                with st.expander("Raw findings JSON", expanded=False):
                    st.json(_find_body)
            except httpx.HTTPError as exc:
                st.error(f"API error: {exc}")

st.divider()
with st.container(border=True):
    st.subheader("Actions (POST /v1/runs/…/actions/…)")
    if run_id.strip():
        if st.button("Record retry (stage.started retry)"):
            try:
                r = httpx.post(f"{API_BASE}/runs/{run_id.strip()}/actions/retry", timeout=30.0)
                r.raise_for_status()
                st.success(r.json())
            except httpx.HTTPError as exc:
                st.error(f"API error: {exc}")
        esc_actor = st.text_input("Escalate actor_id", value="human:operator")
        esc_reason = st.text_input("Escalate reason_code", value="manual_review")
        esc_notes = st.text_area("Escalate notes (optional)", value="")
        if st.button("Record escalation (run.escalated)"):
            try:
                body = {"actor_id": esc_actor, "reason_code": esc_reason}
                if esc_notes.strip():
                    body["notes"] = esc_notes.strip()
                r = httpx.post(
                    f"{API_BASE}/runs/{run_id.strip()}/actions/escalate",
                    json=body,
                    timeout=30.0,
                )
                r.raise_for_status()
                st.success(r.json())
            except httpx.HTTPError as exc:
                st.error(f"API error: {exc}")

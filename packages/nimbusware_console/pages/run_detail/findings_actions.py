"""Run detail — findings, critics, lifecycle actions."""

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

import httpx
import streamlit as st

from nimbusware_console.agent_evaluator_display import (
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
from nimbusware_console.agent_evaluator_workflow_explainer import (
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
from nimbusware_console.bundle_catalog_editor import (
    bundle_editor_patch_payload,
    bundle_editor_validation_issues,
)
from nimbusware_console.bundle_memory_display import (
    bundle_memory_analytics_from_store,
    bundle_memory_caption,
)
from nimbusware_console.bundle_catalog import (
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
from nimbusware_console.console_theme import (
    streamlit_theme_defaults_caption,
    streamlit_white_label_deferred_caption,
)
from nimbusware_console.critic_matrix_display import (
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
from nimbusware_console.escalation_suppress_workflow_explainer import (
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
from nimbusware_console.findings_display import (
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
from nimbusware_console.integrator_gate_display import (
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
from nimbusware_console.integrator_threshold_explainer import (
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
from nimbusware_console.persona_assignment_display import (
    persona_assignment_caption,
    persona_assignment_from_timeline,
    persona_assignment_summary_rows,
    persona_assignment_timeline_export_json,
    persona_assignment_timeline_table_rows_csv,
)
from nimbusware_console.persona_catalog import (
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
from nimbusware_console.persona_editor import (
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
from nimbusware_console.preflight_cross_run_display import (
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
from nimbusware_console.preflight_history_display import (
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
from nimbusware_console.prune_status_display import (
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
from nimbusware_console.run_escalated_display import (
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
from nimbusware_console.run_list_pagination_display import (
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
from nimbusware_console.scraper_fetch_display import (
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
from nimbusware_console.security_scan_metadata_workflow_explainer import (
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
from nimbusware_console.micro_slice_packet_display import (
    latest_slice_context_packet_from_timeline,
)
from nimbusware_console.memory_display import (
    memory_indexed_timeline_summary,
    memory_policy_from_run_summary,
    memory_policy_table_rows,
    memory_retrieval_timeline_summary,
)
from nimbusware_console.phase3_critique_display import (
    phase3_critique_caption,
    phase3_critique_table_rows,
)
from nimbusware_console.security_scan_on_verify_display import (
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
from nimbusware_console.self_refinement_display import (
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
from nimbusware_console.self_refinement_workflow_explainer import (
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
from nimbusware_console.universal_critique_timeline_display import (
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
from nimbusware_console.universal_critique_workflow_explainer import (
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

from nimbusware_console.settings import API_BASE
from nimbusware_console.pages import _state as rl

def render_run_detail_findings_actions_section() -> None:
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
                                Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve(),
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
                            _re_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
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
                    with st.expander("Phase 3 critic stages (from timeline)", expanded=False):
                        st.caption(phase3_critique_caption(data))
                        _p3_rows = phase3_critique_table_rows(data)
                        if _p3_rows:
                            st.dataframe(_p3_rows, use_container_width=True)
                    _ms_tl = data.get("micro_slice") if isinstance(data, dict) else None
                    if isinstance(_ms_tl, dict) and _ms_tl:
                        with st.expander("Micro-slice summary (from timeline)", expanded=False):
                            st.json(_ms_tl)
                        _pkt = latest_slice_context_packet_from_timeline(data)
                        if _pkt:
                            with st.expander("Slice context packet (latest)", expanded=False):
                                st.json(_pkt)
                    _mem_ret = memory_retrieval_timeline_summary(data.get("events") or [])
                    _mem_idx = memory_indexed_timeline_summary(data.get("events") or [])
                    if _mem_ret or _mem_idx:
                        with st.expander("Memory retrieval / index (from timeline)", expanded=False):
                            if _mem_ret:
                                st.caption("Last retrieval event summary")
                                st.json(_mem_ret)
                            if _mem_idx:
                                st.caption("Last memory.indexed summary")
                                st.json(_mem_idx)
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

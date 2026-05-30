"""Run detail — summary, timeline, integrator gate panels."""

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

def render_run_detail_summary_timeline_section() -> None:
    st.divider()
    with st.container(border=True):
        st.subheader("Run detail")
        run_id = st.text_input("Run ID (detail)", placeholder="uuid", key=rl._SS_DETAIL)

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
                    _mem_policy = memory_policy_from_run_summary(data)
                    if _mem_policy:
                        with st.expander("Memory policy (from run.created)", expanded=False):
                            _mem_rows = memory_policy_table_rows(_mem_policy)
                            if _mem_rows:
                                st.dataframe(_mem_rows, use_container_width=True, hide_index=True)
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

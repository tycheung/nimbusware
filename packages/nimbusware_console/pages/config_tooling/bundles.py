"""Config tooling — bundle catalog and FAISS sections."""

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

def _resolve_prune_status_path() -> Path | None:
    """Return ``HERMES_PRUNE_STATUS_PATH`` expanded to a ``Path``, or ``None`` when unset.

    Resolved per-render so operators can switch the env var without restarting the
    Streamlit server. Matches the script-side resolution in
    ``scripts/prune_scraper_artifacts.py``.
    """
    raw = os.environ.get("HERMES_PRUNE_STATUS_PATH", "").strip()
    return Path(raw).expanduser() if raw else None

from nimbusware_console.settings import API_BASE
from nimbusware_console.pages import _state as rl

def render_config_tooling_bundles_section() -> None:
        with st.expander("Bundle catalog search (local repo)", expanded=False):
            st.caption(
                "Read-only: same ``search_bundles`` helper as **GET /v1/bundles/search** over "
                "``configs/bundles/catalog.yaml``. Uses **NIMBUSWARE_REPO_ROOT** (resolved); "
                "matches the API frozen repo root when both use the same env.",
            )
            _root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
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
                    st.session_state[rl._LAST_BUNDLE_SEARCH_JSON] = run_bundle_catalog_search(
                        _root,
                        _bq,
                        k=_bk,
                    )
            _bundle_blob = st.session_state.get(rl._LAST_BUNDLE_SEARCH_JSON)
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

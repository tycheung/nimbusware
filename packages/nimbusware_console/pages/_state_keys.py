from __future__ import annotations

_RUN_LIST_QP_KEYS = frozenset(
    {
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
    }
)

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
_LAST_LIST_PAGE = "hermes_last_list_page"
_LAST_BUNDLE_SEARCH_JSON = "hermes_last_bundle_search_json"
_LAST_PERSONA_CATALOG_JSON = "hermes_last_persona_catalog_json"
_LAST_INTEGRATOR_PREVIEW = "hermes_last_integrator_preview_json"
_LAST_INTEGRATOR_MERGE_DRY = "hermes_last_integrator_merge_dry_run"
_LAST_AGENT_EVALUATOR_MERGE_DRY = "hermes_last_agent_evaluator_merge_dry_run"
_LAST_FULL_WORKFLOW_MERGE_DRY = "hermes_last_full_workflow_merge_dry_run"

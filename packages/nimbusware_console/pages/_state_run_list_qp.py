"""Run list query-param sync and defaults."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import streamlit as st

from nimbusware_client.http import HTTPError, get_response
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.pages._state_keys import (

    _DF_LIST_KEY,
    _DF_LIST_SEL_SIG,
    _LAST_AGENT_EVALUATOR_MERGE_DRY,
    _LAST_BUNDLE_SEARCH_JSON,
    _LAST_FULL_WORKFLOW_MERGE_DRY,
    _LAST_INTEGRATOR_MERGE_DRY,
    _LAST_INTEGRATOR_PREVIEW,
    _LAST_LIST_ERR,
    _LAST_LIST_JSON,
    _LAST_LIST_PAGE,
    _LAST_PERSONA_CATALOG_JSON,
    _LIST_OPTIONAL_ORDER,
    _PREFLIGHT_TREND_ERR,
    _PREFLIGHT_TREND_HISTORY_BODY,
    _PREFLIGHT_TREND_ROWS,
    _RUN_LIST_QP_KEYS,
    _SS_CA,
    _SS_CB,
    _SS_CUR,
    _SS_DETAIL,
    _SS_ESC,
    _SS_LIM,
    _SS_LIST_COLS,
    _SS_OFF,
    _SS_ORDER,
    _SS_PFX,
    _SS_ST,
    _SS_SUM,
    _SS_WF,
)
from nimbusware_console.run_list_pagination_display import (


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
)
from nimbusware_console.settings import API_BASE

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



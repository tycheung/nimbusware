"""Run list query-param sync, fetch, and display."""

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


def _run_list_payload_to_csv(data: dict[str, Any]) -> str:
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
    m1.metric("total (list)", tot if isinstance(tot, int) else "â€”")
    if "has_more" in data:
        m2.metric("has_more", "yes" if data.get("has_more") else "no")
    else:
        m2.metric("has_more", "â€”")
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
                    chip_parts.append(f"{rid[:8]}â€¦ â†’ {st_label}")
            if chip_parts:
                st.caption("Status (from summaries): " + " Â· ".join(chip_parts))
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
        r = get_response("/runs", params=params, timeout=15.0)
        _run_list_qp_push(params)
        data = r.json()
        _hdrs = r.headers
        _link_h = _hdrs.get("link") or _hdrs.get("Link")
        _link_arg = _link_h if isinstance(_link_h, str) else None
        _store_list_snapshot(data, params, link_header=_link_arg)
        st.session_state[_LAST_LIST_JSON] = data
        st.session_state.pop(_LAST_LIST_ERR, None)
        _render_run_list(data, include_summary=bool(st.session_state[_SS_SUM]))
    except HTTPError as exc:
        st.session_state.pop(_LAST_LIST_PAGE, None)
        st.session_state.pop(_LAST_LIST_JSON, None)
        st.session_state[_LAST_LIST_ERR] = str(exc)
        st.error(f"API error: {exc}")
        return False
    else:
        return True

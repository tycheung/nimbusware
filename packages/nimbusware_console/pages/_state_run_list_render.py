from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from nimbusware_client.http import HTTPError, get_response
from nimbusware_console.pages._state_keys import (
    _DF_LIST_KEY,
    _DF_LIST_SEL_SIG,
    _LAST_LIST_ERR,
    _LAST_LIST_JSON,
    _LAST_LIST_PAGE,
    _LIST_OPTIONAL_ORDER,
    _SS_DETAIL,
    _SS_LIST_COLS,
    _SS_SUM,
)
from nimbusware_console.pages._state_run_list_qp import (
    _build_run_list_params,
    _run_list_qp_push,
    _store_list_snapshot,
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

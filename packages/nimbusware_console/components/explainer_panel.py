from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Literal

import streamlit as st


def explainer_utc_timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def hermes_download_filename(
    slug: str,
    ts: str,
    *,
    kind: Literal["metrics", "explainer"],
    ext: str,
) -> str:
    if kind == "explainer":
        return f"hermes_{slug}_explainer_{ts}.{ext}"
    return f"hermes_{slug}_{ts}.{ext}"


def render_operator_metrics_explainer(
    *,
    caption: str | None,
    table_rows: Sequence[Mapping[str, str]] | None,
    json_text: str,
    csv_text: str,
    filename_slug: str,
    json_label: str,
    csv_label: str,
    json_download_key: str,
    csv_download_key: str,
) -> None:
    if caption:
        st.caption(caption)
    if table_rows:
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    ts = explainer_utc_timestamp_slug()
    json_col, csv_col = st.columns(2)
    with json_col:
        st.download_button(
            label=json_label,
            data=json_text.encode("utf-8"),
            file_name=hermes_download_filename(
                filename_slug,
                ts,
                kind="metrics",
                ext="json",
            ),
            mime="application/json",
            key=json_download_key,
        )
    with csv_col:
        if csv_text:
            st.download_button(
                label=csv_label,
                data=csv_text.encode("utf-8"),
                file_name=hermes_download_filename(
                    filename_slug,
                    ts,
                    kind="metrics",
                    ext="csv",
                ),
                mime="text/csv; charset=utf-8",
                key=csv_download_key,
            )


def render_explainer_export_downloads(
    *,
    json_text: str,
    csv_text: str,
    filename_slug: str,
    json_label: str,
    csv_label: str,
    json_download_key: str,
    csv_download_key: str,
) -> None:
    ts = explainer_utc_timestamp_slug()
    json_col, csv_col = st.columns(2)
    with json_col:
        st.download_button(
            label=json_label,
            data=json_text.encode("utf-8"),
            file_name=hermes_download_filename(
                filename_slug,
                ts,
                kind="explainer",
                ext="json",
            ),
            mime="application/json",
            key=json_download_key,
        )
    with csv_col:
        if csv_text:
            st.download_button(
                label=csv_label,
                data=csv_text.encode("utf-8"),
                file_name=hermes_download_filename(
                    filename_slug,
                    ts,
                    kind="explainer",
                    ext="csv",
                ),
                mime="text/csv; charset=utf-8",
                key=csv_download_key,
            )

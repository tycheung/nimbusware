from __future__ import annotations

import streamlit as st


def render_api_error(exc: BaseException, *, prefix: str = "API error") -> None:
    st.error(f"{prefix}: {exc}")

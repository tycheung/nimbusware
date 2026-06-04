from __future__ import annotations


def render_api_error(exc: BaseException) -> None:
    raise RuntimeError("Streamlit UI removed; handle errors in the web console.")

from __future__ import annotations


def render_api_error(exc: BaseException) -> None:
    raise RuntimeError("Use the Admin web UI for API errors.")

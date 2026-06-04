"""Admin Console UI is served at ``/v1/admin/app/`` (Preact SPA)."""

from __future__ import annotations

WEB_ENTRY = "/v1/admin/app/"


def render_main() -> None:
    raise RuntimeError(
        f"Streamlit Admin Console removed. Open {WEB_ENTRY} in a browser "
        "(set NIMBUSWARE_UI_BACKEND=web for desktop launcher).",
    )

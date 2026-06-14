from __future__ import annotations

WEB_ENTRY = "/v1/admin/app/"


def render_main() -> None:
    raise RuntimeError(f"Admin UI is web-only. Open {WEB_ENTRY} (NIMBUSWARE_UI_BACKEND=web).")

from __future__ import annotations

import webbrowser

from nimbusware_env.env_flags import env_str


def open_admin_web() -> None:
    base = env_str("NIMBUSWARE_API_BASE", default="http://127.0.0.1:8000/v1").rstrip("/")
    url = base.replace("/v1", "") + "/v1/admin/app/"
    webbrowser.open(url)

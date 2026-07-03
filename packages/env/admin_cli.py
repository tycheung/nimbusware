from __future__ import annotations

import webbrowser

from env.env_flags import api_base_url


def open_admin_web() -> None:
    base = api_base_url()
    url = base.replace("/v1", "") + "/v1/admin/app/"
    webbrowser.open(url)

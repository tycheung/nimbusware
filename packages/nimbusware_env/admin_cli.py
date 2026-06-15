from __future__ import annotations

import webbrowser

from nimbusware_env.env_flags import nimbusware_api_base_url


def open_admin_web() -> None:
    base = nimbusware_api_base_url()
    url = base.replace("/v1", "") + "/v1/admin/app/"
    webbrowser.open(url)

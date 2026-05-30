from __future__ import annotations

import os

# Local-dev default only — search the repo for this string before any production deploy.
DEFAULT_NIMBUSWARE_ADMIN_TOKEN = "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"


def nimbusware_admin_token() -> str:
    raw = os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "").strip()
    return raw or DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def apply_default_admin_token_env() -> None:
    if not os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "").strip():
        os.environ["NIMBUSWARE_ADMIN_TOKEN"] = DEFAULT_NIMBUSWARE_ADMIN_TOKEN

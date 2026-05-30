from __future__ import annotations

import os
import socket

# Local-dev default only — search the repo for this string before any production deploy.
DEFAULT_NIMBUSWARE_ADMIN_TOKEN = "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"


def nimbusware_admin_token() -> str:
    raw = os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "").strip()
    return raw or DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def apply_default_admin_token_env() -> None:
    if not os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "").strip():
        os.environ["NIMBUSWARE_ADMIN_TOKEN"] = DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def using_default_admin_token() -> bool:
    return nimbusware_admin_token() == DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def is_loopback_host(host: str) -> bool:
    trimmed = host.strip().lower()
    if trimmed in {"127.0.0.1", "localhost", "::1"}:
        return True
    if trimmed.startswith("127."):
        return True
    try:
        packed = socket.inet_pton(socket.AF_INET6, trimmed)
    except OSError:
        return False
    return packed == socket.inet_pton(socket.AF_INET6, "::1")


def require_non_default_admin_token_for_host(host: str) -> None:
    if using_default_admin_token() and not is_loopback_host(host):
        msg = (
            "Refusing to start with the dev default NIMBUSWARE_ADMIN_TOKEN on a "
            f"non-loopback host ({host!r}). Set a unique token in the environment first."
        )
        raise RuntimeError(msg)

from __future__ import annotations

from env.env_flags import api_base_url

SESSION_ADMIN_UNLOCKED = "maker_admin_unlocked"


def is_admin_unlocked(session_state: object | None = None) -> bool:
    if session_state is None:
        return False
    get = getattr(session_state, "get", None)
    if not callable(get):
        return False
    return bool(get(SESSION_ADMIN_UNLOCKED))


def clear_admin_unlock(session_state: object | None = None) -> None:
    if session_state is not None:
        setattr(session_state, SESSION_ADMIN_UNLOCKED, False)


def admin_console_url() -> str:
    base = api_base_url()
    return base.replace("/v1", "") + "/v1/admin/app/"


def render_admin_sidebar() -> None:
    raise RuntimeError("Maker admin sidebar moved to web UI sessionStorage.")

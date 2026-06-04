from __future__ import annotations


def render_enterprise_sidebar() -> bool:
    raise RuntimeError("Enterprise fleet sidebar is deferred; use API fleet endpoints.")


def render_enterprise_fleet_dashboard() -> None:
    raise RuntimeError("Enterprise fleet dashboard is deferred.")


def enterprise_preflight_headers_for_cross_run() -> dict[str, str]:
    return {}

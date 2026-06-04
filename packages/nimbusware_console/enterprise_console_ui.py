"""Legacy Enterprise fleet UI entry points — use Admin SPA at ``/v1/admin/app/fleet``."""


def render_enterprise_sidebar() -> bool:
    return False


def render_enterprise_fleet_dashboard() -> None:
    return None


def enterprise_preflight_headers_for_cross_run() -> dict[str, str]:
    return {}

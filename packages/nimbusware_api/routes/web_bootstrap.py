from __future__ import annotations

from fastapi import APIRouter, Request

from nimbusware_env.edition import edition, is_enterprise
from nimbusware_env.env_flags import env_str
from nimbusware_env.oidc_config import load_oidc_config
from nimbusware_maker.push_subscriptions import push_web_enabled, vapid_public_key
from nimbusware_maker.quick_mode import quick_mode_enabled

router = APIRouter(tags=["web"])


def _api_base(request: Request) -> str:
    base = env_str("NIMBUSWARE_API_BASE")
    if base:
        return base.rstrip("/")
    return str(request.base_url).rstrip("/") + "/v1"


def maker_bootstrap_payload(request: Request) -> dict:
    return {
        "api_base": _api_base(request),
        "edition": edition(),
        "quick_mode": quick_mode_enabled(),
        "ui_backend": env_str("NIMBUSWARE_UI_BACKEND") or "web",
        "features": {
            "maker_web": True,
            "admin_web": True,
            "sse_theater": True,
            "sse_progress": True,
            "mobile_pwa_ready": True,
            "push_web": push_web_enabled(),
        },
        "push": {
            "enabled": push_web_enabled(),
            "vapid_public_key": vapid_public_key() or None,
        },
    }


def admin_bootstrap_payload(request: Request) -> dict:
    body = maker_bootstrap_payload(request)
    body["admin_token_required"] = True
    features = body.setdefault("features", {})
    if isinstance(features, dict):
        features["enterprise_fleet_ui"] = is_enterprise()
        features["oidc_login_ready"] = is_enterprise() and load_oidc_config().login_ready()
    return body


@router.get("/maker/app/bootstrap.json")
def get_maker_app_bootstrap(request: Request) -> dict:
    return maker_bootstrap_payload(request)


@router.get("/admin/app/bootstrap.json")
def get_admin_app_bootstrap(request: Request) -> dict:
    return admin_bootstrap_payload(request)

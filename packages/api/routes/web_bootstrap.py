from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from env.admin_token import is_loopback_host
from env.edition import edition, is_enterprise
from env.env_flags import env_str
from env.oidc_config import load_oidc_config
from maker.push_subscriptions import push_web_enabled, vapid_public_key
from maker.quick_mode import quick_mode_enabled

router = APIRouter(tags=["web"])


def _api_base(request: Request) -> str:
    base = env_str("NIMBUSWARE_API_BASE")
    if base:
        return base.rstrip("/")
    return str(request.base_url).rstrip("/") + "/v1"


def maker_bootstrap_payload(request: Request) -> dict[str, Any]:
    api_host = env_str("NIMBUSWARE_API_HOST").strip() or "127.0.0.1"
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    return {
        "api_base": _api_base(request),
        "edition": edition(),
        "setup_bundle": setup_bundle,
        "quick_mode": quick_mode_enabled(),
        "ui_backend": env_str("NIMBUSWARE_UI_BACKEND") or "web",
        "user_token_required": not is_enterprise() and not is_loopback_host(api_host),
        "default_profiles": {
            "autopilot_profile_id": env_str("NIMBUSWARE_DEFAULT_AUTOPILOT_PROFILE").strip() or None,
            "enforcement_profile_id": env_str("NIMBUSWARE_DEFAULT_ENFORCEMENT_PROFILE").strip()
            or None,
            "workflow_profile": env_str("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE").strip() or None,
        },
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


def admin_bootstrap_payload(request: Request) -> dict[str, Any]:
    body = maker_bootstrap_payload(request)
    body["admin_token_required"] = True
    features = body.setdefault("features", {})
    if isinstance(features, dict):
        features["enterprise_fleet_ui"] = is_enterprise()
        features["oidc_login_ready"] = is_enterprise() and load_oidc_config().login_ready()
    return body


@router.get("/maker/app/bootstrap.json")
def get_maker_app_bootstrap(request: Request) -> dict[str, Any]:
    return maker_bootstrap_payload(request)


@router.get("/admin/app/bootstrap.json")
def get_admin_app_bootstrap(request: Request) -> dict[str, Any]:
    return admin_bootstrap_payload(request)

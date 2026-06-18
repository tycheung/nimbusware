from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.routes import (
    actions,
    admin_oauth,
    admin_ui_bff,
    analytics,
    audit,
    auth,
    bundles,
    campaigns,
    chat,
    chat_host_transfer,
    chat_library,
    chat_participants,
    chat_stream,
    compute,
    config_ops,
    critic_packs,
    custom_agents,
    integrations,
    memory_chunks,
    model_bindings,
    ollama,
    operator_settings,
    personas,
    platform,
    policy,
    preflight,
    project_context_artifacts,
    projects,
    provider_connections,
    runs,
    scraper_artifacts,
)
from nimbusware_api.routes.enterprise import build_enterprise_router
from nimbusware_api.routes.maker_push import router as maker_push_router
from nimbusware_api.routes.web_bootstrap import router as web_bootstrap_router


def build_v1_router() -> APIRouter:
    """Compose all v1 route modules without changing individual path prefixes."""
    router = APIRouter()
    router.include_router(runs.router)
    router.include_router(campaigns.router)
    router.include_router(actions.router)
    router.include_router(policy.router)
    router.include_router(config_ops.router)
    router.include_router(audit.router)
    router.include_router(bundles.router)
    router.include_router(critic_packs.router)
    router.include_router(personas.router)
    router.include_router(custom_agents.router)
    router.include_router(projects.router)
    router.include_router(auth.router)
    router.include_router(chat.router)
    router.include_router(chat_participants.router)
    router.include_router(chat_host_transfer.router)
    router.include_router(chat_library.router)
    router.include_router(chat_stream.router)
    router.include_router(project_context_artifacts.router)
    router.include_router(preflight.router)
    router.include_router(scraper_artifacts.router)
    router.include_router(platform.router)
    router.include_router(provider_connections.router)
    router.include_router(model_bindings.router)
    router.include_router(compute.router)
    router.include_router(memory_chunks.router)
    router.include_router(analytics.router)
    router.include_router(operator_settings.router)
    router.include_router(ollama.router)
    router.include_router(build_enterprise_router())
    router.include_router(web_bootstrap_router)
    router.include_router(admin_ui_bff.router)
    router.include_router(admin_oauth.router)
    router.include_router(integrations.router)
    router.include_router(maker_push_router)
    return router

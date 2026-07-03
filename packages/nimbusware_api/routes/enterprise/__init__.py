from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.routes.enterprise.audit_export import router as enterprise_audit_export_router
from nimbusware_api.routes.enterprise.audit_policy import router as audit_policy_router
from nimbusware_api.routes.enterprise.collab_policy import router as collab_policy_router
from nimbusware_api.routes.enterprise.compliance import router as compliance_router
from nimbusware_api.routes.enterprise.config_notify import router as config_notify_router
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.enterprise.core import router as core_router
from nimbusware_api.routes.enterprise.fleet_analytics import router as fleet_analytics_router
from nimbusware_api.routes.enterprise.fleet_autopilot import router as fleet_autopilot_router
from nimbusware_api.routes.enterprise.fleet_commit import router as fleet_commit_router
from nimbusware_api.routes.enterprise.fleet_critic_reliability import (
    router as fleet_critic_reliability_router,
)
from nimbusware_api.routes.enterprise.fleet_deploy import router as fleet_deploy_router
from nimbusware_api.routes.enterprise.fleet_deploy_approval import (
    router as fleet_deploy_approval_router,
)
from nimbusware_api.routes.enterprise.fleet_discovery import router as fleet_discovery_router
from nimbusware_api.routes.enterprise.fleet_enforcement import router as fleet_enforcement_router
from nimbusware_api.routes.enterprise.fleet_learnings import router as fleet_learnings_router
from nimbusware_api.routes.enterprise.fleet_memory import router as fleet_memory_router
from nimbusware_api.routes.enterprise.fleet_mesh import router as fleet_mesh_router
from nimbusware_api.routes.enterprise.fleet_ops import ollama_sli_router as fleet_ollama_sli_router
from nimbusware_api.routes.enterprise.fleet_ops import worker_router as fleet_worker_router
from nimbusware_api.routes.enterprise.fleet_slice import router as fleet_slice_router
from nimbusware_api.routes.enterprise.fleet_stack import router as fleet_stack_router
from nimbusware_api.routes.enterprise.iam import router as iam_router
from nimbusware_api.routes.enterprise.model_policy import router as model_policy_router
from nimbusware_api.routes.enterprise.object_store import router as object_store_router
from nimbusware_api.routes.enterprise.research_ops import router as enterprise_research_ops_router
from nimbusware_api.routes.enterprise.tenant_collab_policy import (
    router as tenant_collab_policy_router,
)
from nimbusware_api.routes.enterprise.tenant_model_policy import (
    router as tenant_model_policy_router,
)
from nimbusware_api.routes.enterprise.users import router as enterprise_users_router

__all__ = [
    "EnterpriseDep",
    "build_enterprise_router",
    "core_router",
    "iam_router",
    "fleet_memory_router",
    "config_notify_router",
    "object_store_router",
    "fleet_worker_router",
    "fleet_ollama_sli_router",
    "fleet_analytics_router",
    "fleet_critic_reliability_router",
]


def build_enterprise_router() -> APIRouter:
    """Single router mounting all enterprise sub-routers (paths unchanged)."""
    router = APIRouter()
    router.include_router(core_router)
    router.include_router(iam_router)
    router.include_router(fleet_memory_router)
    router.include_router(fleet_learnings_router)
    router.include_router(config_notify_router)
    router.include_router(object_store_router)
    router.include_router(fleet_worker_router)
    router.include_router(fleet_mesh_router)
    router.include_router(fleet_ollama_sli_router)
    router.include_router(fleet_analytics_router)
    router.include_router(fleet_autopilot_router)
    router.include_router(fleet_enforcement_router)
    router.include_router(fleet_slice_router)
    router.include_router(fleet_commit_router)
    router.include_router(fleet_deploy_router)
    router.include_router(fleet_deploy_approval_router)
    router.include_router(fleet_discovery_router)
    router.include_router(fleet_stack_router)
    router.include_router(fleet_critic_reliability_router)
    router.include_router(enterprise_audit_export_router)
    router.include_router(audit_policy_router)
    router.include_router(compliance_router)
    router.include_router(model_policy_router)
    router.include_router(collab_policy_router)
    router.include_router(tenant_collab_policy_router)
    router.include_router(tenant_model_policy_router)
    router.include_router(enterprise_users_router)
    router.include_router(enterprise_research_ops_router)
    return router

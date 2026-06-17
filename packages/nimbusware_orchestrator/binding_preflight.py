from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env.env_flags import env_str
from nimbusware_orchestrator.llm.providers import provider_for_preset
from nimbusware_orchestrator.model_binding_resolver import ModelBindingResolver
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict

_STAGE_ROLE_MAP: dict[str, str] = {
    "plan": "planner",
    "slice.plan": "planner",
    "slice.implement": "backend_writer",
    "slice.test": "test_writer",
    "slice.critique": "security_critic",
    "implementation.critique": "security_critic",
    "test_writer.critique": "test_writer",
    "planner.critique": "planner",
    "frontend_writer.critique": "frontend_writer",
    "module_integrator.critique": "backend_writer",
    "self_refinement.critique": "planner",
    "agent_evaluator.critique": "planner",
}


def agent_role_for_stage(stage_name: str | None) -> str | None:
    if not stage_name:
        return None
    key = stage_name.strip()
    if not key:
        return None
    return _STAGE_ROLE_MAP.get(key)


_WORK_TYPE_ROLES: dict[str, list[str]] = {
    "patch": ["planner", "backend_writer"],
    "slice": ["planner", "backend_writer", "test_writer", "security_critic"],
    "factory": ["planner", "backend_writer", "test_writer", "frontend_writer", "security_critic"],
}


def _roles_from_defaults(repo_root: Path) -> list[str]:
    path = repo_root / "configs" / "model_bindings" / "defaults.yaml"
    if not path.is_file():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    roles = mapping_or_empty(doc.get("roles") if isinstance(doc, dict) else None)
    return sorted(str(k) for k in roles.keys())


def active_roles_for_context(
    repo_root: Path,
    *,
    workflow_profile: str | None = None,
    work_type: str | None = None,
    materializer: Any | None = None,
) -> list[str]:
    """Workflow-scoped active roles."""
    found: set[str] = set()
    wt = (work_type or "").strip().lower()
    if wt and wt in _WORK_TYPE_ROLES:
        found.update(_WORK_TYPE_ROLES[wt])

    profile = (workflow_profile or "").strip()
    if profile:
        try:
            wf = workflow_profile_dict(repo_root, profile, materializer=materializer)
        except (FileNotFoundError, ValueError):
            wf = {}
        actor = wf.get("actor_role_key")
        if isinstance(actor, str) and actor.strip():
            found.add(actor.strip())
        graph = wf.get("stage_graph")
        if isinstance(graph, list):
            for stage in graph:
                if not isinstance(stage, dict):
                    continue
                name = str(stage.get("stage_name") or "").strip()
                role = _STAGE_ROLE_MAP.get(name)
                if role:
                    found.add(role)
        if wf.get("universal_critique"):
            found.update(
                {
                    "security_critic",
                    "code_quality_critic",
                    "performance_critic",
                },
            )

    if not found:
        found.update(_roles_from_defaults(repo_root) or ["planner", "backend_writer"])
    return sorted(found)


def _resolve_api_key(binding) -> str | None:
    ref = binding.api_key_ref
    if isinstance(ref, str) and ref.strip():
        val = env_str(ref.strip())
        return val.strip() or None
    return None


def _inference_mode_label(mode: str) -> str:
    if mode == "cloud-only":
        return "Cloud-only inference"
    if mode == "hybrid":
        return "Hybrid inference (local + cloud)"
    if mode == "local-only":
        return "Local-only inference (Ollama)"
    return "Degraded inference — some roles lack reachable providers"


def build_binding_preflight_report(
    repo_root: Path,
    *,
    workflow_profile: str | None = None,
    work_type: str | None = None,
    materializer: Any | None = None,
    probe: bool = True,
) -> dict[str, Any]:
    roles = active_roles_for_context(
        repo_root,
        workflow_profile=workflow_profile,
        work_type=work_type,
        materializer=materializer,
    )
    resolver = ModelBindingResolver(repo_root)
    role_rows: list[dict[str, Any]] = []
    providers: dict[str, dict[str, Any]] = {}
    local_needed = False
    cloud_used = False
    roles_without_provider: list[str] = []

    for role in roles:
        binding = resolver.resolve(role)
        reachable = True
        probe_msg = "not probed"
        if probe:
            api_key = _resolve_api_key(binding)
            if binding.provider_kind == "local":
                local_needed = True
                provider = provider_for_preset(
                    repo_root,
                    provider_id=binding.provider_id,
                    base_url=binding.base_url,
                )
                probe_out = provider.probe()
            else:
                cloud_used = True
                provider = provider_for_preset(
                    repo_root,
                    provider_id=binding.provider_id,
                    base_url=binding.base_url,
                    api_key=api_key,
                )
                probe_out = provider.probe()
            reachable = bool(probe_out.get("ok"))
            probe_msg = str(probe_out.get("message") or "")
        if not reachable:
            roles_without_provider.append(role)
        pid = binding.provider_id
        providers[pid] = {
            "provider_id": pid,
            "provider_kind": binding.provider_kind,
            "reachable": reachable,
            "message": probe_msg,
        }
        role_rows.append(
            {
                "agent_role": role,
                "provider_id": binding.provider_id,
                "provider_kind": binding.provider_kind,
                "model_id": binding.model_id,
                "binding_source": binding.binding_source,
                "reachable": reachable,
                "message": probe_msg,
            },
        )

    if local_needed and cloud_used:
        inference_mode = "hybrid"
    elif cloud_used and not local_needed:
        inference_mode = "cloud-only"
    elif local_needed:
        inference_mode = "local-only"
    else:
        inference_mode = "degraded"

    if roles_without_provider:
        inference_mode = "degraded"

    return {
        "roles_covered": len(roles) - len(roles_without_provider),
        "roles_total": len(roles),
        "roles_without_provider": roles_without_provider,
        "providers_reachable": providers,
        "roles": role_rows,
        "ollama_required": local_needed,
        "inference_mode": inference_mode,
        "inference_mode_label": _inference_mode_label(inference_mode),
        "workflow_profile": workflow_profile,
        "work_type": work_type,
    }


def cloud_only_roles_satisfied(report: dict[str, Any]) -> bool:
    if report.get("ollama_required"):
        return False
    return not report.get("roles_without_provider")

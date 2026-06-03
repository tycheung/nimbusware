from __future__ import annotations

from typing import Protocol

from hermes_orchestrator._pipeline._helpers import (  # type: ignore[attr-defined]
    UUID,
    Any,
    EventType,
    Path,
    RunCreatedEvent,
    RunCreatedPayload,
    agent_evaluator_production_default_on,
    assert_agent_evaluator_persona_in_shelves,
    assert_bundle_catalog_maps_resolve,
    assert_critique_coverage_complete,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_stage_graph_valid,
    assert_taxonomy_keys_resolve,
    critique_coverage_snapshot,
    datetime,
    effective_universal_critique,
    parse_agent_evaluator_workflow_block,
    parse_self_refinement_workflow_block,
    parse_universal_critique_workflow_block,
    policy_snapshot_from_files,
    self_refinement_production_ungated_effective,
    self_refinement_ungated_loop_effective,
    stage_graph_from_workflow_profile,
    stage_graph_metadata_snapshot,
    taxonomy_keys_for_run_lifecycle,
    timezone,
    universal_critique_production_default_on,
    uuid4,
    workflow_profile_dict,
    workflow_profile_path,
)
from hermes_orchestrator.registry import RoleRegistry
from hermes_store.protocol import EventStore


class _CreateRunHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _repo_root: Path
    _base_path: Path
    _config_materializer: Any | None
    _memory_chunk_store: Any | None
    _critique_router: Any

    def _run_created_metadata(self, run_id: UUID) -> dict[str, Any]: ...


class CreateRunMixin:
    def create_run(
        self: _CreateRunHost,
        workflow_profile: str,
        *,
        idempotency_key: UUID | None = None,
        correlation_id: UUID | None = None,
        run_policy_overrides: dict[str, Any] | None = None,
        business_area_persona_id: str | None = None,
        development_role_persona_id: str | None = None,
        custom_agent_id: str | None = None,
        project_id: UUID | None = None,
        project_name: str | None = None,
        project_workspace_path: str | None = None,
        project_template: str | None = None,
        requirements: dict[str, Any] | None = None,
    ) -> UUID:
        mat = self._config_materializer
        assert_known_workflow(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        assert_stage_graph_valid(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        assert_bundle_catalog_maps_resolve(self._repo_root)
        assert_persona_shelves_valid(self._repo_root, config_materializer=mat)
        assert_agent_evaluator_persona_in_shelves(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        if business_area_persona_id or development_role_persona_id:
            from hermes_orchestrator.ingress import assert_persona_assignment_valid
            from nimbusware_config.persist import load_persona_shelf

            shelf = load_persona_shelf(self._repo_root, materializer=mat)
            assert_persona_assignment_valid(
                shelf,
                business_area_persona_id=business_area_persona_id,
                development_role_persona_id=development_role_persona_id,
            )
        assert_taxonomy_keys_resolve(
            self._registry,
            taxonomy_keys_for_run_lifecycle(self._registry, self._critique_router),
        )
        critique_coverage = critique_coverage_snapshot(self._registry, self._critique_router)
        assert_critique_coverage_complete(critique_coverage)
        wf_dict = workflow_profile_dict(
            self._repo_root,
            workflow_profile,
            materializer=mat,
        )
        stage_graph = stage_graph_from_workflow_profile(wf_dict)
        stage_graph_snapshot = stage_graph_metadata_snapshot(stage_graph)
        uc_block = parse_universal_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        uc_eff = effective_universal_critique(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        ae_block = parse_agent_evaluator_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        sr_block = parse_self_refinement_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        from hermes_orchestrator.workflow_memory import (
            memory_effective_metadata,
            parse_memory_workflow_block,
            resolve_memory_index_version,
        )
        from hermes_orchestrator.workflow_micro_slice import parse_micro_slice_workflow_block

        ms_block = parse_micro_slice_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        mem_block = parse_memory_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        from hermes_orchestrator.workflow_research import (
            parse_research_workflow_block,
            parse_stitch_workflow_block,
            research_effective_metadata,
            stitch_effective_metadata,
        )
        from hermes_orchestrator.workflow_theater import (
            parse_theater_workflow_block,
            theater_effective_metadata,
        )

        research_block = parse_research_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        stitch_block = parse_stitch_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        theater_block = parse_theater_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        memory_meta = memory_effective_metadata(
            mem_block,
            run_policy_overrides=run_policy_overrides,
        )
        memory_index_version = resolve_memory_index_version(
            self._memory_chunk_store,
            repo_root=self._repo_root,
        )
        if memory_index_version:
            memory_meta["memory_index_version"] = memory_index_version
        custom_agent_meta: dict[str, Any] | None = None
        if custom_agent_id and str(custom_agent_id).strip():
            from nimbusware_config.persist import load_custom_agent_registry

            reg = load_custom_agent_registry(
                self._repo_root,
                materializer=self._config_materializer,
            )
            agent = reg.get(str(custom_agent_id).strip())
            if agent is None:
                raise ValueError(f"Unknown custom_agent_id: {custom_agent_id}")
            custom_agent_meta = {
                "id": agent.id,
                "display_name": agent.display_name,
                "system_prompt_preview": agent.system_prompt[:240],
                "bound_role_id": agent.bound_role_id,
            }
        project_meta: dict[str, Any] | None = None
        if project_id is not None:
            if not project_workspace_path or not str(project_workspace_path).strip():
                raise ValueError("project_workspace_path required when project_id is set")
            ws = Path(str(project_workspace_path)).resolve()
            if not ws.is_dir():
                raise ValueError(f"project workspace_path is not a directory: {ws}")
            project_meta = {
                "id": str(project_id),
                "name": (project_name or "").strip() or str(project_id),
                "workspace_path": str(ws),
                "template": (project_template or "attach").strip() or "attach",
            }
        operator_settings_meta: dict[str, str] | None = None
        if run_policy_overrides:
            raw_op = run_policy_overrides.get("operator_settings")
            if isinstance(raw_op, dict) and raw_op:
                operator_settings_meta = {str(k): str(v) for k, v in raw_op.items()}
        requirements_meta: dict[str, Any] | None = None
        if requirements is not None:
            if (
                not isinstance(requirements, dict)
                or not str(requirements.get("business_prompt", "")).strip()
            ):
                raise ValueError("requirements.business_prompt required when requirements is set")
            requirements_meta = dict(requirements)
        universal_critique_effective = {
            "default_enabled": uc_block.default_enabled,
            "production_default_on": universal_critique_production_default_on(
                self._repo_root,
                workflow_profile,
                config_materializer=mat,
            ),
            "impl_llm": uc_eff.impl_llm,
            "impl_stub": uc_eff.impl_stub,
            "tw_enabled": uc_eff.tw_enabled,
            "pll_enabled": uc_eff.pll_enabled,
            "fw_enabled": uc_eff.fw_enabled,
            "mi_enabled": uc_eff.mi_enabled,
            "unanimous_gate_enforce": uc_eff.unanimous_gate_enforce,
        }
        agent_evaluator_effective = {
            "enabled": ae_block.enabled,
            "production_default_on": agent_evaluator_production_default_on(
                self._repo_root,
                workflow_profile,
                config_materializer=mat,
            ),
            "llm_evaluation_enabled": ae_block.llm_evaluation_enabled,
        }
        self_refinement_effective = {
            "enabled": sr_block.enabled,
            "ungated_loop": self_refinement_ungated_loop_effective(sr_block),
            "production_ungated": self_refinement_production_ungated_effective(
                self._repo_root,
                workflow_profile,
                config_materializer=mat,
            ),
            "llm_critique_enabled": sr_block.llm_critique_enabled,
        }
        corr = correlation_id or idempotency_key
        if corr is not None:
            existing = self._store.find_run_id_for_run_created_correlation(corr)
            if existing is not None:
                return existing

        run_id = uuid4()
        mat = self._config_materializer
        if mat is not None and getattr(mat, "use_db", False):
            from hermes_orchestrator.merge import policy_snapshot_from_materializer

            snapshot = policy_snapshot_from_materializer(
                mat,
                workflow_profile,
                run_policy_overrides,
            )
        else:
            wf_path = workflow_profile_path(self._repo_root, workflow_profile)
            snapshot = policy_snapshot_from_files(
                self._base_path,
                wf_path,
                run_policy_overrides,
            )
        from hermes_agent_tools.filesystem_jail import default_jail_policy
        from hermes_agent_tools.sandbox import resolve_sandbox_backend
        from nimbusware_hw.cache import get_cached_profile
        from nimbusware_hw.governor import governor_for_profile

        hw_profile = get_cached_profile()
        resource_governor = governor_for_profile(hw_profile).to_metadata()
        agent_tools_effective = {
            "sandbox_backend": resolve_sandbox_backend(),
            "filesystem_jail": default_jail_policy().enabled,
        }
        from hermes_orchestrator.slice_budget_presets import resolve_slice_budget_preset

        slice_budget = resolve_slice_budget_preset(
            operator_settings=operator_settings_meta,
        )
        ms_max_files = ms_block.max_files
        ms_max_loc = ms_block.max_loc
        if ms_block.enabled:
            ms_max_files = slice_budget.max_files
            ms_max_loc = slice_budget.max_loc
        ev = RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            correlation_id=corr,
            metadata={
                "roles_registry": {
                    "yaml_version": self._registry.yaml_version,
                    "content_digest_sha256_16": self._registry.content_digest_sha256_16,
                },
                "policy_snapshot": {
                    "domain_allowlist_normalized": True,
                    "network_egress_domain_count": len(snapshot.network_egress.domain_allowlist),
                },
                "hardware_profile": hw_profile.model_dump_public(),
                "resource_governor": resource_governor,
                "critique_coverage": critique_coverage,
                "stage_graph": stage_graph_snapshot,
                "universal_critique_effective": universal_critique_effective,
                "agent_evaluator_effective": agent_evaluator_effective,
                "self_refinement_effective": self_refinement_effective,
                "micro_slice_effective": {
                    "enabled": ms_block.enabled,
                    "max_files": ms_max_files,
                    "max_loc": ms_max_loc,
                    "e2e_enabled": ms_block.e2e_enabled,
                    "budget_preset": slice_budget.name,
                    "replan_max": slice_budget.replan_max,
                },
                "agent_tools_effective": agent_tools_effective,
                "memory_effective": {
                    "retrieval_enabled": memory_meta["retrieval_enabled"],
                    "index_contribution": memory_meta["index_contribution"],
                    "retrieval_k": memory_meta["retrieval_k"],
                    "excerpt_max_chars": memory_meta["excerpt_max_chars"],
                    "embedding_mode": memory_meta["embedding_mode"],
                    "memory_index_version": memory_meta.get("memory_index_version"),
                },
                "memory": memory_meta,
                "research": research_effective_metadata(research_block),
                "stitch": stitch_effective_metadata(stitch_block),
                "theater": theater_effective_metadata(theater_block),
                **({"custom_agent": custom_agent_meta} if custom_agent_meta else {}),
                **({"project": project_meta} if project_meta else {}),
                **({"requirements": requirements_meta} if requirements_meta else {}),
                **({"operator_settings": operator_settings_meta} if operator_settings_meta else {}),
                **({"maker_approval": {"enabled": True}} if requirements_meta is not None else {}),
                **(
                    {
                        "persona_assignment": {
                            "business_area": (
                                str(business_area_persona_id).strip()
                                if business_area_persona_id
                                else None
                            ),
                            "development_role": (
                                str(development_role_persona_id).strip()
                                if development_role_persona_id
                                else None
                            ),
                        },
                    }
                    if business_area_persona_id or development_role_persona_id
                    else {}
                ),
            },
            payload=RunCreatedPayload(
                workflow_profile=workflow_profile,
                policy_version="1",
                config_snapshot_id=str(uuid4()),
                policy_snapshot=snapshot,
            ),
        )
        self._store.append(ev)
        return run_id

    def _run_created_metadata(self: _CreateRunHost, run_id: UUID) -> dict[str, Any]:
        for row in self._store.list_run_events(str(run_id)):
            if row.get("event_type") == EventType.RUN_CREATED.value:
                meta = row.get("metadata") or {}
                return dict(meta) if isinstance(meta, dict) else {}
        return {}

    def maybe_rebuild_memory_index(self: _CreateRunHost, run_id: UUID) -> Any | None:
        from hermes_memory.contribution import maybe_rebuild_memory_index_for_run

        return maybe_rebuild_memory_index_for_run(
            self._memory_chunk_store,
            self._store,
            run_id=run_id,
            repo_root=self._repo_root,
            run_created_metadata=self._run_created_metadata(run_id),
        )

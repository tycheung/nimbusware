from __future__ import annotations

from typing import Protocol

from orchestrator._pipeline._helpers import (
    UUID,
    Any,
    EventType,
    Path,
    RunCreatedEvent,
    RunCreatedPayload,
    datetime,
    policy_snapshot_from_files,
    stage_graph_from_workflow_profile,
    stage_graph_metadata_snapshot,
    timezone,
    uuid4,
    workflow_profile_dict,
    workflow_profile_path,
)
from orchestrator.registry import RoleRegistry
from store.protocol import EventStore


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
        autonomous: bool | None = None,
        patch_context: dict[str, Any] | None = None,
        work_type: str | None = None,
        work_type_source: str | None = None,
    ) -> UUID:
        mat = self._config_materializer
        from orchestrator._pipeline.create_run_metadata import (
            build_run_created_metadata,
            resolve_custom_agent_meta,
            resolve_project_meta,
            resolve_requirements_meta,
        )
        from orchestrator._pipeline.create_run_preflight import (
            assert_create_run_preflight,
        )
        from orchestrator._pipeline.create_run_workflow_blocks import (
            load_create_run_workflow_blocks,
        )

        critique_coverage = assert_create_run_preflight(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
            registry=self._registry,
            critique_router=self._critique_router,
            business_area_persona_id=business_area_persona_id,
            development_role_persona_id=development_role_persona_id,
        )
        wf_dict = workflow_profile_dict(self._repo_root, workflow_profile, materializer=mat)
        stage_graph_snapshot = stage_graph_metadata_snapshot(
            stage_graph_from_workflow_profile(wf_dict)
        )
        blocks = load_create_run_workflow_blocks(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
            memory_chunk_store=self._memory_chunk_store,
            run_policy_overrides=run_policy_overrides,
        )
        custom_agent_meta = resolve_custom_agent_meta(
            self._repo_root,
            custom_agent_id,
            config_materializer=mat,
        )
        project_meta = resolve_project_meta(
            project_id,
            project_name=project_name,
            project_workspace_path=project_workspace_path,
            project_template=project_template,
        )
        if workflow_profile == "safe_coding" and project_meta:
            from maker.consumer_test_scaffold import maybe_scaffold_safe_coding_workspace

            maybe_scaffold_safe_coding_workspace(Path(str(project_meta["workspace_path"])))
        operator_settings_meta: dict[str, str] | None = None
        if run_policy_overrides:
            raw_op = run_policy_overrides.get("operator_settings")
            if isinstance(raw_op, dict) and raw_op:
                operator_settings_meta = {str(k): str(v) for k, v in raw_op.items()}
        requirements_meta = resolve_requirements_meta(requirements)
        corr = correlation_id or idempotency_key
        if corr is not None:
            existing = self._store.find_run_id_for_run_created_correlation(corr)
            if existing is not None:
                return existing

        run_id = uuid4()
        if mat is not None and getattr(mat, "use_db", False):
            from orchestrator.merge import policy_snapshot_from_materializer

            snapshot = policy_snapshot_from_materializer(
                mat, workflow_profile, run_policy_overrides
            )
        else:
            wf_path = workflow_profile_path(self._repo_root, workflow_profile)
            snapshot = policy_snapshot_from_files(self._base_path, wf_path, run_policy_overrides)

        metadata = build_run_created_metadata(
            registry=self._registry,
            repo_root=self._repo_root,
            workflow_profile=workflow_profile,
            config_materializer=mat,
            blocks=blocks,
            critique_coverage=critique_coverage,
            stage_graph_snapshot=stage_graph_snapshot,
            snapshot=snapshot,
            run_policy_overrides=run_policy_overrides,
            custom_agent_meta=custom_agent_meta,
            project_meta=project_meta,
            requirements_meta=requirements_meta,
            operator_settings_meta=operator_settings_meta,
            autonomous=autonomous,
            patch_context=patch_context,
            work_type=work_type,
            work_type_source=work_type_source,
            business_area_persona_id=business_area_persona_id,
            development_role_persona_id=development_role_persona_id,
        )
        ev = RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            correlation_id=corr,
            metadata=metadata,
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
        from memory.index.contribution import maybe_rebuild_memory_index_for_run

        return maybe_rebuild_memory_index_for_run(
            self._memory_chunk_store,
            self._store,
            run_id=run_id,
            repo_root=self._repo_root,
            run_created_metadata=self._run_created_metadata(run_id),
        )

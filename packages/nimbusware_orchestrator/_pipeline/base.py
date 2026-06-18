from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from agent_core.models import (
    EventType,
    FindingFixStrictnessSettings,
    RunCreatedEvent,
    validate_event_dict,
)
from nimbusware_orchestrator.critique_routing import load_critique_router
from nimbusware_orchestrator.fast_slice_critique import (
    fast_slice_env_effective,
    fast_slice_skips_optional_critique_matrix,
    max_open_finding_severity,
)
from nimbusware_orchestrator.integrator_gate import workflow_profile_from_run_created_rows
from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.stage_graph import stage_graph_from_run_created_metadata
from nimbusware_orchestrator.workflow_universal_critique import (
    EffectiveUniversalCritique,
    effective_universal_critique,
)
from nimbusware_store.protocol import EventStore, serialized_event_from_row


class RunOrchestratorBase:
    def __init__(
        self,
        store: EventStore,
        registry: RoleRegistry,
        *,
        repo_root: Path,
        base_config_path: Path,
        config_materializer: Any | None = None,
        memory_chunk_store: Any | None = None,
        bundle_outcome_store: Any | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._repo_root = repo_root
        self._base_path = base_config_path
        self._config_materializer = config_materializer
        self._memory_chunk_store = memory_chunk_store
        self._bundle_outcome_store = bundle_outcome_store
        self._critique_router = load_critique_router(
            repo_root,
            config_materializer,
        )

    @property
    def config_materializer(self) -> Any | None:
        return self._config_materializer

    @property
    def repo_root(self) -> Path:
        """Repository root frozen at construct time (configs, bundles catalog, …)."""
        return self._repo_root

    def _base_cfg(self) -> dict[str, Any]:
        mat = self._config_materializer
        if mat is not None and getattr(mat, "use_db", False):
            raw = mat.get_model_routing_base()
            return raw if isinstance(raw, dict) else {}
        return load_yaml(self._base_path)

    def policy_snapshot_for_run(self, run_id: UUID) -> dict[str, Any]:
        for row in self._store.list_run_events(str(run_id)):
            if row["event_type"] == EventType.RUN_CREATED.value:
                d = serialized_event_from_row(row)
                ev = validate_event_dict(d)
                if not isinstance(ev, RunCreatedEvent):
                    continue
                snap = ev.payload.policy_snapshot
                if snap is None:
                    return {}
                return snap.model_dump(mode="json")
        return {}

    def _strictness_context(self, run_id: UUID) -> dict[str, Any]:
        snap = self.policy_snapshot_for_run(run_id)
        fs = snap.get("finding_fix_strictness")
        if isinstance(fs, dict):
            return {"finding_fix_strictness": FindingFixStrictnessSettings.model_validate(fs)}
        return {}

    def _selected_model_for_run(self, run_id: UUID) -> str | None:
        for row in reversed(self._store.list_run_events(str(run_id))):
            et = row["event_type"]
            pl = row.get("payload") or {}
            if et == EventType.MODEL_SELECTED_PRIMARY.value:
                mid = pl.get("model_id")
                if isinstance(mid, str):
                    return mid
            if et == EventType.MODEL_SELECTED_FALLBACK.value:
                mid = pl.get("selected_model_id")
                if isinstance(mid, str):
                    return mid
        return None

    def _effective_universal_critique_for_run(self, run_id: UUID) -> EffectiveUniversalCritique:
        wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
        return effective_universal_critique(self._repo_root, wf)

    def _stage_graph_snapshot_for_run(self, run_id: UUID) -> dict[str, Any] | None:
        for row in self._store.list_run_events(str(run_id)):
            if row.get("event_type") != EventType.RUN_CREATED.value:
                continue
            meta = row.get("metadata")
            if isinstance(meta, dict):
                return stage_graph_from_run_created_metadata(meta)
            break
        return None

    def _fast_slice_should_skip_optional_critique_matrix(self, run_id: UUID) -> bool:
        rows = self._store.list_run_events(str(run_id))
        yaml_enabled = False
        for row in rows:
            if row.get("event_type") != EventType.RUN_CREATED.value:
                continue
            meta = row.get("metadata")
            if isinstance(meta, dict):
                fs_eff = meta.get("fast_slice_effective")
                if isinstance(fs_eff, dict):
                    yaml_enabled = bool(fs_eff.get("enabled"))
            break
        if not fast_slice_env_effective(yaml_enabled=yaml_enabled):
            return False
        return fast_slice_skips_optional_critique_matrix(max_open_finding_severity(rows))

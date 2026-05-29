"""MVP run lifecycle: create → preflight → plan stage → writer loop (plan §12 Phase 1).

Scraper or other roles that perform outbound HTTP should use
``hermes_executor.fetch.egress_checked_httpx_get`` with the frozen
``PolicySnapshot.network_egress`` fields (domain allowlist, scraper role UUIDs)
and the acting role id, instead of calling ``httpx`` directly.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    FindingFixStrictnessSettings,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    ModelPreflightStartedEvent,
    ModelPreflightStartedPayload,
    ModelSelectedFallbackEvent,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryEvent,
    ModelSelectedPrimaryPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    RunStartedEvent,
    RunStartedPayload,
    SelfRefinementLoopSignalledEvent,
    SelfRefinementLoopSignalledPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
    validate_event_dict,
)
from hermes_executor.fetch import EgressResponseTooLarge
from hermes_extensions import SelfRefinementPolicy, load_self_refinement_policy
from hermes_extensions.phase2 import AgentEvaluator, agent_evaluator_score_band
from hermes_extensions.self_refinement import SelfRefinementEvaluator
from hermes_orchestrator.anti_deadlock import (
    load_anti_deadlock_settings,
    should_emit_anti_deadlock_escalation,
)
from hermes_orchestrator.critique_routing import (
    assert_critique_coverage_complete,
    critique_coverage_snapshot,
    load_critique_router,
    taxonomy_keys_for_run_lifecycle,
)
from hermes_orchestrator.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_high_severity_findings,
    load_escalate_after_cumulative_stage_failures,
    load_notice_escalate_at_cumulative_findings,
)
from hermes_orchestrator.ingress import (
    assert_agent_evaluator_persona_in_shelves,
    assert_bundle_catalog_maps_resolve,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_stage_graph_valid,
    assert_taxonomy_keys_resolve,
)
from hermes_orchestrator.integration_adapter_writer_stage import (
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    integration_adapter_writer_stage_would_emit,
)
from hermes_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_bundle_title_for_bundle_id,
    load_integrator_gate_emit_enabled,
    parse_integrator_gate_project_tags,
    rank_bundle_compatibility_candidates,
    select_bundle_id_for_workflow,
    workflow_profile_from_run_created_rows,
)
from hermes_orchestrator.llm_plan import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    MODULE_INTEGRATOR_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
    emit_stub_frontend_writer_critique_panel,
    emit_stub_implementation_critique_panel,
    emit_stub_module_integrator_critique_panel,
    emit_stub_plan_stage,
    emit_stub_planner_critique_panel,
    emit_stub_self_refinement_critique_panel,
    emit_stub_test_writer_critique_panel,
    execute_agent_evaluator_policy_llm,
    execute_frontend_writer_critique_llm,
    execute_implementation_critique_llm,
    execute_module_integrator_critique_llm,
    execute_plan_stage_llm,
    execute_planner_critique_llm,
    execute_self_refinement_critique_llm,
    execute_test_writer_critique_llm,
)
from hermes_orchestrator.merge import load_yaml, policy_snapshot_from_files
from hermes_orchestrator.outbound_http import egress_checked_get_for_run
from hermes_orchestrator.parallel_writers import WriterStageResult, run_parallel_writer_group
from hermes_orchestrator.persona_coverage_critique import (
    emit_stub_persona_coverage_critique_panel,
    execute_persona_coverage_critique_llm,
)
from hermes_orchestrator.persona_shelf_auto_create import try_auto_create_persona_if_missing
from hermes_orchestrator.persona_shelf_promotion import try_auto_promote_probation_persona
from hermes_orchestrator.preflight import run_model_preflight
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.run_dispatch import (
    RunDispatchTask,
    get_run_queue,
    run_dispatch_enabled,
    task_payload_workspace,
)
from hermes_orchestrator.scraper_artifacts import resolve_scraper_artifact_base_dir
from hermes_orchestrator.scraper_stage import ScraperFetchConfig, load_scraper_fetch_config
from hermes_orchestrator.escalation_execution import append_run_escalated
from hermes_orchestrator.security_critique import (
    emit_stub_security_critique_panel,
    execute_security_critique_llm,
    run_security_scan_summary,
)
from hermes_orchestrator.security_scan import run_security_scan, security_scan_tool_summary
from hermes_orchestrator.stage_graph import (
    event_metadata_for_stage,
    parallel_group_members,
    stage_graph_from_run_created_metadata,
    stage_graph_from_workflow_profile,
    stage_graph_metadata_snapshot,
    stage_graph_node_lookup,
)
from hermes_orchestrator.test_writer_stage import run_test_writer_stage
from hermes_orchestrator.traceback_router import suggest_owner_role_from_verifier_log
from hermes_orchestrator.verifier_escalation import load_escalate_on_first_verifier_failure
from hermes_orchestrator.verifiers import run_writer_verifier_bundle
from hermes_orchestrator.workflow_agent_evaluator import (
    agent_evaluator_llm_branch_effective,
    agent_evaluator_llm_stub_env_enabled,
    agent_evaluator_production_default_on,
    agent_evaluator_production_llm_fallback_enabled,
    agent_evaluator_rules_derived_llm_evaluation,
    parse_agent_evaluator_workflow_block,
    persona_coverage_critique_effective,
    persona_coverage_critique_llm_branch_effective,
)
from hermes_orchestrator.workflow_escalation import parse_escalation_workflow_block
from hermes_orchestrator.workflow_integration_adapter_writer import (
    parse_integration_adapter_writer_workflow_block,
)
from hermes_orchestrator.workflow_parallel_writers import (
    parallel_writers_enabled,
    test_writer_llm_body_enabled,
    test_writer_llm_stub_fallback,
    test_writer_stage_enabled,
)
from hermes_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path
from hermes_orchestrator.workflow_security import security_scan_metadata_on_verify_enabled
from hermes_orchestrator.performance_critique import (
    emit_stub_performance_critique_panel,
    execute_performance_critique_llm,
)
from hermes_orchestrator.network_resilience_critique import (
    emit_stub_network_resilience_critique_panel,
    execute_network_resilience_critique_llm,
)
from hermes_orchestrator.network_resilience_scan import run_network_resilience_scan_summary
from hermes_orchestrator.refactor_stage import emit_refactor_stage_and_critique
from hermes_orchestrator.workflow_network_resilience_critique import (
    parse_network_resilience_critique_workflow_block,
    network_resilience_critique_effective,
    network_resilience_critique_llm_branch_effective,
)
from hermes_orchestrator.workflow_performance_critique import (
    parse_performance_critique_workflow_block,
    performance_critique_effective,
    performance_critique_llm_branch_effective,
)
from hermes_orchestrator.workflow_refactor import (
    parse_refactor_workflow_block,
    refactor_stage_effective,
)
from hermes_orchestrator.workflow_security_critique import (
    parse_security_critique_workflow_block,
    security_critique_effective,
    security_critique_llm_branch_effective,
)
from hermes_orchestrator.workflow_self_refinement import (
    parse_self_refinement_workflow_block,
    self_refinement_llm_critique_branch_effective,
    self_refinement_llm_critique_effective_for_run,
    self_refinement_production_ungated_effective,
    self_refinement_ungated_loop_effective,
)
from hermes_orchestrator.workflow_universal_critique import (
    EffectiveUniversalCritique,
    effective_universal_critique,
    parse_universal_critique_workflow_block,
    universal_critique_production_default_on,
)
from hermes_store.memory import InMemoryEventStore
from hermes_store.protocol import EventStore, serialized_event_from_row


def _coerce_samples_ms(raw: Any) -> list[int] | None:
    """Coerce ``evidence['health_latency_samples_ms']`` for payload persistence.

    The preflight evidence dict is loosely typed (``dict[str, Any]``); the
    payload field requires ``list[int] | None`` with non-negative entries
    (fo124). Filters defensively so a corrupted upstream entry can't crash
    persistence: returns ``None`` for non-list values, skips non-int / negative
    entries silently, returns ``None`` if every entry was filtered out.
    """
    if not isinstance(raw, list):
        return None
    cleaned: list[int] = []
    for v in raw:
        if isinstance(v, bool) or not isinstance(v, int):
            continue
        if v < 0:
            continue
        cleaned.append(v)
    return cleaned or None


def _agent_evaluator_auto_promote_env_disabled() -> bool:
    raw = os.environ.get("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE", "").strip().lower()
    return raw in ("0", "false", "no")


def _agent_evaluator_auto_create_env_disabled() -> bool:
    raw = os.environ.get("HERMES_AGENT_EVALUATOR_AUTO_CREATE", "").strip().lower()
    return raw in ("0", "false", "no")


def _self_refinement_stage_marker_env_disabled() -> bool:
    """When ``HERMES_SELF_REFINEMENT_STAGE_MARKER`` is ``0``/``false``/``no``, skip marker emit."""
    raw = os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "").strip().lower()
    return raw in ("0", "false", "no")


def _self_refinement_auto_promote_env_disabled() -> bool:
    raw = os.environ.get("HERMES_SELF_REFINEMENT_AUTO_PROMOTE", "").strip().lower()
    return raw in ("0", "false", "no")


_SELF_REFINEMENT_POLICY_STAGE = "self_refinement:policy"
_SELF_REFINEMENT_MAX_ITER_REASON = "self_refinement_max_iterations"


def _self_refinement_marker_count(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == _SELF_REFINEMENT_POLICY_STAGE
    )


def _last_self_refinement_loop_should_continue(rows: list[dict[str, Any]]) -> bool:
    signals = [
        r
        for r in rows
        if r.get("event_type") == EventType.SELF_REFINEMENT_LOOP_SIGNALLED.value
    ]
    if not signals:
        return False
    last = max(signals, key=lambda x: int(x["store_seq"]))
    pl = last.get("payload") or {}
    return bool(pl.get("should_continue")) and pl.get("gate_decision") == "proceed"


def _self_refinement_max_iterations_exceeded(rows: list[dict[str, Any]]) -> bool:
    return any(
        r.get("event_type") == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("reason_code") == _SELF_REFINEMENT_MAX_ITER_REASON
        for r in rows
    )


def _persona_id_from_assignment_slot(raw: object) -> str | None:
    if isinstance(raw, str):
        rid = raw.strip()
        return rid or None
    if isinstance(raw, dict):
        val = raw.get("id")
        if val is None:
            val = raw.get("persona_id")
        if val is not None:
            rid = str(val).strip()
            return rid or None
    return None


class RunOrchestrator:
    def __init__(
        self,
        store: EventStore,
        registry: RoleRegistry,
        *,
        repo_root: Path,
        base_config_path: Path,
        config_materializer: Any | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._repo_root = repo_root
        self._base_path = base_config_path
        self._config_materializer = config_materializer
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
        return load_yaml(self._base_path)

    def create_run(
        self,
        workflow_profile: str,
        *,
        idempotency_key: UUID | None = None,
        correlation_id: UUID | None = None,
        run_policy_overrides: dict[str, Any] | None = None,
        business_area_persona_id: str | None = None,
        development_role_persona_id: str | None = None,
        custom_agent_id: str | None = None,
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
            from hermes_config.persist import load_persona_shelf
            from hermes_orchestrator.ingress import assert_persona_assignment_valid

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
        from hermes_orchestrator.workflow_micro_slice import parse_micro_slice_workflow_block

        ms_block = parse_micro_slice_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        custom_agent_meta: dict[str, Any] | None = None
        if custom_agent_id and str(custom_agent_id).strip():
            from hermes_config.persist import load_custom_agent_registry

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
                "critique_coverage": critique_coverage,
                "stage_graph": stage_graph_snapshot,
                "universal_critique_effective": universal_critique_effective,
                "agent_evaluator_effective": agent_evaluator_effective,
                "self_refinement_effective": self_refinement_effective,
                "micro_slice_effective": {
                    "enabled": ms_block.enabled,
                    "max_files": ms_block.max_files,
                    "max_loc": ms_block.max_loc,
                },
                **(
                    {"custom_agent": custom_agent_meta} if custom_agent_meta else {}
                ),
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

    def record_micro_slice_plan(
        self,
        run_id: UUID,
        plan: dict[str, Any] | Any,
    ) -> None:
        """Persist a slice plan marker for timeline read-models (fo152)."""
        from hermes_orchestrator.micro_slice import SlicePlan, parse_slice_plan

        p: SlicePlan = plan if isinstance(plan, SlicePlan) else parse_slice_plan(plan)
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={
                    "slice_plan": True,
                    "slice_id": p.slice_id,
                    "target_paths": list(p.target_paths),
                    "rationale": p.rationale,
                    "acceptance_criteria": p.acceptance_criteria,
                },
                payload=StageStartedPayload(stage_name="slice.plan", attempt=1),
            ),
        )

    def record_micro_slice_gate(
        self,
        run_id: UUID,
        plan: dict[str, Any] | Any,
        *,
        verify_ok: bool,
        critique_verdicts: list[str] | None = None,
        tests_passed: bool | None = None,
        diff_unified: str = "",
        test_output: str = "",
    ):
        """Run per-slice gate chain and append pass/fail stage events (fo153–fo154)."""
        from hermes_orchestrator.micro_slice import SlicePlan, parse_slice_plan
        from hermes_orchestrator.slice_context_packet import build_slice_context_packet
        from hermes_orchestrator.slice_gate import SliceGateChainResult, run_slice_gate_chain

        p: SlicePlan = plan if isinstance(plan, SlicePlan) else parse_slice_plan(plan)
        gate = run_slice_gate_chain(
            p,
            verify_ok=verify_ok,
            critique_verdicts=critique_verdicts,
            tests_passed=tests_passed,
        )
        packet = build_slice_context_packet(
            p,
            diff_unified=diff_unified,
            test_output=test_output,
            gate=gate,
        )
        meta = {
            **gate.to_metadata(),
            "slice_context_packet": packet.model_dump(mode="json"),
        }
        now = datetime.now(timezone.utc)
        if gate.passed:
            self._store.append(
                StagePassedEvent(
                    event_type=EventType.STAGE_PASSED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=now,
                    metadata=meta,
                    payload=StagePassedPayload(stage_name="slice.gate", duration_ms=0),
                ),
            )
        else:
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=now,
                    metadata=meta,
                    payload=StageFailedPayload(
                        stage_name="slice.gate",
                        reason_code="slice_gate_blocked",
                        message="per-slice gate did not pass",
                    ),
                ),
            )
        return gate

    def egress_checked_fetch_url(
        self,
        run_id: UUID,
        url: str,
        actor_role_id: UUID,
        *,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> httpx.Response:
        """Opt-in outbound GET using frozen ``run.created`` egress policy.

        Set ``HERMES_OUTBOUND_FETCH_ENABLED=1`` (or ``true``/``yes``) to allow network I/O.
        """
        if os.environ.get("HERMES_OUTBOUND_FETCH_ENABLED", "").lower() not in (
            "1",
            "true",
            "yes",
        ):
            msg = (
                "Set HERMES_OUTBOUND_FETCH_ENABLED=1 to perform outbound GET "
                "from the orchestrator"
            )
            raise RuntimeError(msg)
        return egress_checked_get_for_run(
            self._store,
            run_id,
            url,
            actor_role_id=actor_role_id,
            timeout_seconds=timeout_seconds,
            client=client,
        )

    @staticmethod
    def _parse_content_length_header(resp: httpx.Response) -> int | None:
        raw = resp.headers.get("content-length")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def _scraper_stage_audit_metadata(
        host: str,
        http_status: int,
        nbytes: int,
        attempts_used: int,
        *,
        content_length_header: int | None = None,
    ) -> dict[str, Any]:
        inner: dict[str, Any] = {
            "url_host": host,
            "http_status": http_status,
            "bytes": nbytes,
            "attempts": attempts_used,
        }
        if content_length_header is not None:
            inner["content_length"] = content_length_header
        return {"scraper_fetch": inner}

    @staticmethod
    def _scraper_body_digest_and_snippet(content: bytes, snippet_max_bytes: int) -> dict[str, Any]:
        out: dict[str, Any] = {"body_sha256_hex": hashlib.sha256(content).hexdigest()}
        if snippet_max_bytes > 0:
            raw = content[:snippet_max_bytes]
            out["body_snippet_preview"] = raw.decode("utf-8", errors="replace")
        return out

    def _persist_scraper_response_artifact(
        self,
        run_id: UUID,
        url_index: int,
        content: bytes,
        persist_cap: int,
    ) -> dict[str, Any]:
        """Write truncated response bytes under artifact base dir; returns metadata fields."""
        base_dir = resolve_scraper_artifact_base_dir(self._repo_root)
        base_dir.mkdir(parents=True, exist_ok=True)
        run_dir = base_dir / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        blob = content[:persist_cap]
        digest_full = hashlib.sha256(content).hexdigest()
        fname = f"url{url_index:02d}_{digest_full[:32]}.bin"
        out_path = run_dir / fname
        out_path.write_bytes(blob)
        artifact_digest = hashlib.sha256(blob).hexdigest()
        try:
            rel = out_path.relative_to(base_dir)
        except ValueError:
            rel = Path(fname)
        return {
            "artifact_relpath": str(rel).replace("\\", "/"),
            "artifact_sha256": artifact_digest,
            "artifact_bytes_written": len(blob),
        }

    def _scraper_get_with_retries(
        self,
        run_id: UUID,
        scraper_url: str,
        actor: UUID,
        client: httpx.Client | None,
        cfg: ScraperFetchConfig,
        max_response_bytes: int | None,
    ) -> tuple[httpx.Response, int]:
        last_err: BaseException | None = None
        for attempt in range(1, cfg.max_attempts + 1):
            try:
                fetch_kw: dict[str, Any] = {
                    "timeout_seconds": 30.0,
                    "client": client,
                }
                if max_response_bytes is not None:
                    fetch_kw["max_response_bytes"] = max_response_bytes
                resp = egress_checked_get_for_run(
                    self._store,
                    run_id,
                    scraper_url,
                    actor_role_id=actor,
                    **fetch_kw,
                )
                return resp, attempt
            except PermissionError:
                raise
            except EgressResponseTooLarge:
                raise
            except (OSError, RuntimeError, ValueError, httpx.HTTPError) as exc:
                last_err = exc
                if attempt >= cfg.max_attempts:
                    break
                if cfg.backoff_seconds > 0:
                    time.sleep(cfg.backoff_seconds)
        msg = str(last_err)[:2000] if last_err else "scraper fetch failed"
        raise RuntimeError(msg)

    def _effective_scraper_budget_bytes(
        self,
        run_id: UUID,
        cfg: ScraperFetchConfig,
    ) -> int | None:
        snap = self.policy_snapshot_for_run(run_id)
        ne = snap.get("network_egress") if isinstance(snap, dict) else None
        policy_b: int | None = None
        if isinstance(ne, dict):
            pb = ne.get("budget_bytes_per_run")
            if isinstance(pb, int) and pb >= 0:
                policy_b = pb
        caps: list[int] = []
        if policy_b is not None:
            caps.append(policy_b)
        if cfg.max_bytes is not None:
            caps.append(cfg.max_bytes)
        return min(caps) if caps else None

    def run_optional_scraper_fetch_stage(
        self,
        run_id: UUID,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        """Optional ``scraper:fetch`` stage from workflow YAML (requires env for HTTP)."""
        wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
        if not wf:
            return
        cfg = load_scraper_fetch_config(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if not cfg.enabled or not cfg.fetch_urls:
            return
        first_host = urlparse(cfg.fetch_urls[0]).hostname or ""
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageStartedPayload(stage_name="scraper:fetch", attempt=1),
            ),
        )
        if os.environ.get("HERMES_OUTBOUND_FETCH_ENABLED", "").lower() not in (
            "1",
            "true",
            "yes",
        ):
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata=self._scraper_stage_audit_metadata(first_host, 0, 0, 0),
                    payload=StageFailedPayload(
                        stage_name="scraper:fetch",
                        reason_code="outbound_fetch_disabled",
                        message="HERMES_OUTBOUND_FETCH_ENABLED not set",
                    ),
                ),
            )
            return
        budget = self._effective_scraper_budget_bytes(run_id, cfg)
        remaining: int | None = budget
        actor = self._registry.resolve(cfg.actor_role_key)
        fetches_out: list[dict[str, Any]] = []

        def fail_meta(host: str, partial: list[dict[str, Any]]) -> dict[str, Any]:
            inner: dict[str, Any] = {"fetches": list(partial)}
            if host:
                inner["failed_url_host"] = host
            return {"scraper_fetch": inner}

        for url_index, scraper_url in enumerate(cfg.fetch_urls):
            parsed_host = urlparse(scraper_url).hostname or ""
            per_cap = remaining if remaining is not None else None
            if per_cap is not None and per_cap <= 0:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="scraper_budget_exceeded",
                            message="no bytes remaining for next URL",
                        ),
                    ),
                )
                return
            try:
                resp, attempts_used = self._scraper_get_with_retries(
                    run_id,
                    scraper_url,
                    actor,
                    client,
                    cfg,
                    per_cap,
                )
            except PermissionError as exc:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="egress_denied",
                            message=str(exc)[:2000],
                        ),
                    ),
                )
                return
            except EgressResponseTooLarge as exc:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="scraper_budget_exceeded",
                            message=str(exc)[:2000],
                        ),
                    ),
                )
                return
            except RuntimeError as exc:
                self._store.append(
                    StageFailedEvent(
                        event_type=EventType.STAGE_FAILED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fail_meta(parsed_host, fetches_out),
                        payload=StageFailedPayload(
                            stage_name="scraper:fetch",
                            reason_code="scraper_fetch_error",
                            message=str(exc)[:2000],
                        ),
                    ),
                )
                return
            nbytes = len(resp.content)
            status_code = int(resp.status_code)
            cl_hdr = self._parse_content_length_header(resp)
            row: dict[str, Any] = {
                "url_host": parsed_host,
                "http_status": status_code,
                "bytes": nbytes,
                "attempts": attempts_used,
            }
            if cl_hdr is not None:
                row["content_length"] = cl_hdr
            row.update(
                self._scraper_body_digest_and_snippet(resp.content, cfg.body_snippet_max_bytes),
            )
            if cfg.persist_artifacts_max_bytes_per_url is not None:
                try:
                    row.update(
                        self._persist_scraper_response_artifact(
                            run_id,
                            url_index,
                            resp.content,
                            cfg.persist_artifacts_max_bytes_per_url,
                        ),
                    )
                except OSError as exc:
                    self._store.append(
                        StageFailedEvent(
                            event_type=EventType.STAGE_FAILED,
                            event_id=uuid4(),
                            run_id=run_id,
                            occurred_at=datetime.now(timezone.utc),
                            metadata=fail_meta(parsed_host, fetches_out),
                            payload=StageFailedPayload(
                                stage_name="scraper:fetch",
                                reason_code="scraper_fetch_error",
                                message=f"artifact write failed: {exc!s}"[:2000],
                            ),
                        ),
                    )
                    return
            fetches_out.append(row)
            if remaining is not None:
                remaining -= nbytes

        self._store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"scraper_fetch": {"fetches": fetches_out}},
                payload=StagePassedPayload(stage_name="scraper:fetch", duration_ms=0),
            ),
        )

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

    def start_run_after_preflight(self, run_id: UUID) -> None:
        base = self._base_cfg()
        runtime = base.get("runtime") or {}
        models = base.get("models") or {}
        primary = (models.get("primary") or {}).get("id", "llama3.1:8b")
        fb_raw = models.get("fallbacks") or []
        fallbacks = [
            str(x.get("id")) for x in fb_raw if isinstance(x, dict) and x.get("id") is not None
        ]

        base_url = str(runtime.get("base_url", "http://localhost:11434"))
        health = str(runtime.get("health_endpoint", "/api/tags"))
        preflight_cfg = base.get("preflight") if isinstance(base.get("preflight"), dict) else {}

        self._store.append(
            ModelPreflightStartedEvent(
                event_type=EventType.MODEL_PREFLIGHT_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightStartedPayload(
                    provider=str(runtime.get("provider", "ollama")),
                    base_url=base_url,
                    requested_model_id=primary,
                ),
            ),
        )

        selected, evidence, used_primary = run_model_preflight(
            base_url=base_url,
            health_path=health,
            primary_model_id=primary,
            fallback_model_ids=fallbacks,
            timeout_seconds=float(runtime.get("request_timeout_seconds", 60)),
            preflight_cfg=preflight_cfg,
        )

        checks = list(evidence.get("checks_passed", []))
        self._store.append(
            ModelPreflightPassedEvent(
                event_type=EventType.MODEL_PREFLIGHT_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightPassedPayload(
                    provider=str(runtime.get("provider", "ollama")),
                    validated_model_id=selected,
                    context_tokens=int(evidence.get("context_tokens", 8192)),
                    p95_latency_ms=int(evidence.get("p95_latency_ms", 0)),
                    checks_passed=checks,
                    preflight_latency_sample_count=evidence.get("preflight_latency_sample_count"),
                    p95_latency_source=evidence.get("p95_latency_source"),
                    health_latency_samples_ms=_coerce_samples_ms(
                        evidence.get("health_latency_samples_ms"),
                    ),
                ),
            ),
        )
        if used_primary:
            self._store.append(
                ModelSelectedPrimaryEvent(
                    event_type=EventType.MODEL_SELECTED_PRIMARY,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    model_id=selected,
                    payload=ModelSelectedPrimaryPayload(
                        provider=str(runtime.get("provider", "ollama")),
                        model_id=selected,
                    ),
                ),
            )
        else:
            self._store.append(
                ModelSelectedFallbackEvent(
                    event_type=EventType.MODEL_SELECTED_FALLBACK,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    model_id=selected,
                    payload=ModelSelectedFallbackPayload(
                        provider=str(runtime.get("provider", "ollama")),
                        selected_model_id=selected,
                        reason_code="primary_unavailable_or_failed_preflight",
                        original_model_id=primary,
                    ),
                ),
            )
        self._store.append(
            RunStartedEvent(
                event_type=EventType.RUN_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=RunStartedPayload(started_by="orchestrator"),
            ),
        )

    def _execute_plan_stage_stub(self, run_id: UUID) -> None:
        emit_stub_plan_stage(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
        )

    def execute_plan_stage(self, run_id: UUID) -> None:
        if os.environ.get("HERMES_USE_LLM", "").lower() in ("1", "true", "yes"):
            base = self._base_cfg()
            runtime = base.get("runtime") or {}
            base_url = str(runtime.get("base_url", "http://localhost:11434"))
            model = self._selected_model_for_run(run_id)
            if model:
                try:
                    execute_plan_stage_llm(
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                        base_url=base_url,
                        model_id=model,
                        timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                    )
                    return
                except Exception:
                    pass
        self._execute_plan_stage_stub(run_id)

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

    def _maybe_emit_stage_failed_for_implementation_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit ``stage.failed`` when last ``implementation.critique`` gate is FAIL.

        Default off: set ``HERMES_IMPLEMENTATION_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL`` to
        a truthy value so downstream consumers (escalation, timeline) can react without
        changing default CI behavior. When unset, follows workflow ``universal_critique``.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.impl_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code")
            == "implementation_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_impl_gate: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != IMPLEMENTATION_CRITIQUE_STAGE:
                continue
            last_impl_gate = pl
        if not last_impl_gate:
            return
        verdict_raw = last_impl_gate.get("verdict")
        is_fail = verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"
        if not is_fail:
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=IMPLEMENTATION_CRITIQUE_STAGE,
                    reason_code="implementation_critique_gate_fail",
                    message="implementation.critique gate verdict was FAIL",
                ),
            ),
        )

    def _maybe_emit_stage_failed_for_test_writer_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit ``stage.failed`` when last ``test_writer.critique`` gate is FAIL.

        Default off: set ``HERMES_TEST_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL`` to a
        truthy value (requires a ``test_writer.critique`` gate event from the optional
        test-writer critique pass). When unset, follows workflow ``universal_critique``.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.tw_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "test_writer_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_tw_gate: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != TEST_WRITER_CRITIQUE_STAGE:
                continue
            last_tw_gate = pl
        if not last_tw_gate:
            return
        verdict_raw = last_tw_gate.get("verdict")
        is_fail = verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"
        if not is_fail:
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=TEST_WRITER_CRITIQUE_STAGE,
                    reason_code="test_writer_critique_gate_fail",
                    message="test_writer.critique gate verdict was FAIL",
                ),
            ),
        )

    def _maybe_emit_stage_failed_for_planner_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit ``stage.failed`` when last ``planner.critique`` gate is FAIL.

        Default off: set ``HERMES_PLANNER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL`` to a truthy
        value (requires a ``planner.critique`` gate from the optional post-verify panel).
        When unset, follows workflow ``universal_critique``.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.pll_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "planner_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_gate: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != PLANNER_CRITIQUE_STAGE:
                continue
            last_gate = pl
        if not last_gate:
            return
        verdict_raw = last_gate.get("verdict")
        is_fail = verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"
        if not is_fail:
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=PLANNER_CRITIQUE_STAGE,
                    reason_code="planner_critique_gate_fail",
                    message="planner.critique gate verdict was FAIL",
                ),
            ),
        )

    def _maybe_emit_stage_failed_for_frontend_writer_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.fw_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "frontend_writer_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_gate = self._last_critique_gate_payload_for_stage(rows, FRONTEND_WRITER_CRITIQUE_STAGE)
        if not last_gate or not self._critique_gate_verdict_is_fail(last_gate):
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=FRONTEND_WRITER_CRITIQUE_STAGE,
                    reason_code="frontend_writer_critique_gate_fail",
                    message="frontend_writer.critique gate verdict was FAIL",
                ),
            ),
        )

    def _maybe_emit_stage_failed_for_module_integrator_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.mi_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "module_integrator_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_gate = self._last_critique_gate_payload_for_stage(
            rows,
            MODULE_INTEGRATOR_CRITIQUE_STAGE,
        )
        if not last_gate or not self._critique_gate_verdict_is_fail(last_gate):
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=MODULE_INTEGRATOR_CRITIQUE_STAGE,
                    reason_code="module_integrator_critique_gate_fail",
                    message="module_integrator.critique gate verdict was FAIL",
                ),
            ),
        )

    @staticmethod
    def _critique_gate_verdict_is_fail(gate_payload: dict[str, Any]) -> bool:
        verdict_raw = gate_payload.get("verdict")
        return verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"

    @staticmethod
    def _last_critique_gate_payload_for_stage(
        rows: list[dict[str, Any]],
        stage_name: str,
    ) -> dict[str, Any] | None:
        last: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != stage_name:
                continue
            last = pl
        return last

    @staticmethod
    def _critique_gate_fail_finding_already_emitted(
        rows: list[dict[str, Any]],
        stage_name: str,
    ) -> bool:
        for r in rows:
            if r.get("event_type") != EventType.FINDING_CREATED.value:
                continue
            meta = r.get("metadata") or {}
            if meta.get("critique_gate_fail_finding") and meta.get("stage_name") == stage_name:
                return True
        return False

    def _repro_steps_from_critique_gate(self, gate_pl: dict[str, Any]) -> list[str]:
        lines = [
            f"stage={gate_pl.get('stage_name')}",
            f"verdict={gate_pl.get('verdict')}",
        ]
        code = (gate_pl.get("failure_reason_code") or "").strip()
        if code:
            lines.append(f"failure_reason_code={code}")
        fc = gate_pl.get("failing_critics")
        if isinstance(fc, list) and fc:
            lines.append(f"failing_critics={len(fc)} critic(s)")
        ff = gate_pl.get("failing_finding_ids")
        if isinstance(ff, list) and ff:
            lines.append(f"failing_finding_ids={len(ff)} id(s)")
        return lines[:40]

    def _maybe_emit_critique_gate_fail_findings(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit a LOW ``finding.created`` when last critique gate verdict is FAIL.

        Default off: set ``HERMES_*_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL`` (per stage) or
        workflow ``emit_finding_on_gate_fail``. Scoped to **implementation** / **test_writer**
        / **planner** critique stages only.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        stages: list[tuple[bool, str, str]] = [
            (u.impl_emit_finding_on_gate_fail, IMPLEMENTATION_CRITIQUE_STAGE, "backend_writer"),
            (u.tw_emit_finding_on_gate_fail, TEST_WRITER_CRITIQUE_STAGE, "test_writer"),
            (u.pll_emit_finding_on_gate_fail, PLANNER_CRITIQUE_STAGE, "planner"),
            (u.fw_emit_finding_on_gate_fail, FRONTEND_WRITER_CRITIQUE_STAGE, "frontend_writer"),
            (
                u.mi_emit_finding_on_gate_fail,
                MODULE_INTEGRATOR_CRITIQUE_STAGE,
                "module_integrator",
            ),
        ]
        rows = self._store.list_run_events(str(run_id))
        ctx = self._strictness_context(run_id)
        for enabled, stage_name, role_key in stages:
            if not enabled:
                continue
            if self._critique_gate_fail_finding_already_emitted(rows, stage_name):
                continue
            gate_pl = self._last_critique_gate_payload_for_stage(rows, stage_name)
            if not gate_pl:
                continue
            if not self._critique_gate_verdict_is_fail(gate_pl):
                continue
            owner = self._registry.resolve(role_key)
            source_artifact = f"critique_gate:{stage_name}"
            finding_id = uuid4()
            payload = FindingCreatedPayload.model_validate(
                {
                    "finding_id": str(finding_id),
                    "category": "critique",
                    "owner_role": str(owner),
                    "severity": Severity.LOW.value,
                    "source_artifact": source_artifact,
                    "repro_steps": self._repro_steps_from_critique_gate(gate_pl),
                    "required_fixes": [],
                },
                context=ctx,
            )
            self._store.append(
                FindingCreatedEvent(
                    event_type=EventType.FINDING_CREATED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata={
                        "critique_gate_fail_finding": True,
                        "stage_name": stage_name,
                    },
                    payload=payload,
                ),
            )
            rows = self._store.list_run_events(str(run_id))

    def _critique_impl_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """True when implementation critique ran and last gate is FAIL with hard-block on."""
        if not (eff.impl_hard_block_on_gate_fail and (eff.impl_llm or eff.impl_stub)):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, IMPLEMENTATION_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))

    def _critique_tw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """True when test_writer critique ran and last gate is FAIL with hard-block on."""
        if not (
            eff.tw_hard_block_on_gate_fail
            and eff.tw_enabled
            and (eff.tw_llm or eff.tw_stub)
        ):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, TEST_WRITER_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))

    def _critique_pll_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """True when planner critique ran and last gate is FAIL with hard-block on."""
        if not (
            eff.pll_hard_block_on_gate_fail
            and eff.pll_enabled
            and (eff.pll_llm or eff.pll_stub)
        ):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, PLANNER_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))

    def _critique_fw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        if not (eff.fw_hard_block_on_gate_fail and eff.fw_enabled and (eff.fw_llm or eff.fw_stub)):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, FRONTEND_WRITER_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))

    def _critique_mi_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        if not (eff.mi_hard_block_on_gate_fail and eff.mi_enabled and (eff.mi_llm or eff.mi_stub)):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, MODULE_INTEGRATOR_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))

    def _should_skip_critique_downstream_tail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """Skip integrator / agent-evaluator / self-refinement when hard-block + gate FAIL.

        Anti-deadlock and cumulative stage/gate escalations still run afterward (see
        :meth:`execute_writer_verifier_pass` tail ordering).
        """
        rows = self._store.list_run_events(str(run_id))
        return (
            self._critique_impl_hard_block_gate_fail(rows, eff)
            or self._critique_tw_hard_block_gate_fail(rows, eff)
            or self._critique_pll_hard_block_gate_fail(rows, eff)
            or self._critique_fw_hard_block_gate_fail(rows, eff)
            or self._critique_mi_hard_block_gate_fail(rows, eff)
        )

    def _emit_test_writer_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        """Optional **test_writer.critique** after implementation critique (§14 #16).

        Master switch ``HERMES_ENABLE_TEST_WRITER_CRITIQUE`` or workflow
        ``universal_critique.test_writer.enabled``. LLM / stub envs follow the same
        env-over-YAML pattern.
        """
        if not eff.tw_enabled:
            return
        tw_llm = eff.tw_llm
        stub_tw = eff.tw_stub
        emitted_tw_llm = False
        if tw_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_tw_llm = execute_test_writer_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_tw_llm and stub_tw:
            emit_stub_test_writer_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _emit_planner_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        """Optional **planner.critique** after **test_writer.critique** (§14 #16).

        Master switch ``HERMES_ENABLE_PLANNER_CRITIQUE`` or workflow
        ``universal_critique.planner.enabled``.
        """
        if not eff.pll_enabled:
            return
        pll_llm = eff.pll_llm
        stub_pll = eff.pll_stub
        emitted_pll_llm = False
        if pll_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_pll_llm = execute_planner_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_pll_llm and stub_pll:
            emit_stub_planner_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _emit_frontend_writer_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        if not eff.fw_enabled:
            return
        sg_snapshot = self._stage_graph_snapshot_for_run(run_id)
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            fw_meta = event_metadata_for_stage(sg_snapshot, "frontend_writer")
            if fw_meta:
                self._store.append(
                    StageStartedEvent(
                        event_type=EventType.STAGE_STARTED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fw_meta,
                        payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
                    ),
                )
        emitted_fw_llm = False
        if eff.fw_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_fw_llm = execute_frontend_writer_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_fw_llm and eff.fw_stub:
            emit_stub_frontend_writer_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _emit_module_integrator_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        if not eff.mi_enabled:
            return
        emitted_mi_llm = False
        if eff.mi_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_mi_llm = execute_module_integrator_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_mi_llm and eff.mi_stub:
            emit_stub_module_integrator_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _writer_stage_started_metadata(
        self,
        sg_snapshot: dict[str, Any] | None,
        stage_name: str,
        *,
        dispatch_mode: str | None = None,
    ) -> dict[str, Any] | None:
        meta = dict(event_metadata_for_stage(sg_snapshot, stage_name))
        if dispatch_mode:
            meta["dispatch_mode"] = dispatch_mode
        return meta or None

    def _run_writers_sequential(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        *,
        workspace: Path | None = None,
    ) -> tuple[int, str]:
        impl_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "implementation",
            dispatch_mode="sequential",
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=impl_meta,
                payload=StageStartedPayload(stage_name="implementation", attempt=1),
            ),
        )
        if sg_snapshot and "test_writer" in stage_graph_node_lookup(sg_snapshot):
            tw_meta = self._writer_stage_started_metadata(
                sg_snapshot,
                "test_writer",
                dispatch_mode="sequential",
            )
            if tw_meta:
                self._store.append(
                    StageStartedEvent(
                        event_type=EventType.STAGE_STARTED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=tw_meta,
                        payload=StageStartedPayload(stage_name="test_writer", attempt=1),
                    ),
                )
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            fw_meta = self._writer_stage_started_metadata(
                sg_snapshot,
                "frontend_writer",
                dispatch_mode="sequential",
            )
            if fw_meta:
                self._store.append(
                    StageStartedEvent(
                        event_type=EventType.STAGE_STARTED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fw_meta,
                        payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
                    ),
                )
                self._store.append(
                    StagePassedEvent(
                        event_type=EventType.STAGE_PASSED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        payload=StagePassedPayload(stage_name="frontend_writer", duration_ms=0),
                    ),
                )
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
        return run_writer_verifier_bundle(ws)

    def _parallel_run_implementation(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
    ) -> WriterStageResult:
        started = time.perf_counter()
        impl_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "implementation",
            dispatch_mode="parallel",
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=impl_meta,
                payload=StageStartedPayload(stage_name="implementation", attempt=1),
            ),
        )
        code, log = run_writer_verifier_bundle(ws)
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StagePassedPayload(
                    stage_name="implementation",
                    duration_ms=duration_ms,
                ),
            ),
        )
        return WriterStageResult(
            stage_name="implementation",
            verifier_exit_code=code,
            verifier_log=log,
        )

    def _parallel_run_test_writer(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
        *,
        real_enabled: bool,
        llm_body_enabled: bool,
        llm_stub_fallback_enabled: bool,
        llm_model_id: str | None,
        llm_base_url: str,
        llm_timeout_seconds: float,
    ) -> WriterStageResult:
        delay_raw = os.environ.get("HERMES_PARALLEL_WRITER_TEST_DELAY_SECONDS", "").strip()
        if delay_raw:
            try:
                time.sleep(float(delay_raw))
            except ValueError:
                pass
        started = time.perf_counter()
        tw_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "test_writer",
            dispatch_mode="parallel",
        )
        body_mode = "subprocess"
        if llm_body_enabled and os.environ.get("HERMES_USE_LLM", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            body_mode = "llm"
            if os.environ.get("HERMES_TEST_WRITER_LLM_STUB", "").strip().lower() in (
                "1",
                "true",
                "yes",
            ):
                body_mode = "stub"
        tw_meta["body_mode"] = body_mode
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=tw_meta,
                payload=StageStartedPayload(stage_name="test_writer", attempt=1),
            ),
        )
        code = 0
        log = ""
        if real_enabled:
            code, log, body_mode = run_test_writer_stage(
                ws,
                llm_body_enabled=llm_body_enabled,
                llm_stub_fallback=llm_stub_fallback_enabled,
                llm_model_id=llm_model_id,
                llm_base_url=llm_base_url,
                llm_timeout_seconds=llm_timeout_seconds,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if code == 0:
            self._store.append(
                StagePassedEvent(
                    event_type=EventType.STAGE_PASSED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata={"exit_code": 0, "body_mode": body_mode},
                    payload=StagePassedPayload(stage_name="test_writer", duration_ms=duration_ms),
                ),
            )
        else:
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata={
                        "exit_code": code,
                        "body_mode": body_mode,
                        "failure_reason": "test_writer_stage_failed",
                    },
                    payload=StageFailedPayload(
                        stage_name="test_writer",
                        reason_code="test_writer_stage_failed",
                        message=(log.strip() or "test_writer stage failed")[:500],
                    ),
                ),
            )
        return WriterStageResult(
            stage_name="test_writer",
            verifier_exit_code=code,
            verifier_log=log,
        )

    def _run_writers_parallel_dispatch(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any],
        writers_group: list[str],
        *,
        workspace: Path | None = None,
        real_test_writer_enabled: bool = False,
        test_writer_llm_body: bool = False,
        test_writer_llm_stub_fallback_enabled: bool = False,
        test_writer_llm_model_id: str | None = None,
        test_writer_llm_base_url: str = "http://localhost:11434",
        test_writer_llm_timeout_seconds: float = 120.0,
    ) -> tuple[int, str]:
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
        runners: list[tuple[str, Any]] = []
        if "implementation" in writers_group:
            runners.append(
                (
                    "implementation",
                    lambda: self._parallel_run_implementation(run_id, sg_snapshot, ws),
                ),
            )
        if "test_writer" in writers_group:
            runners.append(
                (
                    "test_writer",
                    lambda: self._parallel_run_test_writer(
                        run_id,
                        sg_snapshot,
                        ws,
                        real_enabled=real_test_writer_enabled,
                        llm_body_enabled=test_writer_llm_body,
                        llm_stub_fallback_enabled=test_writer_llm_stub_fallback_enabled,
                        llm_model_id=test_writer_llm_model_id,
                        llm_base_url=test_writer_llm_base_url,
                        llm_timeout_seconds=test_writer_llm_timeout_seconds,
                    ),
                ),
            )
        if "frontend_writer" in writers_group:
            runners.append(
                (
                    "frontend_writer",
                    lambda: self._parallel_run_frontend_writer_stub(run_id, sg_snapshot),
                ),
            )
        if not runners:
            return self._run_writers_sequential(run_id, sg_snapshot, workspace=workspace)
        results = asyncio.run(run_parallel_writer_group(runners))
        impl = next(
            (r for r in results if r.stage_name == "implementation"),
            WriterStageResult(stage_name="implementation"),
        )
        return impl.verifier_exit_code, impl.verifier_log

    def _parallel_run_frontend_writer_stub(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
    ) -> WriterStageResult:
        started = time.perf_counter()
        fw_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "frontend_writer",
            dispatch_mode="parallel",
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=fw_meta,
                payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
            ),
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StagePassedPayload(stage_name="frontend_writer", duration_ms=duration_ms),
            ),
        )
        return WriterStageResult(stage_name="frontend_writer")

    def _micro_slice_enabled_for_run(self, run_id: UUID) -> bool:
        from hermes_orchestrator.micro_slice_executor import micro_slice_effective_from_rows

        rows = self._store.list_run_events(str(run_id))
        return micro_slice_effective_from_rows(rows) is not None

    def execute_micro_slice_pass(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> list[Any]:
        from hermes_orchestrator.micro_slice_executor import execute_micro_slice_pass

        return execute_micro_slice_pass(self, run_id, workspace=workspace)

    def _security_critique_producer_for_run(
        self,
        sg_snapshot: dict[str, Any] | None,
    ) -> str:
        if sg_snapshot and "module_integrator" in stage_graph_node_lookup(sg_snapshot):
            return "module_integrator"
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            return "frontend_writer"
        return "backend_writer"

    def _emit_security_critique_optional(
        self,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        """Return True when security critique gate last verdict is FAIL (hard-block hint)."""
        block = parse_security_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not security_critique_effective(block):
            return False
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
        scan_summary = run_security_scan_summary(ws)
        producer = self._security_critique_producer_for_run(sg_snapshot)
        eff = self._effective_universal_critique_for_run(run_id)
        enforce = eff.unanimous_gate_enforce
        emitted_llm = False
        if security_critique_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                emitted_llm = execute_security_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    producer_tax_key=producer,
                    scan_summary=scan_summary,
                    base_url=str(runtime.get("base_url", "http://localhost:11434")),
                    model_id=model,
                    block=block,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                    unanimous_gate_enforce=enforce,
                )
        if not emitted_llm and block.stub:
            emit_stub_security_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
                producer_tax_key=producer,
                scan_summary=scan_summary,
                block=block,
                unanimous_gate_enforce=enforce,
            )
        rows = self._store.list_run_events(str(run_id))
        for row in reversed(rows):
            if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = row.get("payload") or {}
            if pl.get("stage_name") != "implementation.security_critique":
                continue
            return str(pl.get("verdict", "")).upper() == "FAIL"
        return False

    def _emit_performance_critique_optional(
        self,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        block = parse_performance_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not performance_critique_effective(block):
            return False
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
        scan_summary = run_security_scan_summary(ws)
        producer = self._security_critique_producer_for_run(sg_snapshot)
        eff = self._effective_universal_critique_for_run(run_id)
        enforce = eff.unanimous_gate_enforce
        emitted_llm = False
        if performance_critique_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                emitted_llm = execute_performance_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    producer_tax_key=producer,
                    scan_summary=scan_summary,
                    base_url=str(runtime.get("base_url", "http://localhost:11434")),
                    model_id=model,
                    block=block,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                    unanimous_gate_enforce=enforce,
                )
        if not emitted_llm and block.stub:
            emit_stub_performance_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
                producer_tax_key=producer,
                scan_summary=scan_summary,
                block=block,
                unanimous_gate_enforce=enforce,
            )
        rows = self._store.list_run_events(str(run_id))
        for row in reversed(rows):
            if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = row.get("payload") or {}
            if pl.get("stage_name") != "implementation.performance_critique":
                continue
            return str(pl.get("verdict", "")).upper() == "FAIL"
        return False

    def _emit_network_resilience_critique_optional(
        self,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        block = parse_network_resilience_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not network_resilience_critique_effective(block):
            return False
        producer = "backend_writer" if block.backend_only else self._security_critique_producer_for_run(
            sg_snapshot,
        )
        if block.backend_only and "backend_writer" not in self._critique_router.known_producer_keys():
            return False
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
        scan_summary = run_network_resilience_scan_summary(ws)
        eff = self._effective_universal_critique_for_run(run_id)
        enforce = eff.unanimous_gate_enforce
        emitted_llm = False
        if network_resilience_critique_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                emitted_llm = execute_network_resilience_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    scan_summary=scan_summary,
                    base_url=str(runtime.get("base_url", "http://localhost:11434")),
                    model_id=model,
                    block=block,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                    unanimous_gate_enforce=enforce,
                )
        if not emitted_llm and block.stub:
            emit_stub_network_resilience_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
                scan_summary=scan_summary,
                block=block,
                unanimous_gate_enforce=enforce,
            )
        rows = self._store.list_run_events(str(run_id))
        for row in reversed(rows):
            if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = row.get("payload") or {}
            if pl.get("stage_name") != "implementation.network_resilience_critique":
                continue
            return str(pl.get("verdict", "")).upper() == "FAIL"
        return False

    def _emit_refactor_stage_optional(
        self,
        run_id: UUID,
        *,
        workflow_profile: str | None,
    ) -> bool:
        block = parse_refactor_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not refactor_stage_effective(block):
            return False
        eff = self._effective_universal_critique_for_run(run_id)
        force_fail = os.environ.get("HERMES_REFACTOR_FORCE_FAIL", "").lower() in (
            "1",
            "true",
            "yes",
        )
        return emit_refactor_stage_and_critique(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            block=block,
            unanimous_gate_enforce=eff.unanimous_gate_enforce,
            force_fail=force_fail,
        )

    def execute_writer_verifier_pass(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> None:
        """Append implementation stage + optional pytest finding on failure.

        When ``micro_slice_effective.enabled`` on ``run.created``, runs the per-slice
        chain instead of the default writer/verifier pass.

        After the verifier, optional **implementation.critique** panel: try LLM when
        workflow ``universal_critique.implementation.llm`` or ``HERMES_IMPLEMENTATION_CRITIQUE_LLM``
        (env overrides YAML when non-empty); same for stub critics. Optionally
        **test_writer.critique** / **planner.critique** via workflow ``universal_critique`` or
        the existing ``HERMES_*`` switches.
        Optional **planner.critique** after that via env or workflow
        ``universal_critique.planner`` (same env-over-YAML pattern). Optional ``stage.failed``
        for gate FAIL mirrors implementation / test_writer / planner knobs (env overrides
        workflow when set). Optional **finding.created** (LOW) on last critique gate FAIL
        is off by default; enable via ``emit_finding_on_gate_fail`` or ``HERMES_*``
        env (see ``_maybe_emit_critique_gate_fail_findings``).
        Optional **hard_block_on_gate_fail** (per stage; env
        ``HERMES_*_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL``) skips integrator gate,
        agent-evaluator stage marker, and self-refinement marker when
        that stage's last critique gate is FAIL; anti-deadlock / cumulative escalations still run.
        When **hard_block_on_gate_fail** and the last gate for that stage is FAIL, later
        optional critique panels are **not** run (implementation FAIL skips test_writer and
        planner; test_writer FAIL skips planner only).
        """
        if self._micro_slice_enabled_for_run(run_id):
            self.execute_micro_slice_pass(run_id, workspace=workspace)
            return
        self.run_optional_scraper_fetch_stage(run_id)
        writer = self._registry.resolve("backend_writer")
        sg_snapshot = self._stage_graph_snapshot_for_run(run_id)
        wf_prof = workflow_profile_from_run_created_rows(
            self._store.list_run_events(str(run_id)),
        )
        use_parallel = parallel_writers_enabled(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        real_test_writer = test_writer_stage_enabled(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        tw_llm_body = test_writer_llm_body_enabled(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        tw_llm_stub_fallback = test_writer_llm_stub_fallback(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        base_cfg = self._base_cfg()
        runtime_cfg = base_cfg.get("runtime") or {}
        writers_group = (
            parallel_group_members(sg_snapshot, "writers")
            if sg_snapshot and use_parallel
            else []
        )
        if writers_group:
            code, log = self._run_writers_parallel_dispatch(
                run_id,
                sg_snapshot,
                writers_group,
                workspace=workspace,
                real_test_writer_enabled=real_test_writer,
                test_writer_llm_body=tw_llm_body,
                test_writer_llm_stub_fallback_enabled=tw_llm_stub_fallback,
                test_writer_llm_model_id=self._selected_model_for_run(run_id),
                test_writer_llm_base_url=str(runtime_cfg.get("base_url", "http://localhost:11434")),
                test_writer_llm_timeout_seconds=float(
                    runtime_cfg.get("request_timeout_seconds", 120),
                ),
            )
        else:
            code, log = self._run_writers_sequential(
                run_id,
                sg_snapshot,
                workspace=workspace,
            )
        if code != 0:
            ctx = self._strictness_context(run_id)
            hinted = suggest_owner_role_from_verifier_log(log, self._registry)
            owner = hinted or writer
            scan_meta: dict[str, Any] = {}
            if security_scan_metadata_on_verify_enabled(
                self._repo_root,
                wf_prof,
                config_materializer=self._config_materializer,
            ):
                ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
                scode, slog, ruff_ec, bandit_ec, mypy_ec, perf_ec, n1_ec, semgrep_ec = (
                    run_security_scan(ws)
                )
                scan_meta = {
                    "security_scan_exit": scode,
                    "security_scan_ruff_exit": ruff_ec,
                    "security_scan_bandit_exit": bandit_ec,
                    "security_scan_mypy_exit": mypy_ec,
                    "security_scan_ruff_perf_exit": perf_ec,
                    "security_scan_n_plus_one_exit": n1_ec,
                    "security_scan_snippet": "\n".join(slog.splitlines()[:20]),
                    **security_scan_tool_summary(
                        ruff_ec,
                        bandit_ec,
                        mypy_ec,
                        perf_ec,
                        n1_ec,
                        semgrep_ec,
                    ),
                }
            payload = FindingCreatedPayload.model_validate(
                {
                    "finding_id": str(uuid4()),
                    "category": "verify",
                    "owner_role": str(owner),
                    "severity": Severity.LOW.value,
                    "source_artifact": "writer_verifier_bundle",
                    "repro_steps": log.splitlines()[:40],
                    "required_fixes": [],
                },
                context=ctx,
            )
            self._store.append(
                FindingCreatedEvent(
                    event_type=EventType.FINDING_CREATED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata=scan_meta,
                    payload=payload,
                ),
            )
            self._maybe_escalate_verifier_failure_checkpoint(run_id)

        log_snippet = "\n".join(log.splitlines()[:60])
        eff = self._effective_universal_critique_for_run(run_id)
        security_gate_fail = self._emit_security_critique_optional(
            run_id,
            workspace=workspace,
            workflow_profile=wf_prof,
            sg_snapshot=sg_snapshot,
        )
        performance_gate_fail = False
        if not security_gate_fail:
            performance_gate_fail = self._emit_performance_critique_optional(
                run_id,
                workspace=workspace,
                workflow_profile=wf_prof,
                sg_snapshot=sg_snapshot,
            )
        network_gate_fail = False
        if not security_gate_fail and not performance_gate_fail:
            network_gate_fail = self._emit_network_resilience_critique_optional(
                run_id,
                workspace=workspace,
                workflow_profile=wf_prof,
                sg_snapshot=sg_snapshot,
            )
        refactor_gate_fail = False
        if not security_gate_fail and not performance_gate_fail and not network_gate_fail:
            refactor_gate_fail = self._emit_refactor_stage_optional(
                run_id,
                workflow_profile=wf_prof,
            )
        impl_llm = eff.impl_llm
        stub_impl = eff.impl_stub
        emitted_impl_llm = False
        if impl_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_impl_llm = execute_implementation_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if (
            not security_gate_fail
            and not performance_gate_fail
            and not network_gate_fail
            and not refactor_gate_fail
            and not emitted_impl_llm
            and stub_impl
        ):
            emit_stub_implementation_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )
        self._maybe_emit_stage_failed_for_implementation_critique_gate_fail(run_id, eff)
        if security_gate_fail or performance_gate_fail or network_gate_fail or refactor_gate_fail:
            return
        rows_post_impl = self._store.list_run_events(str(run_id))
        if not self._critique_impl_hard_block_gate_fail(rows_post_impl, eff):
            self._emit_test_writer_critique_optional(
                run_id,
                verifier_exit_code=code,
                log_snippet=log_snippet,
                eff=eff,
            )
            self._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(run_id, eff)
            rows_post_tw = self._store.list_run_events(str(run_id))
            if not self._critique_tw_hard_block_gate_fail(rows_post_tw, eff):
                self._emit_planner_critique_optional(
                    run_id,
                    verifier_exit_code=code,
                    log_snippet=log_snippet,
                    eff=eff,
                )
                self._maybe_emit_stage_failed_for_planner_critique_gate_fail(run_id, eff)
                rows_post_pll = self._store.list_run_events(str(run_id))
                if not self._critique_pll_hard_block_gate_fail(rows_post_pll, eff):
                    self._emit_frontend_writer_critique_optional(
                        run_id,
                        verifier_exit_code=code,
                        log_snippet=log_snippet,
                        eff=eff,
                    )
                    self._maybe_emit_stage_failed_for_frontend_writer_critique_gate_fail(
                        run_id,
                        eff,
                    )
                    rows_post_fw = self._store.list_run_events(str(run_id))
                    if not self._critique_fw_hard_block_gate_fail(rows_post_fw, eff):
                        self._emit_module_integrator_critique_optional(
                            run_id,
                            verifier_exit_code=code,
                            log_snippet=log_snippet,
                            eff=eff,
                        )
                        self._maybe_emit_stage_failed_for_module_integrator_critique_gate_fail(
                            run_id,
                            eff,
                        )
        self._maybe_emit_critique_gate_fail_findings(run_id, eff)
        self._maybe_auto_escalate(run_id)
        self._maybe_notice_escalate_findings(run_id)
        skip_critique_downstream = self._should_skip_critique_downstream_tail(run_id, eff)
        if not skip_critique_downstream:
            self._emit_bundle_integrator_gate(run_id)
            self._maybe_emit_integration_adapter_writer_stage(run_id)
            self._maybe_emit_agent_evaluator_stage(run_id)
        self._maybe_emit_anti_deadlock_escalation(run_id)
        self._maybe_escalate_after_cumulative_stage_failures(run_id)
        self._maybe_escalate_after_cumulative_gate_failures(run_id)
        self._maybe_escalate_after_cumulative_high_severity_findings(run_id)
        if not skip_critique_downstream:
            self._maybe_emit_self_refinement_stage_marker(run_id)
            self._maybe_continue_ungated_self_refinement_loop(run_id)

    def dispatch_or_run_verify(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> str:
        """Enqueue verify when dispatch enabled; otherwise run synchronously."""
        if not run_dispatch_enabled():
            self.execute_writer_verifier_pass(run_id, workspace=workspace)
            return "sync"
        payload: dict[str, Any] = {}
        if workspace is not None:
            payload["workspace"] = str(workspace)
        get_run_queue().enqueue(
            RunDispatchTask(run_id=str(run_id), step="verify", payload=payload),
        )
        return "queued"

    def process_verify_dispatch_task(self, task: RunDispatchTask) -> None:
        ws_raw = task_payload_workspace(task.payload)
        ws = Path(ws_raw) if ws_raw else None
        self.execute_writer_verifier_pass(UUID(task.run_id), workspace=ws)

    def _workflow_suppresses_automatic_escalation(self, run_id: UUID) -> bool:
        rows = self._store.list_run_events(str(run_id))
        wf_prof = workflow_profile_from_run_created_rows(rows)
        block = parse_escalation_workflow_block(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        return block.suppress_automatic_escalation

    def _maybe_emit_anti_deadlock_escalation(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        enabled, stall_minutes, min_prog = load_anti_deadlock_settings(self._repo_root)
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "anti_deadlock_insufficient_progress"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        if not should_emit_anti_deadlock_escalation(
            rows,
            now=datetime.now(timezone.utc),
            enabled=enabled,
            stall_minutes=stall_minutes,
            min_progress_events=min_prog,
        ):
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="anti_deadlock_insufficient_progress",
            notes=f"stall_minutes={stall_minutes} min_progress_events={min_prog}",
        )

    def _maybe_escalate_after_cumulative_stage_failures(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_escalate_after_cumulative_stage_failures(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_stage_failures"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        n_failed = sum(1 for r in rows if r["event_type"] == EventType.STAGE_FAILED.value)
        if n_failed < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_stage_failures",
            notes=f"threshold={threshold} cumulative_stage_failed={n_failed}",
        )

    def _maybe_escalate_after_cumulative_gate_failures(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_escalate_after_cumulative_gate_failures(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_gate_failures"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        n_gate_fail = 0
        for r in rows:
            if r["event_type"] != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("verdict") == Verdict.FAIL.value:
                n_gate_fail += 1
        if n_gate_fail < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_gate_failures",
            notes=f"threshold={threshold} cumulative_gate_failed={n_gate_fail}",
        )

    def _maybe_escalate_after_cumulative_high_severity_findings(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_escalate_after_cumulative_high_severity_findings(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_high_severity_findings"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        high_n = 0
        for r in rows:
            if r["event_type"] != EventType.FINDING_CREATED.value:
                continue
            sev = (r.get("payload") or {}).get("severity")
            if sev in ("HIGH", "BLOCKER"):
                high_n += 1
        if high_n < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_high_severity_findings",
            notes=(
                f"threshold={threshold} "
                f"cumulative_high_severity_findings={high_n}"
            ),
        )

    def _maybe_auto_escalate(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_auto_escalate_after_cumulative_findings(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(r["event_type"] == EventType.RUN_ESCALATED.value for r in rows):
            return
        n_findings = sum(1 for r in rows if r["event_type"] == EventType.FINDING_CREATED.value)
        if n_findings < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_findings_threshold",
            notes=f"threshold={threshold} cumulative_findings={n_findings}",
        )

    def _maybe_notice_escalate_findings(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_notice_escalate_at_cumulative_findings(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_findings_notice"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        n_findings = sum(1 for r in rows if r["event_type"] == EventType.FINDING_CREATED.value)
        if n_findings < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_findings_notice",
            notes=f"notice_threshold={threshold} cumulative_findings={n_findings}",
        )

    def _maybe_escalate_verifier_failure_checkpoint(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        if not load_escalate_on_first_verifier_failure(self._repo_root):
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "verifier_failure_checkpoint"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="verifier_failure_checkpoint",
            notes="escalate_on_first_verifier_failure policy",
        )

    def _maybe_emit_integration_adapter_writer_stage(self, run_id: UUID) -> None:
        rows = self._store.list_run_events(str(run_id))
        wf = workflow_profile_from_run_created_rows(rows)
        mat = self._config_materializer
        if not integration_adapter_writer_stage_would_emit(
            self._repo_root,
            wf,
            config_materializer=mat,
        ):
            return
        block = parse_integration_adapter_writer_workflow_block(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if block.stub_only:
            emit_stub_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
            )
        else:
            emit_live_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
                repo_root=self._repo_root,
            )

    def _maybe_emit_agent_evaluator_stage(self, run_id: UUID) -> None:
        env_raw = os.environ.get("HERMES_AGENT_EVALUATOR", "").strip().lower()
        if env_raw in ("0", "false", "no"):
            return
        env_on = env_raw in ("1", "true", "yes")
        wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
        block = parse_agent_evaluator_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if not env_on and not block.enabled:
            return
        ae_meta: dict[str, Any] = {}
        ac_cfg = block.auto_create_persona
        if ac_cfg.enabled:
            if _agent_evaluator_auto_create_env_disabled():
                ae_meta["auto_create_persona"] = {
                    "auto_create_persona_requested": True,
                    "auto_create_persona_applied": False,
                    "reason": "env_kill_switch",
                }
            else:
                ae_meta["auto_create_persona"] = try_auto_create_persona_if_missing(
                    self._repo_root,
                    self._store,
                    persona_id=block.persona_id,
                    run_id=run_id,
                    cfg=ac_cfg,
                    config_materializer=self._config_materializer,
                )
        if block.auto_promote_probation:
            if _agent_evaluator_auto_promote_env_disabled():
                ae_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                }
            else:
                ae_meta["auto_promote_probation"] = try_auto_promote_probation_persona(
                    self._repo_root,
                    self._store,
                    persona_id=block.persona_id,
                    run_id=run_id,
                    config_materializer=self._config_materializer,
                )
        from hermes_config.persist import load_persona_shelf
        from hermes_orchestrator.read_models import persona_assignment_from_run_created_metadata

        rows = self._store.list_run_events(str(run_id))
        pa_for_eval: dict[str, Any] | None = None
        for row in rows:
            if row.get("event_type") != EventType.RUN_CREATED.value:
                continue
            meta_row = row.get("metadata")
            if isinstance(meta_row, dict):
                pa_for_eval = persona_assignment_from_run_created_metadata(meta_row)
            break
        shelf = load_persona_shelf(self._repo_root, materializer=self._config_materializer)
        rules_eval = AgentEvaluator().evaluate(
            block.persona_id,
            persona_assignment=pa_for_eval,
            shelf=shelf,
        )
        ae_meta["evaluation"] = rules_eval
        evaluation_branch: Literal["rules", "rules_with_llm_policy"] = "rules"
        production_scoring_mode = "rules"
        if agent_evaluator_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            llm_result = None
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                llm_result = execute_agent_evaluator_policy_llm(
                    self._store,
                    self._registry,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    rules_eval=rules_eval,
                    persona_id=block.persona_id,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
            if llm_result is None and agent_evaluator_llm_stub_env_enabled():
                llm_result = {
                    "status": str(rules_eval.get("status", "ok")),
                    "gaps": (
                        list(rules_eval.get("gaps"))
                        if isinstance(rules_eval.get("gaps"), list)
                        else []
                    ),
                    "summary": "stub agent-evaluator policy review",
                    "production_scoring_mode": "stub",
                }
            elif llm_result is None and agent_evaluator_production_llm_fallback_enabled(
                block,
            ):
                llm_result = agent_evaluator_rules_derived_llm_evaluation(rules_eval)
            if llm_result is not None:
                evaluation_branch = "rules_with_llm_policy"
                llm_eval_meta: dict[str, Any] = {
                    "status": llm_result.get("status"),
                    "gaps": llm_result.get("gaps"),
                    "summary": llm_result.get("summary"),
                }
                mode_raw = llm_result.get("production_scoring_mode")
                if isinstance(mode_raw, str) and mode_raw.strip():
                    production_scoring_mode = mode_raw.strip()
                else:
                    production_scoring_mode = "llm"
                rules_score = rules_eval.get("score")
                if isinstance(rules_score, (int, float)) and not isinstance(
                    rules_score,
                    bool,
                ):
                    score_f = float(rules_score)
                    llm_eval_meta["policy_score"] = score_f
                    llm_eval_meta["policy_score_band"] = agent_evaluator_score_band(
                        score_f,
                    )
                ae_meta["llm_evaluation"] = llm_eval_meta
        ae_meta["evaluation_branch"] = evaluation_branch
        ae_meta["production_scoring_mode"] = production_scoring_mode
        meta: dict[str, Any] = {}
        if ae_meta:
            meta["agent_evaluator"] = ae_meta
        AgentEvaluator().emit_evaluation_stage_started(
            self._store,
            run_id=run_id,
            persona_id=block.persona_id,
            metadata=meta or None,
        )
        if persona_coverage_critique_effective(block):
            eff = self._effective_universal_critique_for_run(run_id)
            emitted = False
            if persona_coverage_critique_llm_branch_effective(block):
                model = self._selected_model_for_run(run_id)
                if model:
                    base = self._base_cfg()
                    runtime = base.get("runtime") or {}
                    base_url = str(runtime.get("base_url", "http://localhost:11434"))
                    emitted = execute_persona_coverage_critique_llm(
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                        rules_eval=rules_eval,
                        base_url=base_url,
                        model_id=model,
                        timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                        unanimous_gate_enforce=eff.unanimous_gate_enforce,
                    )
            if not emitted and block.persona_coverage_critique.stub:
                emit_stub_persona_coverage_critique_panel(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    rules_eval=rules_eval,
                    unanimous_gate_enforce=eff.unanimous_gate_enforce,
                )

    def _maybe_continue_ungated_self_refinement_loop(self, run_id: UUID) -> None:
        """Auto-continue ungated Phase D iterations when the last signal requests it (§14 #17)."""
        for _ in range(16):
            rows = self._store.list_run_events(str(run_id))
            if _self_refinement_max_iterations_exceeded(rows):
                break
            if not _last_self_refinement_loop_should_continue(rows):
                break
            self._maybe_emit_self_refinement_stage_marker(run_id)

    def _maybe_emit_self_refinement_stage_marker(self, run_id: UUID) -> None:
        rows = self._store.list_run_events(str(run_id))
        if _self_refinement_max_iterations_exceeded(rows):
            return

        wf_prof = workflow_profile_from_run_created_rows(rows)
        wf_sr = parse_self_refinement_workflow_block(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )

        mat = self._config_materializer
        if mat is not None and getattr(mat, "use_db", False):
            from hermes_extensions.self_refinement import self_refinement_policy_from_mapping

            try:
                pol = self_refinement_policy_from_mapping(
                    mat.get_self_refinement_policy(),
                )
            except KeyError:
                pol = SelfRefinementPolicy(version=1, enabled=False, description="")
        else:
            path = self._repo_root / "configs" / "self_refinement" / "policy.yaml"
            if path.is_file():
                pol = load_self_refinement_policy(path)
            else:
                pol = SelfRefinementPolicy(version=1, enabled=False, description="")

        if not pol.enabled and not wf_sr.enabled:
            return

        if _self_refinement_stage_marker_env_disabled():
            return

        version = pol.version
        description = pol.description
        if wf_sr.version is not None:
            version = wf_sr.version
        if wf_sr.description is not None:
            description = wf_sr.description

        max_iterations = pol.max_iterations
        if wf_sr.max_iterations is not None:
            max_iterations = wf_sr.max_iterations
        auto_promote = bool(pol.auto_promote_probation or wf_sr.auto_promote_probation)
        llm_critique_enabled = bool(
            wf_sr.llm_critique_enabled or pol.llm_critique_enabled,
        )
        ungated_loop = self_refinement_ungated_loop_effective(wf_sr)

        marker_count = _self_refinement_marker_count(rows)
        attempt = marker_count + 1
        if attempt > max_iterations:
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    payload=StageFailedPayload(
                        stage_name=_SELF_REFINEMENT_POLICY_STAGE,
                        reason_code=_SELF_REFINEMENT_MAX_ITER_REASON,
                        message=(
                            f"self_refinement:policy exceeded max_iterations={max_iterations}"
                        ),
                    ),
                ),
            )
            return

        bounded = (description or "")[:2000]
        from hermes_config.persist import load_persona_shelf
        from hermes_orchestrator.read_models import persona_assignment_from_run_created_metadata

        pa_for_eval: dict[str, Any] | None = None
        for row in rows:
            if row.get("event_type") != EventType.RUN_CREATED.value:
                continue
            meta_row = row.get("metadata")
            if isinstance(meta_row, dict):
                pa_for_eval = persona_assignment_from_run_created_metadata(meta_row)
            break
        sr_eval = SelfRefinementEvaluator().evaluate(
            persona_assignment=pa_for_eval,
            shelf=load_persona_shelf(self._repo_root, materializer=self._config_materializer),
        )
        eval_status_raw = sr_eval.get("status")
        eval_status = eval_status_raw if isinstance(eval_status_raw, str) else None
        gate_decision = "proceed" if (eval_status == "ok" or ungated_loop) else "hold"
        loops_remaining = max(0, int(max_iterations) - int(attempt))
        iteration_progress_ratio = min(1.0, float(attempt) / float(max_iterations))
        should_continue = loops_remaining > 0 and (
            gate_decision == "hold" or ungated_loop
        )
        signal = "phase_d_kickoff" if attempt == 1 else "phase_d_iteration"
        orchestration_branch: Literal["rules", "rules_with_llm_critique"] = "rules"
        llm_critique_attempted = False
        llm_critique_verdict: Verdict | None = None
        llm_gate_decision: Literal["proceed", "hold"] | None = None
        llm_critique_summary: str | None = None
        prior_gate_verdict: str | None = None
        for row in rows:
            if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl_row = row.get("payload")
            if not isinstance(pl_row, dict):
                continue
            if pl_row.get("stage_name") == "self_refinement.critique":
                verdict_raw = pl_row.get("verdict")
                prior_gate_verdict = (
                    str(verdict_raw).strip().upper() if verdict_raw is not None else None
                )
        eval_gaps_raw = sr_eval.get("gaps")
        eval_gaps = (
            [str(g) for g in eval_gaps_raw]
            if isinstance(eval_gaps_raw, list)
            else []
        )
        if (
            llm_critique_enabled
            and gate_decision == "hold"
            and self_refinement_llm_critique_effective_for_run(
                self._repo_root,
                wf_prof,
                wf_sr,
                config_materializer=self._config_materializer,
            )
        ):
            base = self._base_cfg()
            runtime = base.get("runtime") or {}
            base_url = str(runtime.get("base_url", "http://localhost:11434"))
            model = self._selected_model_for_run(run_id)
            if model:
                llm_result = execute_self_refinement_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    evaluation_status=eval_status,
                    gaps=eval_gaps,
                    description=bounded,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
                if llm_result is not None:
                    orchestration_branch = "rules_with_llm_critique"
                    llm_critique_attempted = True
                    llm_critique_verdict = Verdict(str(llm_result.get("verdict", "FAIL")))
                    gate_raw = str(llm_result.get("gate_decision", "hold")).strip().lower()
                    llm_gate_decision = (
                        "proceed" if gate_raw == "proceed" else "hold"
                    )
                    summary_raw = llm_result.get("summary")
                    if isinstance(summary_raw, str) and summary_raw.strip():
                        llm_critique_summary = summary_raw.strip()[:500]
                elif os.environ.get(
                    "HERMES_SELF_REFINEMENT_CRITIQUE_STUB",
                    "",
                ).strip().lower() in ("1", "true", "yes"):
                    emit_stub_self_refinement_critique_panel(
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                    )
        sr_meta: dict[str, Any] = {
            "version": version,
            "description": bounded,
            "evaluation": sr_eval,
            "max_iterations": max_iterations,
            "attempt": attempt,
            "signal": signal,
            "gate_decision": gate_decision,
            "loops_remaining": loops_remaining,
            "iteration_progress_ratio": iteration_progress_ratio,
            "should_continue": should_continue,
            "orchestration_branch": orchestration_branch,
            "llm_critique": {
                "enabled": llm_critique_enabled,
                "attempted": llm_critique_attempted,
                "orchestration_branch": orchestration_branch,
                "verdict": (
                    llm_critique_verdict.value if llm_critique_verdict is not None else None
                ),
                "gate_decision": llm_gate_decision,
                "summary": llm_critique_summary,
            },
            "ungated_loop": ungated_loop,
            "ungated_iterative_depth": ungated_loop and attempt > 1,
            "prior_gate_verdict": prior_gate_verdict,
        }
        if auto_promote:
            persona_id = (
                _persona_id_from_assignment_slot(
                    pa_for_eval.get("business_area") if pa_for_eval else None,
                )
                or ""
            )
            if _self_refinement_auto_promote_env_disabled():
                sr_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                }
            elif persona_id:
                sr_meta["auto_promote_probation"] = try_auto_promote_probation_persona(
                    self._repo_root,
                    self._store,
                    persona_id=persona_id,
                    run_id=run_id,
                    config_materializer=self._config_materializer,
                    actor="system:self_refinement",
                )
            else:
                sr_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "no_business_area_persona_on_run",
                }
        self._store.append(
            SelfRefinementLoopSignalledEvent(
                event_type=EventType.SELF_REFINEMENT_LOOP_SIGNALLED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=SelfRefinementLoopSignalledPayload(
                    attempt=attempt,
                    max_iterations=max_iterations,
                    signal=signal,
                    gate_decision=gate_decision,  # explicit per-iteration phase D gate outcome
                    evaluation_status=eval_status,
                    loops_remaining=loops_remaining,
                    iteration_progress_ratio=iteration_progress_ratio,
                    should_continue=should_continue,
                    orchestration_branch=orchestration_branch,
                    llm_critique_enabled=llm_critique_enabled,
                    llm_critique_attempted=llm_critique_attempted,
                    llm_critique_verdict=llm_critique_verdict,
                    llm_gate_decision=llm_gate_decision,
                ),
            ),
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"self_refinement": sr_meta},
                payload=StageStartedPayload(
                    stage_name=_SELF_REFINEMENT_POLICY_STAGE,
                    attempt=attempt,
                ),
            ),
        )

    def _emit_bundle_integrator_gate(self, run_id: UUID) -> None:
        env = os.environ.get("HERMES_EMIT_INTEGRATOR_GATE", "").strip().lower()
        if env in ("0", "false", "no"):
            return
        from hermes_extensions.phase2 import ModuleIntegrator

        rows = self._store.list_run_events(str(run_id))
        wf = workflow_profile_from_run_created_rows(rows)
        mat = self._config_materializer
        yaml_on = load_integrator_gate_emit_enabled(
            self._repo_root,
            config_materializer=mat,
        )
        wf_on = integrator_gate_workflow_enabled(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if env not in ("1", "true", "yes") and not yaml_on and not wf_on:
            return
        if mat is None or not getattr(mat, "use_db", False):
            path = self._repo_root / "configs" / "integrator" / "thresholds.yaml"
            if not path.is_file():
                return
        eff_min = effective_integrator_min_score_to_pass(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        mi = ModuleIntegrator(min_score_to_pass=eff_min)
        bundle_id = select_bundle_id_for_workflow(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        bundle_tags = load_bundle_tags_for_bundle_id(
            self._repo_root,
            bundle_id,
            config_materializer=self._config_materializer,
        )
        bundle_title = load_bundle_title_for_bundle_id(
            self._repo_root,
            bundle_id,
            config_materializer=self._config_materializer,
        )
        project_override = parse_integrator_gate_project_tags(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if project_override is not None:
            project_tags = project_override
        elif bundle_tags:
            project_tags = list(bundle_tags)
        else:
            project_tags = [bundle_id]
        profile: dict[str, Any]
        if bundle_tags:
            profile = {"tags": project_tags, "bundle_tags": bundle_tags}
        else:
            profile = {"tags": project_tags}
        score = mi.score_fit(bundle_id, profile)
        ok = mi.passes_gate(bundle_id, profile)
        pset = {str(t).lower() for t in project_tags if str(t).strip()}
        bset = {str(t).lower() for t in bundle_tags if str(t).strip()}
        matched_tags = sorted(pset & bset) if bundle_tags else []
        ranking = rank_bundle_compatibility_candidates(
            self._repo_root,
            list(project_tags),
            integrator=mi,
            config_materializer=self._config_materializer,
            limit=10,
        )
        selected_bundle_rank: int | None = None
        for idx, row in enumerate(ranking):
            if row.get("bundle_id") == bundle_id:
                selected_bundle_rank = idx
                break
        gate_meta: dict[str, Any] = {
            "integrator_gate": True,
            "bundle_id": bundle_id,
            "bundle_title": bundle_title,
            "integrator_score": score,
            "min_score_to_pass": mi.min_score_to_pass,
            "integrator_project_tags": list(project_tags),
            "integrator_bundle_tags": list(bundle_tags),
            "integrator_matched_tags": matched_tags,
            "bundle_compatibility_ranking": ranking,
            "bundle_compatibility_ranking_count": len(ranking),
        }
        if selected_bundle_rank is not None:
            gate_meta["selected_bundle_rank"] = selected_bundle_rank
        if ok:
            gate_payload = GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            )
        else:
            gate_payload = GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.FAIL,
                unanimous_pass_required=False,
                failure_reason_code="integrator_below_threshold",
            )
        self._store.append(
            GateDecisionEmittedEvent(
                event_type=EventType.GATE_DECISION_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=gate_meta,
                payload=gate_payload,
            ),
        )


def default_paths(repo_root: Path | None = None) -> tuple[Path, Path]:
    root = repo_root or Path(__file__).resolve().parents[2]
    return (
        root / "configs" / "model-routing.yaml",
        root / "configs" / "workflows" / "default.yaml",
    )


def make_dev_orchestrator(
    repo_root: Path | None = None,
) -> tuple[RunOrchestrator, InMemoryEventStore]:
    root = repo_root or Path(__file__).resolve().parents[2]
    base, _ = default_paths(root)
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    mem = InMemoryEventStore()
    orch = RunOrchestrator(mem, reg, repo_root=root, base_config_path=base)
    return orch, mem

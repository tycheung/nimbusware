from __future__ import annotations

from typing import Any

from orchestrator._pipeline._helpers import (
    UUID,
    EventType,
    Path,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    datetime,
    timezone,
    uuid4,
)
from orchestrator._pipeline.protocol_hosts import MicroSliceHost
from orchestrator.slice.gate import SliceGateChainResult


class MicroSliceMixin:
    def record_micro_slice_plan(
        self: MicroSliceHost,
        run_id: UUID,
        plan: dict[str, Any] | Any,
    ) -> None:
        from orchestrator.slice.micro_slice import SlicePlan, parse_slice_plan

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
        self: MicroSliceHost,
        run_id: UUID,
        plan: dict[str, Any] | Any,
        *,
        verify_ok: bool,
        critique_verdicts: list[str] | None = None,
        tests_passed: bool | None = None,
        e2e_passed: bool | None = None,
        e2e_detail: str = "",
        diff_unified: str = "",
        test_output: str = "",
        test_detail: str = "",
    ) -> SliceGateChainResult:
        from orchestrator.collab.binding_resolver import participant_memory_policy
        from orchestrator.slice.context_packet import build_slice_context_packet
        from orchestrator.slice.gate import run_slice_gate_chain
        from orchestrator.slice.handoff import (
            build_slice_handoff_summary,
            handoff_markdown_capped,
            latest_handoff_from_events,
        )
        from orchestrator.slice.micro_slice import SlicePlan, parse_slice_plan
        from orchestrator.workflow.memory import (
            actor_user_id_from_run_metadata,
            memory_settings_from_run_metadata,
            pinned_generation_for_scope,
            query_digest,
            retrieve_memory_excerpt_for_slice,
            run_memory_retrieval_enabled,
        )

        p: SlicePlan = plan if isinstance(plan, SlicePlan) else parse_slice_plan(plan)
        rows = self._store.list_run_events(str(run_id))
        from orchestrator.enforcement_pipeline import (
            active_enforcement_profile,
            run_milestone_enforcement,
        )
        from orchestrator.profiles.autopilot_profiles import autopilot_profile_from_rows
        from orchestrator.slice.cycle_integration import resolution_for_gate

        profile = autopilot_profile_from_rows(rows)
        enforcement = active_enforcement_profile(rows)
        verify_ok_for_gate = verify_ok
        enforcement_meta: dict[str, Any] = {}

        def _resolution_cb(findings: list[dict[str, Any]]) -> Any:
            return resolution_for_gate(self._store, run_id, rows, findings)

        if enforcement is not None:
            from maker.workspace.workspace import resolve_run_workspace

            ws = resolve_run_workspace(rows)
            milestone = run_milestone_enforcement(
                ws,
                enforcement,
                scope_paths=list(p.target_paths),
            )
            if milestone is not None:
                enforcement_meta["enforcement_steps"] = milestone.get(
                    "enforcement_steps", milestone
                )
                if not milestone.get("enforcement_passed", True):
                    verify_ok_for_gate = False

        gate = run_slice_gate_chain(
            p,
            verify_ok=verify_ok_for_gate,
            critique_verdicts=critique_verdicts,
            tests_passed=tests_passed,
            test_detail=test_detail or test_output[:500],
            e2e_passed=e2e_passed,
            e2e_detail=e2e_detail,
            autopilot_level=profile.level,
            enforcement_profile=enforcement,
            resolution_callback=_resolution_cb,
        )
        run_meta = self._run_created_metadata(run_id)
        memory_excerpt = ""
        memory_hits: list[Any] = []
        memory_scope = ""
        memory_settings = memory_settings_from_run_metadata(run_meta)
        actor_id = actor_user_id_from_run_metadata(run_meta)
        retrieval_policy = participant_memory_policy(run_meta, actor_id)
        if run_memory_retrieval_enabled(run_meta) and self._memory_chunk_store is not None:
            memory_excerpt, memory_hits, memory_scope = retrieve_memory_excerpt_for_slice(
                self._memory_chunk_store,
                p,
                repo_root=self._repo_root,
                settings=memory_settings,
                actor_user_id=actor_id,
                retrieval_policy=retrieval_policy,
            )
        prior_handoff = latest_handoff_from_events(
            self._store.list_run_events(str(run_id)),
        )
        diff_stat = (
            f"{diff_unified.count(chr(10))} diff lines"
            if diff_unified.strip()
            else "no diff captured"
        )
        handoff = build_slice_handoff_summary(
            p,
            prior=prior_handoff,
            gate=gate,
            paths_touched=tuple(p.target_paths),
            diff_stat=diff_stat,
            repo_root=self._repo_root,
        )
        handoff_md = handoff_markdown_capped(handoff)
        packet = build_slice_context_packet(
            p,
            diff_unified=diff_unified,
            test_output=test_output,
            gate=gate,
            memory_excerpt=memory_excerpt,
            repo_root=self._repo_root,
            handoff_summary=handoff_md,
        )
        now = datetime.now(timezone.utc)
        meta = {
            **gate.to_metadata(),
            **enforcement_meta,
            "slice_context_packet": packet.model_dump(mode="json"),
            "slice_handoff": handoff.model_dump(mode="json"),
        }
        if memory_hits:
            from orchestrator.workflow.memory import memory_chunk_ids_from_hits

            meta["memory_chunk_ids"] = memory_chunk_ids_from_hits(memory_hits)
            from memory.index.audit import append_memory_retrieval_emitted_event

            chunk_store = self._memory_chunk_store
            assert chunk_store is not None
            append_memory_retrieval_emitted_event(
                self._store,
                run_id=run_id,
                stage_name="slice.gate",
                slice_id=p.slice_id,
                query_digest=query_digest(
                    " ".join(
                        [p.slice_id, p.rationale, *p.target_paths],
                    ).strip()
                    or "failure fix gate security",
                ),
                hits=memory_hits,
                excerpt=memory_excerpt,
                retrieval_k=memory_settings.retrieval_k,
                repo_scope_hash=memory_scope,
                generation_id=pinned_generation_for_scope(
                    chunk_store,
                    repo_root=self._repo_root,
                ),
            )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=now,
                metadata={
                    "slice_id": p.slice_id,
                    "slice_handoff": handoff.model_dump(mode="json"),
                    "handoff_summary": handoff_md,
                    **(
                        {"memory_chunk_ids": memory_chunk_ids_from_hits(memory_hits)}
                        if memory_hits
                        else {}
                    ),
                },
                payload=StageStartedPayload(stage_name="slice.handoff", attempt=1),
            ),
        )
        from orchestrator.context_compaction import maybe_emit_compaction_event

        maybe_emit_compaction_event(
            self._store,
            run_id=run_id,
            events=self._store.list_run_events(str(run_id)),
            compaction_trigger="auto_handoff",
        )
        from orchestrator.ci_bridge import attach_external_ci_metadata

        attach_external_ci_metadata(
            meta,
            run_id=run_id,
            verdict="PASS" if gate.passed else "FAIL",
            stage_name="slice.gate",
        )
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

    def execute_single_micro_slice(
        self: MicroSliceHost,
        run_id: UUID,
        *,
        slice_index: int,
        workspace: Path | None = None,
        plan: Any | None = None,
        backlog_slice_id: str | None = None,
    ) -> Any:
        from typing import cast

        from orchestrator.slice.executor import execute_single_micro_slice

        return execute_single_micro_slice(
            cast(Any, self),
            run_id,
            slice_index=slice_index,
            workspace=workspace,
            plan=plan,
            backlog_slice_id=backlog_slice_id,
        )

    def execute_micro_slice_pass(
        self: MicroSliceHost,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> list[Any]:
        from typing import cast

        from orchestrator.slice.executor import execute_micro_slice_pass

        return execute_micro_slice_pass(cast(Any, self), run_id, workspace=workspace)

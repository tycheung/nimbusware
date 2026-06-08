from __future__ import annotations

from typing import Any

from nimbusware_orchestrator._pipeline._helpers import (
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
from nimbusware_orchestrator._pipeline.protocol_hosts import MicroSliceHost
from nimbusware_orchestrator.slice_gate import SliceGateChainResult


class MicroSliceMixin:
    def record_micro_slice_plan(
        self: MicroSliceHost,
        run_id: UUID,
        plan: dict[str, Any] | Any,
    ) -> None:
        """Persist a slice plan marker for timeline read-models."""
        from nimbusware_orchestrator.micro_slice import SlicePlan, parse_slice_plan

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
    ) -> SliceGateChainResult:
        """Run per-slice gate chain and append pass/fail stage events."""
        from nimbusware_orchestrator.micro_slice import SlicePlan, parse_slice_plan
        from nimbusware_orchestrator.slice_context_packet import build_slice_context_packet
        from nimbusware_orchestrator.slice_gate import run_slice_gate_chain
        from nimbusware_orchestrator.slice_handoff import (
            build_slice_handoff_summary,
            handoff_markdown_capped,
            latest_handoff_from_events,
        )
        from nimbusware_orchestrator.workflow_memory import (
            memory_settings_from_run_metadata,
            pinned_generation_for_scope,
            query_digest,
            retrieve_memory_excerpt_for_slice,
            run_memory_retrieval_enabled,
        )

        p: SlicePlan = plan if isinstance(plan, SlicePlan) else parse_slice_plan(plan)
        gate = run_slice_gate_chain(
            p,
            verify_ok=verify_ok,
            critique_verdicts=critique_verdicts,
            tests_passed=tests_passed,
            e2e_passed=e2e_passed,
            e2e_detail=e2e_detail,
        )
        run_meta = self._run_created_metadata(run_id)
        memory_excerpt = ""
        memory_hits: list[Any] = []
        memory_scope = ""
        memory_settings = memory_settings_from_run_metadata(run_meta)
        if run_memory_retrieval_enabled(run_meta) and self._memory_chunk_store is not None:
            memory_excerpt, memory_hits, memory_scope = retrieve_memory_excerpt_for_slice(
                self._memory_chunk_store,
                p,
                repo_root=self._repo_root,
                settings=memory_settings,
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
            "slice_context_packet": packet.model_dump(mode="json"),
            "slice_handoff": handoff.model_dump(mode="json"),
        }
        if memory_hits:
            from nimbusware_memory.audit import append_memory_retrieval_emitted_event

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
                },
                payload=StageStartedPayload(stage_name="slice.handoff", attempt=1),
            ),
        )
        from nimbusware_orchestrator.context_compaction import maybe_emit_compaction_event

        maybe_emit_compaction_event(
            self._store,
            run_id=run_id,
            events=self._store.list_run_events(str(run_id)),
            compaction_trigger="auto_handoff",
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

    def _micro_slice_enabled_for_run(self: MicroSliceHost, run_id: UUID) -> bool:
        from nimbusware_orchestrator.micro_slice_executor import micro_slice_effective_from_rows

        rows = self._store.list_run_events(str(run_id))
        return micro_slice_effective_from_rows(rows) is not None

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

        from nimbusware_orchestrator.micro_slice_executor import execute_single_micro_slice

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

        from nimbusware_orchestrator.micro_slice_executor import execute_micro_slice_pass

        return execute_micro_slice_pass(cast(Any, self), run_id, workspace=workspace)

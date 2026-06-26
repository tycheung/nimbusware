from __future__ import annotations

from nimbusware_env.env_flags import env_tri_state
from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    Any,
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Verdict,
    datetime,
    load_bundle_tags_for_bundle_id,
    load_bundle_title_for_bundle_id,
    rank_bundle_compatibility_candidates,
    select_bundle_id_for_workflow,
    timezone,
    uuid4,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import IntegratorOptionalStagesHost
from nimbusware_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_event_would_emit,
    parse_integrator_gate_project_tags,
)


class IntegratorOptionalStagesMixin:
    def _maybe_emit_integrator_dep_preflight(
        self: IntegratorOptionalStagesHost,
        run_id: UUID,
        *,
        bundle_id: str,
    ) -> None:
        from nimbusware_config.persist import load_bundle_catalog_dict
        from nimbusware_orchestrator.integrator_dep_preflight import (
            analyze_integrator_dep_conflicts,
        )

        if env_tri_state("NIMBUSWARE_INTEGRATOR_DEP_PREFLIGHT") != "on":
            return
        ws = self._repo_root
        pyproject = ws / "pyproject.toml"
        catalog = load_bundle_catalog_dict(ws, materializer=self._config_materializer)
        bundle_meta: dict[str, Any] | None = None
        bundles_raw = catalog.get("bundles") if isinstance(catalog, dict) else None
        if isinstance(bundles_raw, list):
            for row in bundles_raw:
                if isinstance(row, dict) and str(row.get("id") or "") == bundle_id:
                    bundle_meta = row
                    break
        conflicts = analyze_integrator_dep_conflicts(
            pyproject_path=pyproject,
            bundle_meta=bundle_meta,
        )
        if not conflicts:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("metadata") or {}).get("integrator_dep_preflight")
            for r in rows
            if r.get("event_type") == EventType.FINDING_CREATED.value
        ):
            return
        from agent_core.models import (
            EventType as ET,
        )
        from agent_core.models import (
            FindingCreatedEvent,
            FindingCreatedPayload,
            Severity,
        )

        self._store.append(
            FindingCreatedEvent(
                event_type=ET.FINDING_CREATED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"integrator_dep_preflight": True, "bundle_id": bundle_id},
                payload=FindingCreatedPayload(
                    finding_id=uuid4(),
                    category="integrator",
                    owner_role=uuid4(),
                    severity=Severity.LOW,
                    source_artifact=f"integrator_dep_preflight:{bundle_id}",
                    repro_steps=[c.get("detail", "") for c in conflicts[:20]],
                    required_fixes=[],
                ),
            ),
        )

    def _emit_bundle_integrator_gate(self: IntegratorOptionalStagesHost, run_id: UUID) -> None:
        from nimbusware_extensions.extension_runtime import ModuleIntegrator
        from nimbusware_orchestrator._pipeline._helpers_runtime import optional_rows_and_profile

        rows, wf = optional_rows_and_profile(self, run_id)
        mat = self._config_materializer
        if not integrator_gate_event_would_emit(
            self._repo_root,
            wf,
            config_materializer=mat,
        ):
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
        self._maybe_emit_integrator_dep_preflight(run_id, bundle_id=bundle_id)
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
            bundle_outcome_store=self._bundle_outcome_store,
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
        from nimbusware_orchestrator.integrator_live_context import (
            integrator_live_context_from_rows,
        )

        live_ctx = integrator_live_context_from_rows(rows)
        if live_ctx:
            gate_meta["integrator_live_context"] = live_ctx
        verdict = Verdict.PASS if ok else Verdict.FAIL
        from nimbusware_extensions.bundle_memory import (
            build_bundle_outcome_from_gate,
            bundle_outcome_metadata,
        )

        outcome = build_bundle_outcome_from_gate(
            run_id=run_id,
            bundle_id=bundle_id,
            workflow_profile=wf,
            project_tags=list(project_tags),
            integrator_score=score,
            verdict=verdict,
        )
        gate_meta["bundle_outcome"] = bundle_outcome_metadata(outcome)
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
        from nimbusware_orchestrator.ci_bridge import notify_gate_decision_external

        ci_status = notify_gate_decision_external(
            run_id=run_id,
            verdict=str(gate_payload.verdict.value),
            stage_name=gate_payload.stage_name,
        )
        if ci_status.get("status") != "skipped":
            gate_meta["external_ci"] = ci_status
        if self._bundle_outcome_store is not None:
            store_seq = self._store.max_store_seq_for_run(str(run_id))
            persisted = build_bundle_outcome_from_gate(
                run_id=run_id,
                bundle_id=bundle_id,
                workflow_profile=wf,
                project_tags=list(project_tags),
                integrator_score=score,
                verdict=verdict,
                source_store_seq=store_seq,
            )
            self._bundle_outcome_store.append(persisted)

from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
    UUID,
    Any,
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Verdict,
    datetime,
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_bundle_title_for_bundle_id,
    load_integrator_gate_emit_enabled,
    parse_integrator_gate_project_tags,
    rank_bundle_compatibility_candidates,
    select_bundle_id_for_workflow,
    timezone,
    uuid4,
    workflow_profile_from_run_created_rows,
)
from nimbusware_env.env_flags import env_tri_state


class IntegratorOptionalStagesMixin:
    def _emit_bundle_integrator_gate(self, run_id: UUID) -> None:
        tri = env_tri_state("HERMES_EMIT_INTEGRATOR_GATE")
        if tri == "off":
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
        if tri != "on" and not yaml_on and not wf_on:
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
        verdict = Verdict.PASS if ok else Verdict.FAIL
        from hermes_extensions.bundle_memory import (
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
        from hermes_orchestrator.ci_bridge import notify_gate_decision_external

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

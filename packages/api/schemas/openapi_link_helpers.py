from __future__ import annotations

from typing import Any

RUN_LIST_LINK_HEADER: dict[str, Any] = {
    "description": (
        "RFC 5988 Web Linking: comma-separated entries when pagination applies. "
        '``rel="next"`` advances offset or keyset ``cursor``; ``rel="prev"`` only for '
        "non-zero offset lists."
    ),
    "schema": {"type": "string"},
}

RUN_DETAIL_LINK_HEADER: dict[str, Any] = {
    "description": (
        'RFC 5988 Web Linking on **200**: comma-separated ``<``URL``>; rel="…"`` entries for '
        "``timeline`` and ``findings`` child resources of this ``run_id`` (also set at runtime "
        "when the run exists). Clients can still derive URLs from ``/v1/runs/{run_id}/…`` "
        "templates if the header is stripped by a proxy."
    ),
    "schema": {"type": "string"},
    "example": (
        '</v1/runs/11111111-1111-4111-8111-111111111111/timeline>; rel="timeline", '
        '</v1/runs/11111111-1111-4111-8111-111111111111/findings>; rel="findings"'
    ),
}


def format_run_detail_link_header(run_id: str) -> str:
    return (
        f'</v1/runs/{run_id}/timeline>; rel="timeline", '
        f'</v1/runs/{run_id}/findings>; rel="findings"'
    )


RUN_TIMELINE_LINK_HEADER: dict[str, Any] = {
    "description": (
        "RFC 5988 Web Linking on **200**: ``run`` points at ``GET /v1/runs/{run_id}``; "
        "``findings`` at ``GET /v1/runs/{run_id}/findings``."
    ),
    "schema": {"type": "string"},
    "example": (
        '</v1/runs/11111111-1111-4111-8111-111111111111>; rel="run", '
        '</v1/runs/11111111-1111-4111-8111-111111111111/findings>; rel="findings"'
    ),
}


def format_run_timeline_link_header(run_id: str) -> str:
    return f'</v1/runs/{run_id}>; rel="run", </v1/runs/{run_id}/findings>; rel="findings"'


RUN_TIMELINE_RESPONSE_200: dict[str, Any] = {
    "description": (
        "Replayed canonical events for the run plus top-level read-model "
        "summaries (``integrator_gate`` / ``self_refinement`` optional keys are "
        "presence-gated; degraded-metadata skip-vs-emit differs per helper): "
        "``integrator_gate`` (latest; optional ``bundle_compatibility_ranking`` "
        "pipeline inputs, ``selected_bundle_rank``, ``selected_bundle_id``), "
        "``integrator_gate_history`` "
        "(chronological gate decisions, bounded), ``integrator_gate_delta`` "
        "(latest vs prior gate when at least two decisions exist), ``agent_evaluator`` "
        "(optional ``auto_promote`` / ``auto_create_persona`` nested objects plus flattened "
        "``auto_promote_*`` / ``auto_create_*`` scalar fields when present; "
        "``evaluation_branch`` rules vs ``rules_with_llm_policy``; "
        "``llm_evaluation_summary`` / ``llm_evaluation_status`` when LLM policy ran), "
        "``self_refinement`` (latest ``self_refinement:policy`` marker plus "
        "optional evaluation fields ``evaluation_status`` / ``evaluation_gaps`` / "
        "``promotion_ready`` / ``coverage_*`` / ``max_iterations`` / "
        "``max_iterations_exceeded`` / flattened ``auto_promote_*`` when present, "
        "``phase_d_signal`` (latest ``self_refinement.loop.signalled`` event "
        "with attempt/max-iterations snapshot, rules gate, optional LLM branch "
        "``orchestration_branch`` / ``llm_critique_*`` fields for Phase D), "
        "``llm_critique_stage`` (latest ``self_refinement.critique`` gate panel "
        "verdict when emitted), ``llm_critique_summary`` from stage metadata when present, "
        "``marker_count`` session total, "
        "``first_marker_occurred_at``, and "
        "``last_marker_occurred_at`` when markers exist; omitted when "
        "``NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER`` is ``0``/``false``/``no``), "
        "``self_refinement_marker_history`` (chronological policy markers, bounded), "
        "``run_escalated`` (latest), ``run_escalated_history`` (chronological "
        "bounded list), ``run_escalated_delta`` (latest vs prior when at least "
        "two escalations exist), ``security_scan_on_verify`` (latest), "
        "``security_scan_on_verify_history`` (bounded chronological list), "
        "``preflight`` "
        "(latest ``model.preflight.passed`` projection — provider, "
        "validated model id, p95 latency, multisample count, and per-sample "
        "``health_latency_samples_ms`` when persisted; null when preflight "
        "was skipped via ``NIMBUSWARE_SKIP_PREFLIGHT``), and ``scraper_fetch`` "
        "(latest terminal ``scraper:fetch`` ``stage.passed`` / ``stage.failed`` "
        "with fetch count, total bytes, failure ``reason_code`` when set, and capped "
        "``fetches`` per-URL rows when present), and "
        "``universal_critique`` (latest ``gate.decision.emitted`` per "
        "``*.critique`` stage with ``producer_taxonomy_key`` alignment and "
        "``stage_count`` / ``fail_count`` / ``pass_count`` rollups, "
        "``distinct_fail_stages``, plus optional ``critique_coverage`` "
        "frozen from first ``run.created``), "
        "and ``persona_assignment`` (frozen composite persona ids from the first "
        "``run.created`` when present), "
        "``stage_graph`` (``stage_count``, ``parallel_group_count``, "
        "``ordered_stage_names`` from frozen ``run.created`` metadata), "
        "``parallel_writer_groups`` (writer parallel-group gate pass/fail rollups, "
        "``dispatch_mode``, per-stage ``stage_details``), "
        "and ``critic_matrix_live`` (orchestration gate matrix rows + summary)."
    ),
    "headers": {
        "Link": RUN_TIMELINE_LINK_HEADER,
    },
}

RUN_FINDINGS_LINK_HEADER: dict[str, Any] = {
    "description": (
        "RFC 5988 Web Linking on **200**: ``run`` points at ``GET /v1/runs/{run_id}``; "
        "``timeline`` at ``GET /v1/runs/{run_id}/timeline``."
    ),
    "schema": {"type": "string"},
    "example": (
        '</v1/runs/11111111-1111-4111-8111-111111111111>; rel="run", '
        '</v1/runs/11111111-1111-4111-8111-111111111111/timeline>; rel="timeline"'
    ),
}


def format_run_findings_link_header(run_id: str) -> str:
    return f'</v1/runs/{run_id}>; rel="run", </v1/runs/{run_id}/timeline>; rel="timeline"'

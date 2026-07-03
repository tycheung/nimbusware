from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType


def _coerce_samples_ms(raw: Any) -> list[int] | None:
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
    from env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE")


def _agent_evaluator_auto_create_env_disabled() -> bool:
    from env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE")


def _self_refinement_stage_marker_env_disabled() -> bool:
    from env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER")


def _self_refinement_auto_promote_env_disabled() -> bool:
    from env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_SELF_REFINEMENT_AUTO_PROMOTE")


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
        r for r in rows if r.get("event_type") == EventType.SELF_REFINEMENT_LOOP_SIGNALLED.value
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


def optional_tri_allows_emit(tri: str | None) -> bool:
    return tri != "off"


def optional_stage_yaml_gate(
    env_key: str,
    host: Any,
    run_id: UUID,
    parse_block: Callable[..., Any],
) -> tuple[str | None, list[dict[str, Any]], str, Any] | None:
    from env.env_flags import env_tri_state

    tri = env_tri_state(env_key)
    if not optional_tri_allows_emit(tri):
        return None
    rows, wf = optional_rows_and_profile(host, run_id)
    block = parse_block(
        host._repo_root,
        wf,
        config_materializer=host._config_materializer,
    )
    if tri != "on" and not block.enabled:
        return None
    return tri, rows, wf, block


def optional_rows_and_profile(host: Any, run_id: UUID) -> tuple[list[dict[str, Any]], str]:
    from orchestrator.integrator_gate import workflow_profile_from_run_created_rows

    rows = host._store.list_run_events(str(run_id))
    wf = workflow_profile_from_run_created_rows(rows) or ""
    return rows, wf


def optional_meta_section(host: Any, run_id: UUID, key: str) -> dict[str, Any]:
    meta = host._run_created_metadata(run_id)
    return mapping_or_empty(meta.get(key))


def gate_fail_for_stage(rows: list[dict[str, Any]], stage_name: str) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        pl = mapping_or_empty(row.get("payload"))
        if pl.get("stage_name") != stage_name:
            continue
        return str(pl.get("verdict", "")).upper() == "FAIL"
    return False


def ollama_runtime_from_host(host: Any) -> tuple[str, float]:
    runtime = mapping_or_empty(host._base_cfg().get("runtime"))
    return (
        str(runtime.get("base_url", "http://localhost:11434")),
        float(runtime.get("request_timeout_seconds", 120)),
    )

"""Live orchestration critic matrix from gate + stage events ."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from hermes_orchestrator.stage_graph import stage_graph_from_run_created_metadata


def _json_safe_metadata(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        try:
            return _json_safe_metadata(value.value)
        except Exception:
            return str(value)
    if isinstance(value, list):
        return [_json_safe_metadata(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe_metadata(v) for k, v in value.items()}
    return str(value)


def _run_created_stage_graph(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for ev in events:
        if ev.get("event_type") != "run.created":
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            return stage_graph_from_run_created_metadata(meta)
        break
    return None


def build_live_critic_matrix_rows(
    events: list[dict[str, Any]],
    stage_graph_meta: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Merge ``gate.decision.emitted`` with stage graph context for in-progress matrix rows."""
    sg = stage_graph_meta if stage_graph_meta is not None else _run_created_stage_graph(events)
    gate_by_stage: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event_type") != "gate.decision.emitted":
            continue
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        stage_name = pl.get("stage_name")
        if not isinstance(stage_name, str) or not stage_name.strip():
            continue
        gate_by_stage[stage_name.strip()] = {
            "stage_name": stage_name.strip(),
            "verdict": pl.get("verdict"),
            "unanimous_pass_required": pl.get("unanimous_pass_required"),
            "failing_critics": pl.get("failing_critics"),
            "parallel_group": (ev.get("metadata") or {}).get("parallel_group")
            if isinstance(ev.get("metadata"), dict)
            else None,
            "stage_graph_order_index": (ev.get("metadata") or {}).get("stage_graph_order_index")
            if isinstance(ev.get("metadata"), dict)
            else None,
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
        }

    critique_stages: list[str] = []
    if isinstance(sg, dict):
        ordered = sg.get("ordered_stage_names")
        if isinstance(ordered, list):
            critique_stages = [
                str(x)
                for x in ordered
                if isinstance(x, str) and str(x).strip().endswith(".critique")
            ]
    if not critique_stages:
        critique_stages = sorted(gate_by_stage.keys())

    rows: list[dict[str, Any]] = []
    for stage_name in critique_stages:
        gate = gate_by_stage.get(stage_name)
        if gate is not None:
            verdict_raw = gate.get("verdict")
            verdict = str(verdict_raw).strip().upper() if verdict_raw is not None else "PENDING"
            rows.append(
                {
                    "stage_name": stage_name,
                    "verdict": verdict,
                    "unanimous_pass_required": _json_safe_metadata(
                        gate.get("unanimous_pass_required"),
                    ),
                    "failing_critics": _json_safe_metadata(gate.get("failing_critics")),
                    "parallel_group": gate.get("parallel_group"),
                    "stage_graph_order_index": gate.get("stage_graph_order_index"),
                    "event_id": _json_safe_metadata(gate.get("event_id")),
                    "occurred_at": _json_safe_metadata(gate.get("occurred_at")),
                    "status": "decided",
                },
            )
        else:
            rows.append(
                {
                    "stage_name": stage_name,
                    "verdict": "PENDING",
                    "unanimous_pass_required": None,
                    "parallel_group": None,
                    "stage_graph_order_index": None,
                    "event_id": None,
                    "occurred_at": None,
                    "status": "pending",
                },
            )
    return rows


def critic_matrix_unanimous_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pass/fail/pending counts per stage row."""
    pass_count = 0
    fail_count = 0
    pending_count = 0
    fail_stage_names: list[str] = []
    failing_critics: set[str] = set()
    for row in rows:
        verdict = str(row.get("verdict", "")).strip().upper()
        stage_name = row.get("stage_name")
        if verdict == "PASS":
            pass_count += 1
        elif verdict == "FAIL":
            fail_count += 1
            if isinstance(stage_name, str) and stage_name.strip():
                fail_stage_names.append(stage_name.strip())
            raw_failing = row.get("failing_critics")
            if isinstance(raw_failing, list):
                for critic in raw_failing:
                    if isinstance(critic, str) and critic.strip():
                        failing_critics.add(critic.strip())
        else:
            pending_count += 1
    return {
        "row_count": len(rows),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pending_count": pending_count,
        "fail_stage_names": sorted(set(fail_stage_names)),
        "failing_critics": sorted(failing_critics),
    }


def enrich_gate_metadata_with_critic_matrix_live(
    events: list[dict[str, Any]],
    *,
    stage_name: str,
    base_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ``metadata.critic_matrix_live`` snapshot for ``gate.decision.emitted`` append."""
    meta = dict(base_metadata or {})
    sg = _run_created_stage_graph(events)
    rows = build_live_critic_matrix_rows(events, sg)
    summary = critic_matrix_unanimous_summary(rows)
    meta["critic_matrix_live"] = _json_safe_metadata(
        {
            "stage_name": stage_name,
            "rows": rows,
            "summary": summary,
        },
    )
    return _json_safe_metadata(meta)

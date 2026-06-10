from __future__ import annotations

import re
from typing import Any

from agent_core.models import EventType
from nimbusware_maker.intent import (
    plan_summary_from_requirements,
    requirements_from_run_created_metadata,
)
from nimbusware_projections.builders.pressure_headline import (
    latest_resource_pressure_from_events,
)

_SLICE_STAGE_NAMES = frozenset(
    {
        "slice.plan",
        "slice.implement",
        "slice.verify",
        "slice.critique",
        "slice.test",
        "slice.gate",
        "slice.handoff",
    },
)


def _latest_handoff_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in events:
        if _stage_name(row) != "slice.handoff":
            continue
        meta = _metadata(row)
        summary = meta.get("handoff_summary")
        handoff = meta.get("slice_handoff")
        if isinstance(summary, str) and summary.strip():
            latest = {
                "summary": summary,
                "handoff": handoff if isinstance(handoff, dict) else None,
                "slice_id": meta.get("slice_id"),
            }
    return latest


def _stage_name(row: dict[str, Any]) -> str:
    payload = row.get("payload")
    if isinstance(payload, dict):
        name = payload.get("stage_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return ""


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("metadata")
    return dict(meta) if isinstance(meta, dict) else {}


def pytest_bullets(test_output: str) -> list[str]:
    bullets: list[str] = []
    for line in test_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if " PASSED" in stripped or stripped.startswith("FAILED"):
            bullets.append(stripped[:140])
        elif " passed in " in stripped or stripped.startswith("= "):
            bullets.append(stripped[:140])
    if not bullets and test_output.strip():
        first = test_output.strip().splitlines()[0][:140]
        bullets.append(first)
    return bullets[:8]


def _slice_plans(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in events:
        meta = _metadata(row)
        if not meta.get("slice_plan"):
            continue
        sid = str(meta.get("slice_id") or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        paths = meta.get("target_paths")
        target_paths = [str(p) for p in paths] if isinstance(paths, list) else []
        plans.append(
            {
                "slice_id": sid,
                "rationale": str(meta.get("rationale") or "").strip(),
                "target_paths": target_paths,
            },
        )
    return plans


def _slice_gate_rows(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_slice: dict[str, dict[str, Any]] = {}
    for row in events:
        if row.get("event_type") not in {
            EventType.STAGE_PASSED.value,
            EventType.STAGE_FAILED.value,
        }:
            continue
        if _stage_name(row) != "slice.gate":
            continue
        meta = _metadata(row)
        sid = str(meta.get("slice_id") or "").strip()
        if not sid:
            continue
        verdict = str(meta.get("slice_gate_verdict") or "").strip().upper()
        packet = meta.get("slice_context_packet")
        test_output = ""
        if isinstance(packet, dict):
            test_output = str(packet.get("test_output") or "")
        tests_passed = meta.get("tests_passed")
        by_slice[sid] = {
            "verdict": verdict or None,
            "tests_passed": tests_passed if isinstance(tests_passed, bool) else None,
            "test_output": test_output,
        }
    return by_slice


def _latest_slice_stage(events: list[dict[str, Any]]) -> tuple[str, str] | None:
    latest: tuple[str, str] | None = None
    for row in events:
        stage = _stage_name(row)
        if stage not in _SLICE_STAGE_NAMES:
            continue
        meta = _metadata(row)
        sid = str(meta.get("slice_id") or "").strip()
        if sid:
            latest = (sid, stage)
    return latest


def _headline_for_slice(
    *,
    index: int,
    total: int,
    status: str,
    tests_passed: bool | None,
) -> str:
    if status == "passed":
        if tests_passed is False:
            return f"Slice {index} of {total} — tests failed"
        return f"Slice {index} of {total} — tests passed — ready for next slice"
    if status == "failed":
        return f"Slice {index} of {total} — blocked at gates"
    if status == "in_progress":
        return f"Slice {index} of {total} — in progress"
    return f"Slice {index} of {total} — planned"


def maker_progress_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    requirements: dict[str, Any] | None = None
    work_type: str | None = None
    slice_total_hint = 2
    campaign_mode = False
    run_status = "created"
    for row in events:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = _metadata(row)
        requirements = requirements_from_run_created_metadata(meta)
        raw_wt = str(meta.get("work_type") or "").strip().lower()
        if raw_wt:
            work_type = raw_wt
        ce = meta.get("campaign_effective")
        if isinstance(ce, dict) and ce.get("enabled"):
            campaign_mode = True
            policy = ce.get("policy")
            if isinstance(policy, dict):
                raw_max = policy.get("max_slices")
                if isinstance(raw_max, int) and raw_max > 0:
                    slice_total_hint = raw_max
        ms = meta.get("micro_slice_effective")
        if isinstance(ms, dict) and ms.get("enabled"):
            raw_count = ms.get("max_slices")
            if isinstance(raw_count, int) and raw_count > 0:
                slice_total_hint = raw_count
        break

    if campaign_mode:
        from agent_core.read.campaign import backlog_from_events

        backlog = backlog_from_events(events)
        if backlog is not None:
            slice_total_hint = max(slice_total_hint, backlog.metadata.total_slices_planned)

    if any(r.get("event_type") == EventType.RUN_STARTED.value for r in events):
        run_status = "running"
    if any(r.get("event_type") == EventType.RUN_COMPLETED.value for r in events):
        run_status = "complete"
    if any(r.get("event_type") == EventType.RUN_FAILED.value for r in events):
        run_status = "failed"
    if campaign_mode and any(
        r.get("event_type") == EventType.CAMPAIGN_COMPLETED.value for r in events
    ):
        run_status = "complete"
    if campaign_mode and any(
        r.get("event_type") == EventType.CAMPAIGN_FAILED.value for r in events
    ):
        run_status = "failed"

    plans = _slice_plans(events)
    gates = _slice_gate_rows(events)
    total = max(len(plans), slice_total_hint, 1)

    slices_out: list[dict[str, Any]] = []
    sentences: list[str] = []
    plan_summary = plan_summary_from_requirements(requirements)
    sentences.append(plan_summary)

    passed_count = 0
    blocked = False
    for idx, plan in enumerate(plans, start=1):
        sid = plan["slice_id"]
        gate = gates.get(sid, {})
        verdict = gate.get("verdict")
        tests_passed = gate.get("tests_passed")
        test_output = str(gate.get("test_output") or "")
        if verdict == "PASS":
            status = "passed"
            passed_count += 1
        elif verdict == "FAIL":
            status = "failed"
            blocked = True
        else:
            latest = _latest_slice_stage(events)
            status = "in_progress" if latest and latest[0] == sid else "planned"
        headline = _headline_for_slice(
            index=idx,
            total=total,
            status=status,
            tests_passed=tests_passed if isinstance(tests_passed, bool) else None,
        )
        bullets = pytest_bullets(test_output) if test_output else []
        if status == "passed" and not bullets:
            bullets = ["Scoped tests passed"]
        elif status == "failed" and not bullets:
            bullets = ["Scoped tests did not pass"]
        slices_out.append(
            {
                "slice_id": sid,
                "index": idx,
                "status": status,
                "headline": headline,
                "rationale": plan.get("rationale") or "",
                "target_paths": plan.get("target_paths") or [],
                "test_summary": {
                    "passed": tests_passed,
                    "bullets": bullets,
                },
            },
        )
        if verdict:
            sentences.append(headline)

    current_index = passed_count + 1 if not blocked else max(passed_count, 1)
    if not plans:
        overall = "awaiting_plan"
        current_headline = "Run created — waiting for the first slice plan"
        sentences.append(current_headline)
    elif blocked:
        overall = "blocked"
        current_headline = slices_out[-1]["headline"] if slices_out else "A slice was blocked"
    elif passed_count >= len(plans):
        if campaign_mode and run_status == "complete":
            overall = "complete"
            current_headline = f"Build complete — {passed_count} slices, campaign finished"
        else:
            overall = "complete" if run_status == "complete" else "ready_for_next"
            current_headline = (
                f"All {len(plans)} planned slices passed — ready for review"
                if passed_count
                else "Waiting for slice work to begin"
            )
    elif campaign_mode:
        overall = "building"
        current_headline = f"Campaign building — slice {passed_count + 1} of {total}"
    else:
        overall = "in_progress"
        active = slices_out[min(passed_count, len(slices_out) - 1)]
        current_headline = str(active.get("headline") or f"Working on slice {current_index}")

    pressure = latest_resource_pressure_from_events(events)
    if pressure and pressure.get("level") in {"warn", "throttle", "block"}:
        ph = str(pressure.get("headline") or "")
        if ph and ph not in current_headline:
            current_headline = f"{ph} — {current_headline}"

    out: dict[str, Any] = {
        "status": overall,
        "run_status": run_status,
        "plan_summary": plan_summary,
        "requirements": requirements,
        "slice_index": min(current_index, total),
        "slice_total": total,
        "slices_completed": passed_count,
        "current_headline": current_headline,
        "sentences": sentences,
        "slices": slices_out,
        "simple_mode": True,
    }
    if work_type:
        out["work_type"] = work_type
    if pressure:
        out["resource_pressure"] = pressure
    handoff = _latest_handoff_summary(events)
    if handoff:
        out["latest_handoff"] = handoff
    from nimbusware_projections.builders.context_budget import estimate_context_budget

    out["context_budget"] = estimate_context_budget(events)
    if campaign_mode:
        from nimbusware_projections.builders.campaign_progress import campaign_progress_from_events

        cp = campaign_progress_from_events(events)
        if cp:
            out["campaign_progress"] = cp
    from nimbusware_projections.builders.factory_status import factory_status_from_events

    factory_status = factory_status_from_events(events)
    if factory_status:
        out["factory_status"] = factory_status
    return out


def strip_operator_fields(payload: dict[str, Any]) -> dict[str, Any]:
    blocked_keys = re.compile(
        r"(telemetry|csv|fo133|matrix|critic_matrix|preflight_history)",
        re.IGNORECASE,
    )
    return {k: v for k, v in payload.items() if not blocked_keys.search(k)}

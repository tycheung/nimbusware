from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "golden" / "timelines"


def load_golden_timeline(name: str) -> dict[str, Any]:
    path = GOLDEN_ROOT / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: golden timeline must be a JSON object")
    return data


def _is_subsequence(required: list[str], actual: list[str]) -> bool:
    if not required:
        return True
    idx = 0
    for item in actual:
        if item == required[idx]:
            idx += 1
            if idx == len(required):
                return True
    return False


def assert_timeline_golden(events: list[dict[str, Any]], golden: dict[str, Any]) -> None:
    actual_types = [str(ev.get("event_type") or "") for ev in events]
    required = [str(x) for x in golden.get("required_subsequence") or []]
    if not _is_subsequence(required, actual_types):
        tail = actual_types[-10:]
        raise AssertionError(
            f"timeline missing required subsequence {required!r}; last_10_event_types={tail!r}"
        )
    required_stages = [str(x) for x in golden.get("required_stage_names") or []]
    if required_stages:
        seen_stages = [
            str((ev.get("payload") or {}).get("stage_name") or "")
            for ev in events
            if ev.get("event_type") in ("stage.started", "stage.passed")
        ]
        for stage in required_stages:
            if stage not in seen_stages:
                raise AssertionError(f"timeline missing required stage {stage!r}")
    min_stage_passed = int(golden.get("min_stage_passed") or 0)
    if min_stage_passed:
        passed = sum(1 for t in actual_types if t == "stage.passed")
        if passed < min_stage_passed:
            raise AssertionError(
                f"expected at least {min_stage_passed} stage.passed events, got {passed}"
            )

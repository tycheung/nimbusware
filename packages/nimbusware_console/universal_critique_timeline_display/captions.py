from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.universal_critique_timeline_display.rows import (
    universal_critique_from_timeline,
)


def universal_critique_timeline_fail_stage_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    stages = summary.get("stages")
    if not isinstance(stages, list):
        return None
    names: set[str] = set()
    for s in stages:
        if not isinstance(s, dict):
            continue
        verdict = s.get("verdict")
        if not isinstance(verdict, str) or verdict.strip().upper() != "FAIL":
            continue
        sn = s.get("stage_name")
        if isinstance(sn, str) and sn.strip():
            names.add(sn.strip())
    if not names:
        return None
    ordered = ", ".join(sorted(names))
    return f"FAIL critique stages: {ordered}."


def universal_critique_snapshot_from_compare_paste(
    parsed: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(parsed, Mapping):
        return None
    if "events" in parsed or "universal_critique" in parsed:
        return universal_critique_from_timeline(parsed)
    if isinstance(parsed.get("stages"), list):
        return dict(parsed)
    return None


def universal_critique_timeline_fail_count_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    fail_count = summary.get("fail_count")
    stage_count = summary.get("stage_count")
    if not isinstance(fail_count, int) or isinstance(fail_count, bool):
        return None
    if not isinstance(stage_count, int) or isinstance(stage_count, bool):
        return None
    if stage_count < 1:
        return None
    return (
        f"Universal critique gates: **{fail_count}** FAIL of **{stage_count}** "
        "stage(s) on this timeline."
    )



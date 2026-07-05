from __future__ import annotations

from pathlib import Path

from standards.profile import (
    StandardsProfile,
    resolve_standards_profile,
    streams_for_enforcement_level,
)
from standards.runner import run_bundle, run_streams
from standards.stream_results import StreamResult


def run_workspace_standards(
    workspace: Path,
    *,
    profile: StandardsProfile | None = None,
    enforcement_level: int | None = None,
) -> tuple[bool, list[StreamResult]]:
    effective = profile or resolve_standards_profile(workspace=workspace)
    results: list[StreamResult] = []
    for bundle_id in effective.bundle_ids:
        results.append(
            run_bundle(
                bundle_id,
                workspace=workspace,
                verdict_overrides=effective.verdict_overrides,
            ),
        )
    if enforcement_level is not None:
        stream_ids = (
            list(effective.stream_ids)
            if effective.stream_ids
            else list(streams_for_enforcement_level(enforcement_level))
        )
        if stream_ids:
            for _sid, stream_result in run_streams(stream_ids, workspace=workspace).items():
                results.append(stream_result)
    passed = all(r.passed for r in results)
    return passed, results


def format_standards_log(results: list[StreamResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"=== standards {result.stream_id} ===")
        for check in result.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"{check.check_id}: {status} ({check.verdict})")
            if check.detail and not check.passed:
                lines.append(check.detail[:800])
    return "\n".join(lines)

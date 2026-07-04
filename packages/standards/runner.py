from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from env import find_repo_root
from standards.registry import load_bundle_manifest, profile_stream_ids, stream_checks
from standards.stream_results import CheckResult, StreamResult
from standards.verdict import VerdictMode

ROOT = find_repo_root()


def _resolve_command(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not raw:
        msg = "check command must be a non-empty list"
        raise ValueError(msg)
    out: list[str] = []
    for part in raw:
        token = str(part)
        if token == "{python}":
            out.append(sys.executable)
        elif token == "{root}":
            out.append(str(ROOT))
        else:
            out.append(token)
    return out


def _run_subprocess(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )
    detail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, detail.strip()[:4000]


def _invoke_runner(runner: str, *, workspace: Path, params: dict[str, Any]) -> CheckResult:
    module_path, _, func_name = runner.partition(":")
    if not module_path or not func_name:
        msg = f"invalid runner import path: {runner!r}"
        raise ValueError(msg)
    mod = importlib.import_module(module_path)
    fn = getattr(mod, func_name)
    return fn(workspace=workspace, params=params)


def run_check_definition(
    spec: dict[str, Any],
    *,
    workspace: Path | None = None,
    default_verdict: VerdictMode = "hard_gate",
) -> CheckResult:
    check_id = str(spec.get("id") or "unknown")
    verdict: VerdictMode = spec.get("default_verdict") or default_verdict
    runner = spec.get("runner")
    if isinstance(runner, str) and runner.strip():
        params = spec.get("params")
        if not isinstance(params, dict):
            params = {}
        try:
            raw = _invoke_runner(runner.strip(), workspace=workspace or ROOT, params=params)
            passed = raw.passed
            if verdict in ("warn", "skip"):
                passed = True
            return CheckResult(
                check_id=check_id,
                passed=passed,
                verdict=verdict,
                detail=raw.detail,
                exit_code=raw.exit_code,
            )
        except Exception as exc:
            return CheckResult(
                check_id=check_id,
                passed=False,
                verdict=verdict,
                detail=str(exc),
                exit_code=1,
            )
    cmd = _resolve_command(spec.get("command"))
    code, detail = _run_subprocess(cmd, cwd=workspace if workspace else ROOT)
    passed = code == 0
    if verdict in ("warn", "skip"):
        passed = True
    return CheckResult(
        check_id=check_id,
        passed=passed,
        verdict=verdict,
        detail=detail,
        exit_code=code,
    )


def run_stream(stream_id: str, *, workspace: Path | None = None) -> StreamResult:
    checks: list[CheckResult] = []
    for spec in stream_checks(stream_id):
        checks.append(run_check_definition(spec, workspace=workspace))
    passed = all(c.passed for c in checks)
    return StreamResult(stream_id=stream_id, passed=passed, checks=checks)


def run_streams(stream_ids: list[str], *, workspace: Path | None = None) -> dict[str, StreamResult]:
    return {sid: run_stream(sid, workspace=workspace) for sid in stream_ids}


def run_profile(profile_id: str, *, workspace: Path | None = None) -> dict[str, StreamResult]:
    return run_streams(profile_stream_ids(profile_id), workspace=workspace)


def run_bundle(
    bundle_id: str,
    *,
    workspace: Path,
    verdict_overrides: dict[str, VerdictMode] | None = None,
) -> StreamResult:
    manifest = load_bundle_manifest(bundle_id)
    if manifest is None:
        return StreamResult(
            stream_id=f"bundle:{bundle_id}",
            passed=False,
            checks=[
                CheckResult(
                    check_id="bundle.missing",
                    passed=False,
                    verdict="hard_gate",
                    detail=f"bundle not found: {bundle_id}",
                    exit_code=1,
                ),
            ],
        )
    overrides = verdict_overrides or {}
    checks: list[CheckResult] = []
    raw_checks = manifest.get("checks")
    if not isinstance(raw_checks, list):
        raw_checks = []
    for spec in raw_checks:
        if not isinstance(spec, dict):
            continue
        cid = str(spec.get("id") or "")
        verdict: VerdictMode = overrides.get(cid) or spec.get("default_verdict") or "warn"
        spec = {**spec, "default_verdict": verdict}
        checks.append(run_check_definition(spec, workspace=workspace, default_verdict=verdict))
    passed = all(c.passed or c.verdict in ("warn", "skip") for c in checks)
    hard_fail = any((not c.passed) and c.verdict in ("hard_gate", "critique") for c in checks)
    return StreamResult(stream_id=f"bundle:{bundle_id}", passed=not hard_fail, checks=checks)


def run_bundles_for_facade(
    facade_id: str,
    *,
    workspace: Path,
    verdict_overrides: dict[str, VerdictMode] | None = None,
) -> list[StreamResult]:
    from standards.profile import facade_bundle_ids

    results: list[StreamResult] = []
    for bundle_id in facade_bundle_ids(facade_id):
        results.append(run_bundle(bundle_id, workspace=workspace, verdict_overrides=verdict_overrides))
    return results


def aggregate_passed(results: dict[str, StreamResult] | list[StreamResult]) -> bool:
    if isinstance(results, dict):
        items = results.values()
    else:
        items = results
    return all(r.passed for r in items)

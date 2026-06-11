#!/usr/bin/env python3
"""Optional SWE-bench-style harness for Nimbusware micro_slice profile.

Dry-run (default): validate manifest + fixture layout, emit JSON summary.
``--run``: in-memory orchestrator against fixture workspace; score slice.gate outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "swe_bench" / "manifest.json"


@dataclass
class SweBenchSummary:
    ok: bool
    mode: str
    manifest_path: str
    fixture_root: str
    workflow_profile: str
    message: str
    checks: list[str] = field(default_factory=list)
    slices_total: int = 0
    gates_passed: int = 0
    gates_failed: int = 0
    pass_rate: float = 0.0
    duration_sec: float = 0.0
    run_id: str = ""


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def _fixture_root(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    sub = str(manifest.get("fixture_subdir") or "repo").strip() or "repo"
    return manifest_path.parent / sub


def _score_slice_gates(results: list[Any]) -> tuple[int, int, int, float]:
    slices_total = len(results)
    gates_passed = sum(1 for g in results if getattr(g, "passed", False))
    gates_failed = slices_total - gates_passed
    pass_rate = gates_passed / slices_total if slices_total else 0.0
    return slices_total, gates_passed, gates_failed, pass_rate


def _apply_benchmark_env(manifest: dict[str, Any]) -> None:
    raw = manifest.get("benchmark_env")
    if not isinstance(raw, dict):
        return
    for key, value in raw.items():
        if value is None:
            continue
        os.environ[str(key)] = str(value)


def _fixture_slice_plan_factory(target_paths: list[str]):
    from nimbusware_orchestrator.micro_slice import parse_slice_plan

    def _plan(slice_index: int):
        return parse_slice_plan(
            {
                "slice_id": f"slice-{slice_index}",
                "rationale": "SWE-bench fixture micro-slice",
                "target_paths": target_paths,
                "acceptance_criteria": "Scoped fixture tests pass",
            },
        )

    return _plan


def _run_micro_slice_benchmark(
    *,
    repo_root: Path,
    fixture: Path,
    workflow_profile: str,
    manifest: dict[str, Any] | None = None,
) -> SweBenchSummary:
    checks: list[str] = ["benchmark_start"]
    os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    os.environ.setdefault("NIMBUSWARE_MICRO_SLICE_COUNT", "1")
    os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(repo_root))
    if manifest:
        _apply_benchmark_env(manifest)

    from unittest.mock import patch

    from nimbusware_orchestrator.pipeline import make_dev_orchestrator

    target_paths = ["calc.py"]
    if manifest:
        raw_paths = manifest.get("fixture_target_paths")
        if isinstance(raw_paths, list) and raw_paths:
            target_paths = [str(p) for p in raw_paths]

    t0 = time.perf_counter()
    orch, _store = make_dev_orchestrator(repo_root)
    run_id = orch.create_run(workflow_profile)
    checks.append("run_created")
    plan_factory = _fixture_slice_plan_factory(target_paths)
    with (
        patch(
            "nimbusware_orchestrator.micro_slice_plan.default_stub_slice_plan",
            plan_factory,
        ),
        patch(
            "nimbusware_orchestrator.micro_slice_executor.default_stub_slice_plan",
            plan_factory,
        ),
    ):
        results = orch.execute_micro_slice_pass(run_id, workspace=fixture.resolve())
    duration_sec = time.perf_counter() - t0
    slices_total, gates_passed, gates_failed, pass_rate = _score_slice_gates(results)
    checks.append(f"slices_total={slices_total}")
    checks.append(f"gates_passed={gates_passed}")
    checks.append(f"gates_failed={gates_failed}")

    return SweBenchSummary(
        ok=True,
        mode="run",
        manifest_path="",
        fixture_root=str(fixture),
        workflow_profile=workflow_profile,
        message="micro_slice benchmark completed",
        checks=checks,
        slices_total=slices_total,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        pass_rate=pass_rate,
        duration_sec=round(duration_sec, 3),
        run_id=str(run_id),
    )


def run_harness(
    *,
    manifest_path: Path,
    dry_run: bool = True,
    repo_root: Path | None = None,
) -> SweBenchSummary:
    checks: list[str] = []
    manifest = _load_manifest(manifest_path)
    checks.append("manifest_json_ok")
    fixture = _fixture_root(manifest_path, manifest)
    if not fixture.is_dir():
        return SweBenchSummary(
            ok=False,
            mode="dry_run" if dry_run else "run",
            manifest_path=str(manifest_path),
            fixture_root=str(fixture),
            workflow_profile=str(manifest.get("workflow_profile") or ""),
            message=f"fixture directory missing: {fixture}",
            checks=checks,
        )
    checks.append("fixture_dir_ok")
    py_files = list(fixture.rglob("*.py"))
    if not py_files:
        return SweBenchSummary(
            ok=False,
            mode="dry_run" if dry_run else "run",
            manifest_path=str(manifest_path),
            fixture_root=str(fixture),
            workflow_profile=str(manifest.get("workflow_profile") or ""),
            message="fixture repo has no .py files",
            checks=checks,
        )
    checks.append(f"python_files={len(py_files)}")
    profile = str(manifest.get("workflow_profile") or "micro_slice")
    if dry_run:
        return SweBenchSummary(
            ok=True,
            mode="dry_run",
            manifest_path=str(manifest_path),
            fixture_root=str(fixture),
            workflow_profile=profile,
            message="dry-run ok",
            checks=checks,
        )

    root = (repo_root or REPO_ROOT).resolve()
    summary = _run_micro_slice_benchmark(
        repo_root=root,
        fixture=fixture,
        workflow_profile=profile,
        manifest=manifest,
    )
    summary.manifest_path = str(manifest_path)
    summary.checks = checks + summary.checks

    min_rate = manifest.get("min_pass_rate")
    if min_rate is not None:
        try:
            threshold = float(min_rate)
        except (TypeError, ValueError):
            threshold = None
        if threshold is not None and summary.pass_rate < threshold:
            summary.ok = False
            summary.message = (
                f"pass_rate {summary.pass_rate:.3f} below min_pass_rate {threshold:.3f}"
            )
            summary.checks.append("min_pass_rate_fail")
        else:
            summary.checks.append("min_pass_rate_ok")

    out_dir = root / "benchmarks"
    if os.environ.get("NIMBUSWARE_SWE_BENCH_WRITE_JSON", "").lower() in ("1", "true", "yes"):
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "latest_swe_bench.json"
        out_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
        summary.checks.append(f"wrote={out_path.name}")

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nimbusware SWE-bench harness")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            os.environ.get("NIMBUSWARE_SWE_BENCH_MANIFEST", str(DEFAULT_MANIFEST)),
        ),
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--run", action="store_true", help="Run scored micro_slice benchmark")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout")
    args = parser.parse_args(argv)
    enabled = os.environ.get("NIMBUSWARE_SWE_BENCH_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    if not enabled:
        print("NIMBUSWARE_SWE_BENCH_ENABLED=0 — skipping", file=sys.stderr)
        return 0
    dry = not args.run
    summary = run_harness(manifest_path=args.manifest.resolve(), dry_run=dry)
    if args.json:
        print(json.dumps(asdict(summary), indent=2))
    else:
        print(summary.message)
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

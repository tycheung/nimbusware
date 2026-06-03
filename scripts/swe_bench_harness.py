#!/usr/bin/env python3
"""Optional SWE-bench-style harness for Hermes micro_slice profile (fo452).

Dry-run (default): validate manifest + fixture layout, emit JSON summary.
Full run: reserved for scheduled CI with workspace checkout (not required on PR).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
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
    checks: list[str]


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def _fixture_root(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    sub = str(manifest.get("fixture_subdir") or "repo").strip() or "repo"
    return manifest_path.parent / sub


def run_harness(
    *,
    manifest_path: Path,
    dry_run: bool = True,
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
            message="dry-run ok (full micro_slice run reserved for scheduled workflow)",
            checks=checks,
        )
    return SweBenchSummary(
        ok=False,
        mode="run",
        manifest_path=str(manifest_path),
        fixture_root=str(fixture),
        workflow_profile=profile,
        message="full benchmark run not implemented in dry CI; use --dry-run",
        checks=checks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes SWE-bench harness (fo452)")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            os.environ.get("HERMES_SWE_BENCH_MANIFEST", str(DEFAULT_MANIFEST)),
        ),
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--run", action="store_true", help="Attempt full benchmark (stub)")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout")
    args = parser.parse_args(argv)
    enabled = os.environ.get("HERMES_SWE_BENCH_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    if not enabled:
        print("HERMES_SWE_BENCH_ENABLED=0 — skipping", file=sys.stderr)
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

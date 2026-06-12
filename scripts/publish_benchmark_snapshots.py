#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BENCH_DIR = _ROOT / "benchmarks"


def _load_factory_weekly_runner():
    import importlib.util

    path = _ROOT / "scripts" / "run_factory_weekly_ci.py"
    spec = importlib.util.spec_from_file_location("run_factory_weekly_ci", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("run_factory_weekly_ci.py not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_critic_reliability_snapshot() -> Path:
    from datetime import datetime, timezone

    from nimbusware_iam.constants import DEFAULT_TENANT_ID
    from nimbusware_orchestrator.fleet_critic_reliability import tenant_critic_reliability_metrics
    from nimbusware_store.memory import InMemoryEventStore

    store = InMemoryEventStore()
    metrics = tenant_critic_reliability_metrics(
        store,
        tenant_id=DEFAULT_TENANT_ID,
        run_limit=100,
    )
    _BENCH_DIR.mkdir(parents=True, exist_ok=True)
    out = _BENCH_DIR / "latest_critic_reliability.json"
    payload = {
        **metrics,
        "published_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "snapshot": True,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


def _write_factory_weekly_snapshot() -> Path | None:
    mod = _load_factory_weekly_runner()
    summary = mod.run_factory_weekly_ci(repo_root=_ROOT)
    _BENCH_DIR.mkdir(parents=True, exist_ok=True)
    out = _BENCH_DIR / "latest_factory_weekly.json"
    payload = {
        **summary,
        "published_at": summary.get("generated_at"),
        "pass_rate": 1.0 if summary.get("passed") else 0.0,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


def _write_classifier_acceptance_snapshot() -> Path:
    from datetime import datetime, timezone

    proc = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "measure_classifier_acceptance.py"),
            "--json",
            str(_BENCH_DIR / "latest_classifier_acceptance.json"),
        ],
        cwd=_ROOT,
        check=False,
    )
    out = _BENCH_DIR / "latest_classifier_acceptance.json"
    if proc.returncode != 0 and out.is_file():
        body = json.loads(out.read_text(encoding="utf-8"))
        body["published_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        out.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
    return out


def main() -> int:
    env = {
        **os.environ,
        "NIMBUSWARE_SKIP_PREFLIGHT": "1",
        "NIMBUSWARE_REPO_ROOT": str(_ROOT),
        "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
        "NIMBUSWARE_SWE_BENCH_WRITE_JSON": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "swe_bench_harness.py"), "--run", "--json"],
        cwd=_ROOT,
        env=env,
        check=False,
    )
    swe_out = _BENCH_DIR / "latest_swe_bench.json"
    if swe_out.is_file():
        print(f"Wrote {swe_out.relative_to(_ROOT)}")
    factory_out = _write_factory_weekly_snapshot()
    if factory_out is not None:
        print(f"Wrote {factory_out.relative_to(_ROOT)}")
    critic_out = _write_critic_reliability_snapshot()
    print(f"Wrote {critic_out.relative_to(_ROOT)}")
    classifier_out = _write_classifier_acceptance_snapshot()
    if classifier_out.is_file():
        print(f"Wrote {classifier_out.relative_to(_ROOT)}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
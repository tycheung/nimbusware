#!/usr/bin/env python3
"""Validate production profile live-writer flags and record soak metadata."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_PRODUCTION = _ROOT / "configs" / "workflows" / "nimbusware_production.yaml"
_OUT = _ROOT / "benchmarks" / "latest_live_writers_soak.json"


def _load_production_profile() -> dict:
    if not _PRODUCTION.is_file():
        raise SystemExit(f"missing {_PRODUCTION}")
    doc = yaml.safe_load(_PRODUCTION.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise SystemExit("nimbusware_production.yaml must be a mapping")
    return doc


def _writer_flags(doc: dict) -> dict[str, bool | None]:
    iaw = doc.get("integration_adapter_writer") or {}
    refactor = doc.get("refactor") or {}
    return {
        "integration_adapter_writer_stub_only": iaw.get("stub_only"),
        "refactor_stub_only": refactor.get("stub_only"),
    }


def _run_pipeline_smoke(repo_root: Path) -> dict[str, object]:
    import subprocess

    env = {
        **os.environ,
        "NIMBUSWARE_SKIP_PREFLIGHT": "1",
        "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
        "NIMBUSWARE_REPO_ROOT": str(repo_root),
        "NIMBUSWARE_SLICE_IMPLEMENT": "stub",
    }
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "swe_bench_harness.py"), "--run", "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = round(time.perf_counter() - t0, 3)
    if proc.returncode != 0:
        return {
            "ok": False,
            "duration_sec": duration,
            "stderr": (proc.stderr or proc.stdout or "")[:500],
        }
    try:
        summary = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "duration_sec": duration, "parse_error": True}
    return {
        "ok": bool(summary.get("ok")),
        "pass_rate": summary.get("pass_rate"),
        "run_id": summary.get("run_id"),
        "duration_sec": duration,
        "workflow_profile": summary.get("workflow_profile"),
    }


def main() -> int:
    doc = _load_production_profile()
    flags = _writer_flags(doc)
    live_ok = (
        flags.get("integration_adapter_writer_stub_only") is False
        and flags.get("refactor_stub_only") is False
    )
    ollama_url = os.environ.get("NIMBUSWARE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    use_llm = os.environ.get("NIMBUSWARE_USE_LLM", "0").lower() in ("1", "true", "yes")

    smoke: dict[str, object] = {"skipped": True, "reason": "pipeline smoke optional"}
    try:
        if (_ROOT / "scripts" / "swe_bench_harness.py").is_file():
            smoke = _run_pipeline_smoke(_ROOT)
    except Exception as exc:  # noqa: BLE001
        smoke = {"ok": False, "error": str(exc)[:500]}

    payload = {
        "published_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "profile_path": "configs/workflows/nimbusware_production.yaml",
        "live_writer_flags_ok": live_ok,
        "writer_flags": flags,
        "ollama_base_url": ollama_url,
        "use_llm_env": use_llm,
        "note": (
            "Config validates stub_only:false on production writers. "
            "Full Ollama live-writer soak requires NIMBUSWARE_USE_LLM=1 and a running Ollama server."
        ),
        "pipeline_smoke": smoke,
        "passed": live_ok and bool(smoke.get("ok", smoke.get("skipped", False))),
    }
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "benchmarks" / "latest_fo2172_live_journey.json"
_JOURNEY = (
    "tests/e2e/journeys/test_one_prompt_fullstack_scope_journey.py"
    "::test_one_prompt_scope_to_fullstack_campaign_backlog"
)
_LLM_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "NIMBUSWARE_LLM_PROVIDER_URL",
)


def _live_requested() -> bool:
    return os.environ.get("NIMBUSWARE_FO2172_LIVE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _llm_configured() -> bool:
    return any(os.environ.get(key, "").strip() for key in _LLM_ENV_KEYS)


def _run_journey() -> dict[str, object]:
    env = dict(os.environ)
    env.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(_ROOT))
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            _JOURNEY,
            "-m",
            "e2e_journey",
            "-q",
            "--tb=short",
        ],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=600,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def main() -> int:
    live = _live_requested()
    llm = _llm_configured()
    body: dict[str, object] = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "journey": "fo2172_one_prompt_fullstack_scope",
        "live_requested": live,
        "llm_configured": llm,
        "skipped": False,
        "ok": False,
    }
    if not live:
        body["skipped"] = True
        body["skip_reason"] = "set NIMBUSWARE_FO2172_LIVE=1 to run live journey soak"
        body["ok"] = True
        _OUT.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        print("fo2172 live journey soak: skipped (opt-in)", flush=True)
        return 0

    if not llm:
        body["skip_reason"] = "no LLM provider env configured"
        _OUT.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        print("fo2172 live journey soak: LLM env missing", file=sys.stderr, flush=True)
        return 1

    result = _run_journey()
    body["journey_result"] = result
    body["ok"] = bool(result.get("ok"))
    _OUT.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    if not body["ok"]:
        print("fo2172 live journey soak: failed", file=sys.stderr, flush=True)
        return 1
    print("fo2172 live journey soak: OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

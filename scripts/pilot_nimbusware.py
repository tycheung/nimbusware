#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(ROOT))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")


def main() -> int:
    from nimbusware_api.app import app

    with TestClient(app) as client:
        r = client.post("/v1/runs", json={"workflow_profile": "default"})
        r.raise_for_status()
        run_id = r.json()["run_id"]
        client.post(f"/v1/runs/{run_id}/lifecycle/start").raise_for_status()
        client.post(f"/v1/runs/{run_id}/lifecycle/plan").raise_for_status()
        client.post(f"/v1/runs/{run_id}/lifecycle/verify").raise_for_status()
        tl = client.get(f"/v1/runs/{run_id}/timeline").json()
        types = [e["event_type"] for e in tl.get("events", [])]
        assert "run.created" in types
        assert "model.preflight.passed" in types
        assert "critic.verdict.emitted" in types
        print("pilot_ok", run_id, "events", len(types))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

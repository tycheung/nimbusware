from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_launch_eval_matrix_scores_default_workspaces() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "benchmarks" / "launch_eval.py"), "--matrix"],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={
            **dict(__import__("os").environ),
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(root),
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    rows = json.loads(proc.stdout)
    assert len(rows) >= 2
    workspaces = {r["workspace"] for r in rows}
    assert any("tiny_python_app" in w for w in workspaces)
    assert any("tiny_web_app" in w for w in workspaces)
    assert all("prompt_catalog" in r for r in rows)
    assert "static_site" in rows[0]["prompt_catalog"]

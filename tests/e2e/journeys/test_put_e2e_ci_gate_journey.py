from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _load_put_e2e_gate():
    path = REPO / "scripts" / "run_put_e2e_ci_gate.py"
    spec = importlib.util.spec_from_file_location("run_put_e2e_ci_gate", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.e2e
def test_put_e2e_ci_gate_passes_on_tiny_api() -> None:
    mod = _load_put_e2e_gate()
    summary = mod.run_put_e2e_ci_gate(repo_root=REPO)
    assert summary.get("workspace") == "tiny_api_app"
    assert summary.get("passed") is True, summary
    assert summary.get("put_e2e", {}).get("verdict") == "PASS"

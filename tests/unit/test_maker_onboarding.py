from __future__ import annotations

from pathlib import Path

import pytest

from maker.onboarding import is_onboarded, mark_onboarded, onboarding_flag_path
from maker.readiness.smoke import readiness_smoke_ok


class _FakeSession:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value


def test_mark_onboarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_MAKER_STATE_DIR", str(tmp_path))
    session = _FakeSession()
    assert not is_onboarded(session)
    mark_onboarded(session)
    assert is_onboarded(session)
    assert onboarding_flag_path().is_file()


def test_readiness_smoke_ok_accepts_ready_and_degraded() -> None:
    assert readiness_smoke_ok({"status": "ready"})[0]
    assert readiness_smoke_ok({"status": "degraded"})[0]
    ok, msg = readiness_smoke_ok({"status": "not_ready"})
    assert not ok
    assert "not ready" in msg.lower()


def test_preview_diff_for_plan_lists_targets(tmp_path: Path) -> None:
    from maker.slice_engine import preview_diff_for_plan
    from orchestrator.slice.micro_slice import SlicePlan

    ws = tmp_path / "ws"
    ws.mkdir()
    target = "packages/demo/app.py"
    (ws / "packages/demo").mkdir(parents=True)
    (ws / "packages/demo/app.py").write_text("print('hi')\n", encoding="utf-8")
    plan = SlicePlan(
        slice_id="s1",
        rationale="demo",
        target_paths=(target,),
        acceptance_criteria=("tests pass",),
    )
    text = preview_diff_for_plan(ws, plan)
    assert "Scoped implement" in text or target in text
    assert "bytes" in text or "demo" in text

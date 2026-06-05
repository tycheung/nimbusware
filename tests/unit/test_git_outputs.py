from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from nimbusware_orchestrator.git_outputs import (
    gh_pr_on_complete_enabled,
    git_native_outputs_enabled,
    maybe_finalize_git_outputs,
    maybe_open_gh_pr,
    run_branch_name,
    run_complete_commit_message,
    slice_commit_message,
)
from nimbusware_orchestrator.micro_slice import SlicePlan


def test_run_branch_name() -> None:
    rid = "abc-123"
    assert run_branch_name(rid) == f"nimbusware/run-{rid}"


def test_slice_commit_message() -> None:
    plan = SlicePlan(
        slice_id="s1",
        target_paths=("a.py",),
        rationale="fix lint",
    )
    assert "s1" in slice_commit_message(plan)
    assert "fix lint" in slice_commit_message(plan)


def test_run_complete_message() -> None:
    assert "3 slice" in run_complete_commit_message(uuid4(), slice_count=3)


def test_git_native_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_GIT_NATIVE_OUTPUTS", "1")
    assert git_native_outputs_enabled({}) is True
    assert gh_pr_on_complete_enabled({}) is False


def test_maybe_open_gh_pr_skips_without_gh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("nimbusware_orchestrator.git_outputs.shutil.which", lambda _: None)
    (tmp_path / ".git").mkdir()
    out = maybe_open_gh_pr(tmp_path, uuid4())
    assert out["status"] == "skipped"
    assert out["reason"] == "gh_not_found"


def test_maybe_finalize_git_outputs_disabled() -> None:
    out = maybe_finalize_git_outputs(Path("/tmp"), uuid4(), {}, slice_count=1)
    assert out["status"] == "skipped"


def test_maybe_finalize_git_branch_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_GIT_NATIVE_OUTPUTS", "1")
    (tmp_path / ".git").mkdir()
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr("nimbusware_orchestrator.git_outputs.subprocess.run", fake_run)
    rid = uuid4()
    out = maybe_finalize_git_outputs(tmp_path, rid, {}, slice_count=2)
    assert out["branch"] == run_branch_name(rid)
    assert any(c[:3] == ["git", "checkout", "-B"] for c in calls)

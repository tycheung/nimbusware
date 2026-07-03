from __future__ import annotations

import json

from maker.github_workflow_poll import poll_github_workflow_run


def test_poll_github_workflow_run_passed(monkeypatch) -> None:
    payload = [
        {
            "status": "completed",
            "conclusion": "success",
            "url": "https://github.com/acme/app/actions/runs/1",
            "databaseId": 1,
            "workflowName": "Nimbusware CI",
            "headBranch": "nimbusware/run-abc",
        },
    ]

    class _Proc:
        returncode = 0
        stdout = json.dumps(payload)
        stderr = ""

    monkeypatch.setattr("shutil.which", lambda _cmd: "/usr/bin/gh")
    monkeypatch.setattr(
        "maker.github_workflow_poll.subprocess.run",
        lambda *_a, **_k: _Proc(),
    )
    result = poll_github_workflow_run(
        github_repo="acme/app",
        workflow_path=".github/workflows/nimbusware-ci.yaml",
        branch="nimbusware/run-abc",
    )
    assert result["status"] == "passed"
    assert result["run_url"].endswith("/runs/1")


def test_poll_github_workflow_run_skips_without_repo() -> None:
    result = poll_github_workflow_run(github_repo="")
    assert result["status"] == "skipped"

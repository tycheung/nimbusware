from __future__ import annotations

from maker.approval import git_outputs_from_rows


def test_git_outputs_from_finalize_stage() -> None:
    rows = [
        {
            "event_type": "stage.passed",
            "store_seq": 10,
            "payload": {"stage_name": "slice.git_finalize"},
            "metadata": {
                "branch": "nimbusware/run-abc",
                "pr": {"status": "created", "pr_url": "https://github.com/o/r/pull/1"},
            },
        },
    ]
    out = git_outputs_from_rows(rows)
    assert out["branch"] == "nimbusware/run-abc"
    assert out["pr_url"] == "https://github.com/o/r/pull/1"
    assert out["pr_status"] == "created"

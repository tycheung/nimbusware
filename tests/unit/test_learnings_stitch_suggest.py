from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.learnings_stitch_suggest import stitch_suggestion_for_run


def _learn_event(fp: str, seq: int) -> dict:
    return {
        "store_seq": seq,
        "payload": {"stage_name": "diagnose.learn"},
        "metadata": {"diagnose_learn": {"fingerprint": fp}},
    }


def test_stitch_suggestion_when_fingerprint_repeats(tmp_path: Path) -> None:
    run_id = "00000000-0000-4000-8000-000000000099"
    cand_dir = tmp_path / ".nimbusware" / "research" / "catalog_candidates" / run_id
    cand_dir.mkdir(parents=True)
    (cand_dir / "stitch-1.json").write_text(
        json.dumps(
            {
                "candidate_id": "stitch-1",
                "source": "stitch_applied",
                "status": "pending_integrator_review",
                "summary": "Auth module transplant",
            },
        ),
        encoding="utf-8",
    )
    rows = [_learn_event("abc123", 1), _learn_event("abc123", 2)]
    sug = stitch_suggestion_for_run(rows, tmp_path)
    assert sug is not None
    assert sug["candidate_id"] == "stitch-1"
    assert sug["repeat_count"] == 2


def test_no_suggestion_without_repeat() -> None:
    rows = [_learn_event("once", 1)]
    assert stitch_suggestion_for_run(rows, Path("/tmp")) is None

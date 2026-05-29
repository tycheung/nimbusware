from __future__ import annotations

from uuid import uuid4

from agent_core.models import EventType, Verdict
from hermes_memory.chunking import chunks_from_event_rows, run_index_contribution_enabled


def test_run_index_contribution_defaults_true() -> None:
    assert run_index_contribution_enabled({}) is True
    assert run_index_contribution_enabled({"memory": {}}) is True
    assert run_index_contribution_enabled({"memory": {"index_contribution": False}}) is False


def test_chunks_from_finding_and_fail_gate() -> None:
    rid = uuid4()
    finding_id = uuid4()
    rows = [
        {
            "store_seq": 1,
            "run_id": rid,
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {},
            "payload": {},
        },
        {
            "store_seq": 2,
            "run_id": rid,
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {
                "finding_id": str(finding_id),
                "category": "security",
                "severity": "high",
                "source_artifact": "semgrep",
            },
        },
        {
            "store_seq": 3,
            "run_id": rid,
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": "security_scan",
                "verdict": Verdict.PASS.value,
            },
        },
        {
            "store_seq": 4,
            "run_id": rid,
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": "critique",
                "verdict": Verdict.FAIL.value,
                "failing_critics": ["c1"],
            },
        },
    ]
    drafts = chunks_from_event_rows(rows)
    assert len(drafts) == 2
    assert drafts[0].category == "security"
    assert drafts[1].category == "gate"


def test_chunks_skip_run_when_index_contribution_false() -> None:
    rid = uuid4()
    rows = [
        {
            "store_seq": 1,
            "run_id": rid,
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {"memory": {"index_contribution": False}},
            "payload": {},
        },
        {
            "store_seq": 2,
            "run_id": rid,
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {"finding_id": str(uuid4()), "category": "x"},
        },
    ]
    assert chunks_from_event_rows(rows) == []

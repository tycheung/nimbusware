from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType
from agent_core.models.events_payloads import StagePassedPayload
from nimbusware_projections.builders.policy_compare_outcome import (
    build_policy_compare_outcome,
    load_policy_compare_outcome,
    save_policy_compare_outcome,
)


class _MemStore:
    def __init__(self) -> None:
        self._rows: dict[str, list[dict]] = {}

    def list_run_events(self, run_id: str) -> list[dict]:
        return list(self._rows.get(run_id, []))

    def add_gate(self, run_id: str, *, verdict: str, slice_id: str = "slice-1") -> None:
        self._rows.setdefault(run_id, []).append(
            {
                "run_id": run_id,
                "store_seq": len(self._rows[run_id]) + 1,
                "event_type": EventType.STAGE_PASSED.value,
                "payload": StagePassedPayload(stage_name="slice.gate", duration_ms=1).model_dump(),
                "metadata": {"slice_gate_verdict": verdict, "slice_id": slice_id},
            }
        )


def test_policy_compare_outcome_delta(tmp_path: Path) -> None:
    store = _MemStore()
    run_a, run_b = str(uuid4()), str(uuid4())
    store.add_gate(run_a, verdict="FAIL")
    store.add_gate(run_b, verdict="PASS")
    outcome = build_policy_compare_outcome(
        store,
        run_a=run_a,
        run_b=run_b,
        policy_identical=False,
        changed_count=2,
    )
    assert outcome["gate_pass_rate_delta"] == 1.0
    save_policy_compare_outcome(tmp_path, outcome)
    loaded = load_policy_compare_outcome(tmp_path)
    assert loaded is not None
    assert loaded["run_a"] == run_a

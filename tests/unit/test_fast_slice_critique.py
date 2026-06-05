"""fo463: fast_slice severity helpers and workflow parser."""

from __future__ import annotations

from pathlib import Path

from agent_core.models import EventType, Severity
from nimbusware_orchestrator.fast_slice_critique import (
    fast_slice_skips_optional_critique_matrix,
    max_open_finding_severity,
)
from nimbusware_orchestrator.workflow_fast_slice import parse_fast_slice_workflow_block


def test_parse_fast_slice_top_level(tmp_path: Path) -> None:
    wf = tmp_path / "configs" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / "fs.yaml").write_text(
        "version: 1\nfast_slice: true\n",
        encoding="utf-8",
    )
    block = parse_fast_slice_workflow_block(tmp_path, "fs")
    assert block.enabled is True


def test_max_severity_from_findings() -> None:
    events = [
        {
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {"severity": Severity.LOW.value},
        },
        {
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {"severity": Severity.MEDIUM.value},
        },
    ]
    assert max_open_finding_severity(events) == Severity.MEDIUM


def test_skip_when_below_high() -> None:
    assert fast_slice_skips_optional_critique_matrix(Severity.LOW) is True
    assert fast_slice_skips_optional_critique_matrix(Severity.HIGH) is False

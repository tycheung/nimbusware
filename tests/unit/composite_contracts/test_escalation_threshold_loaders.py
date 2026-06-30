from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_stage_failures,
    load_notice_escalate_at_cumulative_findings,
)
from unit.composite_contracts.escalation_loader_contract import (
    assert_positive_int_loader_boundary,
    assert_positive_int_loader_rejects_non_int,
)

_LOADERS = (
    ("auto", load_auto_escalate_after_cumulative_findings, "auto_escalate_after_cumulative_findings"),
    ("notice", load_notice_escalate_at_cumulative_findings, "notice_escalate_at_cumulative_findings"),
    ("stage", load_escalate_after_cumulative_stage_failures, "escalate_after_cumulative_stage_failures"),
    ("gate", load_escalate_after_cumulative_gate_failures, "escalate_after_cumulative_gate_failures"),
)


@pytest.mark.parametrize(("label", "loader", "yaml_key"), _LOADERS)
def test_escalation_positive_int_loader_non_int_and_boundary_matrix(
    tmp_path: Path,
    label: str,
    loader: object,
    yaml_key: str,
) -> None:
    assert_positive_int_loader_rejects_non_int(
        tmp_path,
        loader=loader,  # type: ignore[arg-type]
        yaml_key=yaml_key,
        prefix=label,
    )
    assert_positive_int_loader_boundary(
        tmp_path,
        loader=loader,  # type: ignore[arg-type]
        yaml_key=yaml_key,
        prefix=label,
    )

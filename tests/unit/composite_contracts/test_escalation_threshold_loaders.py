from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.escalation.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_stage_failures,
    load_notice_escalate_at_cumulative_findings,
)
from unit.composite_contracts.escalation_loader_contract import (
    KEY_AUTO,
    KEY_GATE,
    KEY_NOTICE,
    KEY_STAGE,
    assert_bool_yaml_false_rejected_by_all,
    assert_bool_yaml_true_accepted_by_all,
    assert_call_order_idempotent,
    assert_empty_or_missing_key_returns_none,
    assert_loaders_read_distinct_keys,
    assert_policy_absent_returns_none,
    assert_positive_int_loader_boundary,
    assert_positive_int_loader_rejects_non_int,
    assert_quartet_isolation_matrix,
    assert_verification_non_dict_matrix,
    assert_verification_non_dict_returns_none,
)
from unit.composite_repo_fixtures import write_escalation_policy

_LOADERS = (
    ("auto", load_auto_escalate_after_cumulative_findings, KEY_AUTO),
    ("notice", load_notice_escalate_at_cumulative_findings, KEY_NOTICE),
    ("stage", load_escalate_after_cumulative_stage_failures, KEY_STAGE),
    ("gate", load_escalate_after_cumulative_gate_failures, KEY_GATE),
)


@pytest.mark.parametrize(("label", "loader", "yaml_key"), _LOADERS)
def test_escalation_loader_defensive_contract(
    tmp_path: Path,
    label: str,
    loader: object,
    yaml_key: str,
) -> None:
    fn = loader  # type: ignore[assignment]
    assert_policy_absent_returns_none(fn, tmp_path, label)
    if label == "auto":
        assert_verification_non_dict_matrix(tmp_path, loader=fn, prefix=label)
    else:
        sample = "verification: 7\n" if label == "notice" else "verification:\n  - a\n  - b\n"
        assert_verification_non_dict_returns_none(
            tmp_path,
            loader=fn,
            yaml_key=yaml_key,
            prefix=label,
            body=sample,
            label="representative",
        )
    assert_empty_or_missing_key_returns_none(
        tmp_path,
        loader=fn,
        yaml_key=yaml_key,
        prefix=label,
    )
    assert_positive_int_loader_rejects_non_int(
        tmp_path,
        loader=fn,
        yaml_key=yaml_key,
        prefix=label,
    )
    assert_positive_int_loader_boundary(
        tmp_path,
        loader=fn,
        yaml_key=yaml_key,
        prefix=label,
    )


def test_auto_notice_key_divergence(tmp_path: Path) -> None:
    assert_loaders_read_distinct_keys(
        tmp_path,
        key_a=KEY_AUTO,
        loader_a=load_auto_escalate_after_cumulative_findings,
        value_a=10,
        key_b=KEY_NOTICE,
        loader_b=load_notice_escalate_at_cumulative_findings,
        prefix="auto_notice",
    )


def test_stage_gate_key_divergence(tmp_path: Path) -> None:
    assert_loaders_read_distinct_keys(
        tmp_path,
        key_a=KEY_STAGE,
        loader_a=load_escalate_after_cumulative_stage_failures,
        value_a=4,
        key_b=KEY_GATE,
        loader_b=load_escalate_after_cumulative_gate_failures,
        prefix="stage_gate",
    )


def test_escalation_quartet_cross_loader_matrix(tmp_path: Path) -> None:
    assert_quartet_isolation_matrix(
        tmp_path,
        loaders=_LOADERS,
        values=(2, 3, 4, 5),
        prefix="isolation_matrix",
    )
    assert_bool_yaml_true_accepted_by_all(tmp_path, loaders=_LOADERS)
    assert_bool_yaml_false_rejected_by_all(tmp_path, loaders=_LOADERS)
    assert_call_order_idempotent(
        tmp_path,
        loaders=_LOADERS,
        values=(11, 22, 33, 44),
    )

    fault_repo = tmp_path / "fault_isolation"
    fault_repo.mkdir()
    write_escalation_policy(
        fault_repo,
        "version: 1\n"
        "verification:\n"
        f"  {KEY_AUTO}: 2\n"
        f'  {KEY_NOTICE}: "abc"\n'
        f"  {KEY_STAGE}: 4\n"
        f"  {KEY_GATE}: 5\n",
    )
    assert load_notice_escalate_at_cumulative_findings(fault_repo) is None
    assert (
        load_auto_escalate_after_cumulative_findings(fault_repo),
        load_escalate_after_cumulative_stage_failures(fault_repo),
        load_escalate_after_cumulative_gate_failures(fault_repo),
    ) == (2, 4, 5)

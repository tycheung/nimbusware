from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from unit.workflow_explainer_case_runner import load_caption_fn
from unit.workflow_explainer_helpers import escalation_explainer_payload

_FIXTURES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explainers" / "caption_guard_cases.yaml"
)
_RAW: dict[str, Any] = yaml.safe_load(_FIXTURES.read_text(encoding="utf-8"))


def _decode_input(value: Any) -> Any:
    if value == "null":
        return None
    return value


_BAD_CASES = [
    (row["fn"], _decode_input(inp))
    for row in _RAW["bad_payload"]
    for inp in row["inputs"]
]

_LOAD_ERROR_CASES = [(row["fn"], row["payload"]) for row in _RAW["load_error_payload"]]


@pytest.mark.parametrize(("fn_path", "bad_input"), _BAD_CASES)
def test_workflow_explainer_caption_bad_payload_returns_none(
    fn_path: str,
    bad_input: Any,
) -> None:
    fn = load_caption_fn(fn_path)
    assert fn(bad_input) is None


@pytest.mark.parametrize(("fn_path", "payload"), _LOAD_ERROR_CASES)
def test_workflow_explainer_caption_load_error_payload_returns_none(
    fn_path: str,
    payload: dict[str, Any],
) -> None:
    fn = load_caption_fn(fn_path)
    assert fn(payload) is None


@pytest.mark.parametrize("row", _RAW["tmp_path_load_error"])
def test_workflow_explainer_caption_tmp_path_load_error_returns_none(
    row: dict[str, Any],
    tmp_path: Path,
) -> None:
    fn = load_caption_fn(row["fn"])
    if row.get("setup") == "malformed_escalation_policy":
        pl = escalation_explainer_payload(
            tmp_path,
            policy_yaml=": : not yaml\n",
        )
        assert isinstance(pl["escalation_policy_yaml_load_error"], str)
        assert fn(pl) is None

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from unit.workflow_explainer_case_runner import (
    assert_caption_guard_returns_none,
    assert_caption_guard_tmp_path_load_error,
    caption_guard_bad_payload_matrix,
    caption_guard_load_error_matrix,
    load_explainer_cases_yaml,
)

_FIXTURES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explainers" / "caption_guard_cases.yaml"
)
_RAW: dict[str, Any] = load_explainer_cases_yaml(_FIXTURES)

_BAD_CASES = caption_guard_bad_payload_matrix(_RAW)
_LOAD_ERROR_CASES = caption_guard_load_error_matrix(_RAW)
_TMP_PATH_CASES = list(_RAW.get("tmp_path_load_error") or [])


@pytest.mark.parametrize(("fn_path", "bad_input"), _BAD_CASES)
def test_workflow_explainer_caption_bad_payload_returns_none(
    fn_path: str,
    bad_input: Any,
) -> None:
    assert_caption_guard_returns_none(fn_path, bad_input)


@pytest.mark.parametrize(("fn_path", "payload"), _LOAD_ERROR_CASES)
def test_workflow_explainer_caption_load_error_payload_returns_none(
    fn_path: str,
    payload: dict[str, Any],
) -> None:
    assert_caption_guard_returns_none(fn_path, payload)


@pytest.mark.parametrize("row", _TMP_PATH_CASES)
def test_workflow_explainer_caption_tmp_path_load_error_returns_none(
    row: dict[str, Any],
    tmp_path: Path,
) -> None:
    assert_caption_guard_tmp_path_load_error(row, tmp_path)

from __future__ import annotations

from unittest.mock import MagicMock, patch

from console.services import runs as svc


def test_fetch_run_calls_get_json() -> None:
    with patch("console.services.runs.get_json") as get_json:
        get_json.return_value = {"run_id": "r1"}
        out = svc.fetch_run("r1")
    get_json.assert_called_once_with("/runs/r1", timeout=30.0)
    assert out["run_id"] == "r1"


def test_post_retry_calls_post_json() -> None:
    with patch("console.services.runs.post_json") as post_json:
        post_json.return_value = {"ok": True}
        svc.post_retry("abc")
    post_json.assert_called_once_with("/runs/abc/actions/retry", {}, timeout=30.0)


def test_fetch_runs_list_uses_get_response() -> None:
    with patch("console.services.runs.get_response") as get_response:
        get_response.return_value = MagicMock()
        svc.fetch_runs_list(params={"limit": 5})
    get_response.assert_called_once_with("/runs", params={"limit": 5}, timeout=15.0)

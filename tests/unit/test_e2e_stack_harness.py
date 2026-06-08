from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from e2e.harness.stack import stack_http_request


def test_stack_http_request_retries_connect_error() -> None:
    response = MagicMock(spec=httpx.Response)
    with patch(
        "e2e.harness.stack.httpx.request", side_effect=[httpx.ConnectError("refused"), response]
    ) as req:
        with patch("e2e.harness.stack.time.sleep") as sleep:
            out = stack_http_request(
                "GET", "http://127.0.0.1:9/probe", retries=2, retry_delay_sec=0.01
            )
    assert out is response
    assert req.call_count == 2
    sleep.assert_called_once_with(0.01)


def test_stack_http_request_raises_after_retries_exhausted() -> None:
    with patch(
        "e2e.harness.stack.httpx.request",
        side_effect=httpx.ConnectError("refused"),
    ):
        with patch("e2e.harness.stack.time.sleep"):
            with pytest.raises(httpx.ConnectError):
                stack_http_request(
                    "GET", "http://127.0.0.1:9/probe", retries=2, retry_delay_sec=0.01
                )

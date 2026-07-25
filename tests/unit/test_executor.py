from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from executor.egress_bridge import assert_egress_allowed, host_matches_allowlist
from executor.fetch import EgressResponseTooLarge, egress_checked_httpx_get

_STREAM_ACTOR = UUID("11111111-1111-4111-8111-111111111101")


def test_host_suffix_allowlist_raises_after_peel() -> None:
    with pytest.raises(RuntimeError, match="local allowlist removed"):
        host_matches_allowlist("files.pypi.org", [".pypi.org"])


def test_egress_role_gate_raises_after_peel() -> None:
    rid = UUID("11111111-1111-4111-8111-111111111101")
    with pytest.raises(RuntimeError, match="local policy removed"):
        assert_egress_allowed(
            actor_role_id=rid,
            target_host="pypi.org",
            scraper_role_allowlist=[rid],
            domain_allowlist=[".pypi.org"],
        )


def test_egress_checked_stream_rejects_content_length_over_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: {"allowed": True},
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-length": "500"}, content=b"")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(EgressResponseTooLarge):
        egress_checked_httpx_get(
            "https://ok.example.test/p",
            actor_role_id=_STREAM_ACTOR,
            scraper_role_allowlist=[_STREAM_ACTOR],
            domain_allowlist=[".example.test"],
            max_response_bytes=10,
            client=client,
        )


def test_egress_checked_stream_reads_body_within_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: {"allowed": True},
    )
    body = b"hello"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-length": str(len(body))}, content=body)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    r = egress_checked_httpx_get(
        "https://ok.example.test/p",
        actor_role_id=_STREAM_ACTOR,
        scraper_role_allowlist=[_STREAM_ACTOR],
        domain_allowlist=[".example.test"],
        max_response_bytes=100,
        client=client,
    )
    assert r.content == body


def test_egress_checked_stream_rejects_body_over_budget_without_cl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: {"allowed": True},
    )
    big = b"x" * 50

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=big)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(EgressResponseTooLarge):
        egress_checked_httpx_get(
            "https://ok.example.test/p",
            actor_role_id=_STREAM_ACTOR,
            scraper_role_allowlist=[_STREAM_ACTOR],
            domain_allowlist=[".example.test"],
            max_response_bytes=10,
            client=client,
        )

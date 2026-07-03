from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from executor.egress import assert_egress_allowed, host_matches_allowlist
from executor.fetch import EgressResponseTooLarge, egress_checked_httpx_get


def test_host_suffix_allowlist() -> None:
    assert host_matches_allowlist("files.pypi.org", [".pypi.org"])
    assert not host_matches_allowlist("evil.com", [".pypi.org"])


def test_egress_role_gate() -> None:
    rid = UUID("11111111-1111-4111-8111-111111111101")
    assert_egress_allowed(
        actor_role_id=rid,
        target_host="pypi.org",
        scraper_role_allowlist=[rid],
        domain_allowlist=[".pypi.org"],
    )
    with pytest.raises(PermissionError):
        assert_egress_allowed(
            actor_role_id=UUID("22222222-2222-4222-8222-222222222202"),
            target_host="pypi.org",
            scraper_role_allowlist=[rid],
            domain_allowlist=[".pypi.org"],
        )


_STREAM_ACTOR = UUID("11111111-1111-4111-8111-111111111101")


def test_egress_checked_stream_rejects_content_length_over_budget() -> None:
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


def test_egress_checked_stream_reads_body_within_budget() -> None:
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


def test_egress_checked_stream_rejects_body_over_budget_without_cl() -> None:
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

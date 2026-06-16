from __future__ import annotations

from uuid import UUID

import pytest

from nimbusware_executor.egress import assert_egress_allowed, host_matches_allowlist


def test_host_suffix_and_exact() -> None:
    assert host_matches_allowlist("files.pypi.org", [".pypi.org"])
    assert host_matches_allowlist("pypi.org", [".pypi.org"])
    assert not host_matches_allowlist("evil.com", [".pypi.org"])


def test_ip_literal_exact_only() -> None:
    assert host_matches_allowlist("203.0.113.1", ["203.0.113.1"])
    assert not host_matches_allowlist("203.0.113.2", ["203.0.113.1"])


def test_assert_egress_allowed_requires_role_and_host() -> None:
    rid = UUID("00000000-0000-4000-8000-000000000001")
    allow_roles = [rid]
    domains = ["example.com"]
    assert_egress_allowed(
        actor_role_id=rid,
        target_host="example.com",
        scraper_role_allowlist=allow_roles,
        domain_allowlist=domains,
    )
    with pytest.raises(PermissionError, match="not in scraper_role_allowlist"):
        assert_egress_allowed(
            actor_role_id=UUID("00000000-0000-4000-8000-000000000002"),
            target_host="example.com",
            scraper_role_allowlist=allow_roles,
            domain_allowlist=domains,
        )
    with pytest.raises(PermissionError, match="not in domain_allowlist"):
        assert_egress_allowed(
            actor_role_id=rid,
            target_host="other.com",
            scraper_role_allowlist=allow_roles,
            domain_allowlist=domains,
        )

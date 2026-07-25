from __future__ import annotations

from uuid import UUID

import pytest

from executor.egress_bridge import assert_egress_allowed, host_matches_allowlist


def test_host_matches_allowlist_raises_after_peel() -> None:
    with pytest.raises(RuntimeError, match="local allowlist removed"):
        host_matches_allowlist("files.pypi.org", [".pypi.org"])


def test_assert_egress_allowed_raises_after_peel() -> None:
    role = UUID("11111111-1111-4111-8111-111111111101")
    with pytest.raises(RuntimeError, match="local policy removed"):
        assert_egress_allowed(
            actor_role_id=role,
            target_host="example.com",
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
        )

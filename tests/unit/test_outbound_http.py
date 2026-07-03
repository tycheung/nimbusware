from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from agent_core.models import (
    EventType,
    FindingFixStrictnessSettings,
    NetworkEgressPolicySnapshot,
    PolicySnapshotV1,
    RunCreatedEvent,
    RunCreatedPayload,
)
from orchestrator.outbound_http import (
    egress_checked_get_for_run,
    network_egress_from_run_created,
)
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.scraper.stage import ScraperFetchConfig
from store.memory import InMemoryEventStore

# follow-on 65: shared fixtures + helper for NIMBUSWARE_OUTBOUND_FETCH_ENABLED
# string-arm contract tests at both call sites in ``pipeline.py``.

_SITE1_ACTOR_UUID = UUID("11111111-1111-4111-8111-111111111101")
_SITE1_RUN_EGRESS: dict[str, Any] = {
    "network_egress": {
        "scraper_role_allowlist": [str(_SITE1_ACTOR_UUID)],
        "domain_allowlist": [".example.test"],
    },
}
_SITE2_RUN_EGRESS: dict[str, Any] = {
    "network_egress": {
        "scraper_role_allowlist": ["44444444-4444-4444-8444-444444444404"],
        "domain_allowlist": [".example.test"],
    },
}
_SITE2_DEFAULT_CFG = ScraperFetchConfig(
    enabled=True,
    fetch_urls=("https://www.example.test/",),
    actor_role_key="backend_writer",
    max_attempts=1,
    backoff_seconds=0.0,
    max_bytes=None,
    body_snippet_max_bytes=256,
    persist_artifacts_max_bytes_per_url=None,
)


def _outbound_fetch_disabled_event(events: list[dict[str, Any]]) -> bool:
    """Return True iff ``events`` contains the site-2 env-gate ``stage.failed``.

    Factors out the recurring ``stage.failed`` + ``reason_code ==
    "outbound_fetch_disabled"`` presence check used by Parts B and C below.
    Pre-existing tests in this module assert different observables (raises at
    site 1, richer mock-client assertions for the egress permission check)
    and are left untouched.
    """
    return any(
        r["event_type"] == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("reason_code") == "outbound_fetch_disabled"
        for r in events
    )


def _snapshot_with_egress(actor: UUID) -> PolicySnapshotV1:
    return PolicySnapshotV1(
        finding_fix_strictness=FindingFixStrictnessSettings(),
        network_egress=NetworkEgressPolicySnapshot(
            scraper_role_allowlist=[actor],
            domain_allowlist=[".example.test"],
        ),
    )


def test_network_egress_from_run_created() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    actor = UUID("11111111-1111-4111-8111-111111111101")
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
                policy_snapshot=_snapshot_with_egress(actor),
            ),
        ),
    )
    scrapers, domains = network_egress_from_run_created(store, run_id)
    assert scrapers == [actor]
    assert domains == [".example.test"]


def test_egress_checked_get_for_run_uses_mock_client() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    actor = UUID("11111111-1111-4111-8111-111111111101")
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
                policy_snapshot=_snapshot_with_egress(actor),
            ),
        ),
    )
    mock_resp = MagicMock(spec=httpx.Response)
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp
    r = egress_checked_get_for_run(
        store,
        run_id,
        "https://www.example.test/path",
        actor_role_id=actor,
        client=client,
    )
    assert r is mock_resp
    client.get.assert_called_once()


def test_egress_checked_get_wrong_role_raises() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    allowed = UUID("11111111-1111-4111-8111-111111111101")
    other = UUID("22222222-2222-4222-8222-222222222202")
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
                policy_snapshot=_snapshot_with_egress(allowed),
            ),
        ),
    )
    with pytest.raises(PermissionError, match="not in scraper_role_allowlist"):
        egress_checked_get_for_run(
            store,
            run_id,
            "https://www.example.test/",
            actor_role_id=other,
            client=MagicMock(spec=httpx.Client),
        )


def test_orchestrator_egress_fetch_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", raising=False)
    orch, _mem = make_dev_orchestrator()
    rid = orch.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {
                "scraper_role_allowlist": ["11111111-1111-4111-8111-111111111101"],
                "domain_allowlist": [".example.test"],
            },
        },
    )
    with pytest.raises(RuntimeError, match="NIMBUSWARE_OUTBOUND_FETCH_ENABLED"):
        orch.egress_checked_fetch_url(
            rid,
            "https://www.example.test/",
            UUID("11111111-1111-4111-8111-111111111101"),
        )


def test_outbound_fetch_env_force_on_at_egress_checked_fetch_url_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #10 ``NIMBUSWARE_OUTBOUND_FETCH_ENABLED`` force-on contract at site 1.

    :meth:`RunOrchestrator.egress_checked_fetch_url` ([pipeline.py lines
    214-218](packages\\orchestrator\\pipeline.py)) gates the
    outbound GET on ``os.environ.get("NIMBUSWARE_OUTBOUND_FETCH_ENABLED",
    "").lower() not in ("1", "true", "yes")``. Existing
    ``test_orchestrator_egress_fetch_requires_env`` only pins the
    env-absent branch (raises ``RuntimeError``); this test pins the
    accept-side of the **single force-on tuple** across canonical and
    case-folded variants.

    **Whitespace-padded variants are intentionally NOT in this part** — the
    coercion here is plain ``.lower()`` with no ``.strip()`` (unlike the
    fo62/63/64 tri-state envs), so ``" 1 "`` falls into the fail-closed
    branch covered by Part C. This split makes a future "unify env handling
    by adding ``.strip()``" refactor fail loudly in Part C, not silently
    pass here.

    Per-case ``force_on_site1 raw=<raw>`` message identifies the failing
    env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", raw)
        orch, _mem = make_dev_orchestrator()
        rid = orch.create_run("default", run_policy_overrides=_SITE1_RUN_EGRESS)
        mock_resp = MagicMock(spec=httpx.Response)
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = mock_resp
        result = orch.egress_checked_fetch_url(
            rid,
            "https://www.example.test/",
            _SITE1_ACTOR_UUID,
            client=client,
        )
        assert result is mock_resp, f"force_on_site1 raw={raw!r}"
        client.get.assert_called_once()


def test_outbound_fetch_env_force_on_at_scraper_fetch_stage_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #10 ``NIMBUSWARE_OUTBOUND_FETCH_ENABLED`` force-on contract at site 2.

    :meth:`RunOrchestrator.run_optional_scraper_fetch_stage` ([pipeline.py
    lines 379-398](packages\\orchestrator\\pipeline.py))
    uses the **identical** coercion as site 1 to decide whether to emit a
    ``stage.failed`` ``outbound_fetch_disabled`` and return early. This
    test mirrors Part A across the same force-on variants asserting NO
    ``outbound_fetch_disabled`` event surfaces.

    Together with Part A this pins that **both sites share identical
    coercion** — a future refactor that adds ``.strip()`` or changes the
    truthy tuple at only one site would break exactly one of the two
    parts.

    Per-case ``force_on_site2 raw=<raw>`` message identifies the failing
    env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", raw)
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default", run_policy_overrides=_SITE2_RUN_EGRESS)
        with patch(
            "orchestrator._pipeline.pipeline_scraper.load_scraper_fetch_config",
            return_value=_SITE2_DEFAULT_CFG,
        ):
            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.content = b"ok"
            mock_resp.status_code = 200
            mock_resp.headers = httpx.Headers({"content-length": "2"})
            client = MagicMock(spec=httpx.Client)
            client.get.return_value = mock_resp
            orch.run_optional_scraper_fetch_stage(rid, client=client)
        evs = mem.list_run_events(str(rid))
        assert not _outbound_fetch_disabled_event(evs), f"force_on_site2 raw={raw!r}"


def test_outbound_fetch_env_fail_closed_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #10 fail-closed contract at BOTH sites — the asymmetry-rich part.

    The single force-on tuple ``("1", "true", "yes")`` is the **only** way
    to enable outbound fetch — there is no kill-switch tuple, no
    fallthrough to YAML, and **no** ``.strip()``. Every other env value
    fails closed at site 1 (``RuntimeError``) and site 2
    (``outbound_fetch_disabled`` ``stage.failed`` via helper).

    Three sub-contracts pinned simultaneously:

    1. **Single-tuple membership** — ``"0"`` / ``"false"`` / ``"no"`` fall
       through the ``not in`` check just like any other unknown token; no
       separate early-return for falsy values (distinct from the fo62 / 63
       / 64 tri-state envs).
    2. **No ``.strip()``** — whitespace-padded canonical values like
       ``"  1  "`` / ``" true "`` / ``"\\tyes\\n"`` fail closed because the
       lookup is plain ``.lower()`` against the tuple, with no whitespace
       trimming. A refactor that adds ``.strip()`` to "match the other env
       layers" would silently flip ``" 1 "`` from "raise / stage.failed"
       to "enabled", breaking deployments that rely on whitespace as a
       guard. This test fails loudly on exactly that change.
    3. **``"on"`` / ``"off"`` asymmetry** vs the YAML coercer — parallel
       to fo51 / fo62 / fo63 / fo64; the env layer here excludes ``"on"``
       from the force-on tuple even though the workflow YAML coercer
       accepts it.

    Per-case ``fail_closed_site1 raw=<raw>`` / ``fail_closed_site2
    raw=<raw>`` messages identify both the failing site and the offending
    env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("yaml_on_lower", "on"),
        ("yaml_on_upper", "ON"),
        ("falsy_zero", "0"),
        ("falsy_false", "false"),
        ("falsy_no", "no"),
        ("empty", ""),
        ("junk_maybe", "maybe"),
        ("near_miss_true_bang", "true!"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_OUTBOUND_FETCH_ENABLED", raw)
        orch1, _mem1 = make_dev_orchestrator()
        rid1 = orch1.create_run("default", run_policy_overrides=_SITE1_RUN_EGRESS)
        try:
            orch1.egress_checked_fetch_url(
                rid1,
                "https://www.example.test/",
                _SITE1_ACTOR_UUID,
            )
        except RuntimeError as exc:
            assert "NIMBUSWARE_OUTBOUND_FETCH_ENABLED" in str(exc), (
                f"fail_closed_site1 raw={raw!r} wrong message: {exc!s}"
            )
        else:
            pytest.fail(f"fail_closed_site1 raw={raw!r} did not raise")
        orch2, mem2 = make_dev_orchestrator()
        rid2 = orch2.create_run("default", run_policy_overrides=_SITE2_RUN_EGRESS)
        with patch(
            "orchestrator._pipeline.pipeline_scraper.load_scraper_fetch_config",
            return_value=_SITE2_DEFAULT_CFG,
        ):
            orch2.run_optional_scraper_fetch_stage(rid2)
        evs = mem2.list_run_events(str(rid2))
        assert _outbound_fetch_disabled_event(evs), f"fail_closed_site2 raw={raw!r}"

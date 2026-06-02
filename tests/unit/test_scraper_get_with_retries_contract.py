from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from hermes_executor.fetch import EgressResponseTooLarge
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.scraper_stage import ScraperFetchConfig


def _make_cfg(max_attempts: int = 1, backoff_seconds: float = 0.0) -> ScraperFetchConfig:
    """Neutral ScraperFetchConfig varying only retry-cadence fields per axis."""
    return ScraperFetchConfig(
        enabled=True,
        fetch_urls=("https://www.example.test/",),
        actor_role_key="backend_writer",
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        max_bytes=None,
        body_snippet_max_bytes=0,
        persist_artifacts_max_bytes_per_url=None,
    )


def test_scraper_get_with_retries_happy_and_retry_then_succeed_4_axis() -> None:
    """Pin 1-indexed attempt counter + retry-then-succeed + fetch_kw surface.

    A1 -- first attempt succeeds -> (resp, 1).
    A2 -- second attempt succeeds after 1 OSError -> (resp, 2); 1 sleep.
    A3 -- third attempt succeeds after OSError + ValueError -> (resp, 3); 2 sleeps.
    A4 -- fetch_kw kwarg surface: timeout_seconds=30.0 + client + max_response_bytes
          + actor_role_id propagated verbatim to egress_checked_get_for_run.
    """
    resp_mock = MagicMock(spec=httpx.Response)

    orch_a1, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[resp_mock],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_a1,
    ):
        result_a1 = orch_a1._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=1, backoff_seconds=0.5),
            None,
        )
    assert result_a1 == (resp_mock, 1), (
        "A1: first attempt succeeds -> returns (resp, 1); attempt counter is 1-indexed (not 0)"
    )
    assert sleep_a1.call_count == 0, "A1: success on attempt 1 -> no sleep"

    orch_a2, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[OSError("net"), resp_mock],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_a2,
    ):
        result_a2 = orch_a2._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=3, backoff_seconds=0.5),
            None,
        )
    assert result_a2 == (resp_mock, 2), (
        "A2: OSError then success -> (resp, 2); attempt counter advances correctly"
    )
    assert sleep_a2.call_args_list == [((0.5,), {})], (
        "A2: exactly 1 sleep between attempts 1 and 2, with backoff_seconds=0.5"
    )

    orch_a3, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[OSError("a"), ValueError("b"), resp_mock],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_a3,
    ):
        result_a3 = orch_a3._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=5, backoff_seconds=0.5),
            None,
        )
    assert result_a3 == (resp_mock, 3), (
        "A3: 2 retryable failures then success -> (resp, 3); loop terminates on success "
        "even with max_attempts=5 budget remaining"
    )
    assert sleep_a3.call_count == 2, (
        "A3: exactly 2 sleeps (between attempts 1->2 and 2->3); not 3 (no sleep after success)"
    )

    orch_a4, _ = make_dev_orchestrator()
    actor_a4 = uuid4()
    run_id_a4 = uuid4()
    sentinel_client = MagicMock(spec=httpx.Client)
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[resp_mock],
        ) as egress_a4,
        patch("hermes_orchestrator.pipeline.time.sleep"),
    ):
        orch_a4._scraper_get_with_retries(  # noqa: SLF001
            run_id_a4,
            "https://www.example.test/path",
            actor_a4,
            sentinel_client,
            _make_cfg(max_attempts=1),
            4096,
        )
    call_a4 = egress_a4.call_args
    assert call_a4.kwargs == {
        "actor_role_id": actor_a4,
        "timeout_seconds": 30.0,
        "client": sentinel_client,
        "max_response_bytes": 4096,
    }, (
        "A4: fetch_kw keyword surface -- actor_role_id + timeout_seconds=30.0 + client + "
        "max_response_bytes=4096 propagated verbatim to egress_checked_get_for_run"
    )
    assert call_a4.args == (orch_a4._store, run_id_a4, "https://www.example.test/path"), (  # noqa: SLF001
        "A4: positional args -- store, run_id, scraper_url propagated in order"
    )


def test_scraper_get_with_retries_immediate_reraise_taxonomy_4_axis() -> None:
    """Pin PermissionError + EgressResponseTooLarge immediate-reraise.

    Each axis sets backoff_seconds=1.0 so the assertion that time.sleep is
    NOT called proves the reraise bypasses the loop AND the sleep guard
    (the two ``raise`` handlers are evaluated BEFORE the retry-eligible
    tuple, so neither type ever enters ``last_err = exc``).

    B1 -- PermissionError, max_attempts=1.
    B2 -- PermissionError, max_attempts=5 (bypasses 4 remaining attempts).
    B3 -- EgressResponseTooLarge, max_attempts=1.
    B4 -- EgressResponseTooLarge, max_attempts=5 (bypasses 4 remaining attempts).
    """
    orch_b1, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=PermissionError("denied"),
        ) as egress_b1,
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_b1,
        pytest.raises(PermissionError, match="denied"),
    ):
        orch_b1._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=1, backoff_seconds=1.0),
            None,
        )
    assert egress_b1.call_count == 1 and sleep_b1.call_count == 0, (
        "B1: PermissionError with max_attempts=1 -> single call, no sleep"
    )

    orch_b2, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=PermissionError("denied-wide"),
        ) as egress_b2,
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_b2,
        pytest.raises(PermissionError, match="denied-wide"),
    ):
        orch_b2._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=5, backoff_seconds=1.0),
            None,
        )
    assert egress_b2.call_count == 1 and sleep_b2.call_count == 0, (
        "B2: PermissionError with max_attempts=5 still single call, no sleep -- "
        "bypasses retry budget AND backoff cadence"
    )

    orch_b3, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=EgressResponseTooLarge("too big"),
        ) as egress_b3,
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_b3,
        pytest.raises(EgressResponseTooLarge, match="too big"),
    ):
        orch_b3._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=1, backoff_seconds=1.0),
            None,
        )
    assert egress_b3.call_count == 1 and sleep_b3.call_count == 0, (
        "B3: EgressResponseTooLarge with max_attempts=1 -> single call, no sleep"
    )

    orch_b4, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=EgressResponseTooLarge("too big wide"),
        ) as egress_b4,
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_b4,
        pytest.raises(EgressResponseTooLarge, match="too big wide"),
    ):
        orch_b4._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=5, backoff_seconds=1.0),
            None,
        )
    assert egress_b4.call_count == 1 and sleep_b4.call_count == 0, (
        "B4: EgressResponseTooLarge with max_attempts=5 still single call, no sleep -- "
        "bypasses retry budget AND backoff cadence"
    )


def test_scraper_get_with_retries_retry_eligible_exhaustion_5_axis() -> None:
    """Pin the 4 retry-eligible exception types + exhaustion -> RuntimeError.

    Each axis sets max_attempts=2, backoff_seconds=0.0 so the final
    ``raise RuntimeError(str(last_err)[:2000])`` is the only outcome.

    C1 -- OSError all attempts -> RuntimeError("net 2") (last_err wins).
    C2 -- RuntimeError all attempts -> outer RuntimeError wraps inner msg.
    C3 -- ValueError all attempts -> RuntimeError("v 2") (not reraised).
    C4 -- httpx.HTTPError subclasses ConnectError + ReadTimeout -> RuntimeError.
    C5 -- exception identity cross-cut: outer RuntimeError is a FRESH instance,
          not the inner RuntimeError("rt 2") re-raised.
    """
    cfg = _make_cfg(max_attempts=2, backoff_seconds=0.0)

    orch_c1, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[OSError("net 1"), OSError("net 2")],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep"),
        pytest.raises(RuntimeError) as exc_c1,
    ):
        orch_c1._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            cfg,
            None,
        )
    assert str(exc_c1.value) == "net 2", (
        "C1: OSError exhaustion -> RuntimeError uses LAST exception's message (last_err wins)"
    )

    inner_rt = RuntimeError("rt 2")
    orch_c2, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[RuntimeError("rt 1"), inner_rt],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep"),
        pytest.raises(RuntimeError) as exc_c2,
    ):
        orch_c2._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            cfg,
            None,
        )
    assert str(exc_c2.value) == "rt 2", (
        "C2: RuntimeError exhaustion -> outer RuntimeError carries inner's message"
    )
    assert exc_c2.value is not inner_rt, (
        "C5: outer RuntimeError is a FRESH instance, not the inner re-raised (wrap-not-reraise)"
    )

    orch_c3, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[ValueError("v 1"), ValueError("v 2")],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep"),
        pytest.raises(RuntimeError) as exc_c3,
    ):
        orch_c3._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            cfg,
            None,
        )
    assert str(exc_c3.value) == "v 2", (
        "C3: ValueError exhaustion -> RuntimeError (ValueError is retry-eligible, not reraised)"
    )

    orch_c4, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[httpx.ConnectError("c 1"), httpx.ReadTimeout("c 2")],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep"),
        pytest.raises(RuntimeError) as exc_c4,
    ):
        orch_c4._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            cfg,
            None,
        )
    assert str(exc_c4.value) == "c 2", (
        "C4: httpx.ConnectError + httpx.ReadTimeout exhaustion -> RuntimeError; "
        "both httpx.HTTPError subclasses are retry-eligible"
    )


def test_scraper_get_with_retries_backoff_and_truncation_and_fetch_kw_5_axis() -> None:
    """Pin backoff cadence + 2000-char message truncation + fetch_kw matrix.

    D1 -- backoff_seconds=0.0 -> time.sleep NOT called (guard).
    D2 -- backoff_seconds=0.5 with 3 attempts -> sleep called exactly 2x with 0.5.
    D3 -- last-attempt-no-sleep cross-cut: 3 egress calls but only 2 sleeps
          proving ``break`` runs before the sleep guard.
    D4 -- 5000-char OSError message with max_attempts=1 -> RuntimeError msg
          is exactly 2000 chars and equals "x" * 2000.
    D5 -- dual-axis fetch_kw conditional: max_response_bytes=None excludes
          the kwarg vs max_response_bytes=8192 includes it.
    """
    orch_d1, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[OSError("a"), OSError("b"), OSError("c")],
        ) as egress_d1,
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_d1,
        pytest.raises(RuntimeError, match="^c$"),
    ):
        orch_d1._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=3, backoff_seconds=0.0),
            None,
        )
    assert sleep_d1.call_count == 0, (
        "D1: backoff_seconds=0.0 -> time.sleep NEVER called (guard ``> 0`` blocks)"
    )
    assert egress_d1.call_count == 3, (
        "D1 cross-cut: all 3 attempts still exhausted (no sleep != no retry)"
    )

    orch_d23, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[OSError("a"), OSError("b"), OSError("c")],
        ) as egress_d23,
        patch("hermes_orchestrator.pipeline.time.sleep") as sleep_d23,
        pytest.raises(RuntimeError, match="^c$"),
    ):
        orch_d23._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=3, backoff_seconds=0.5),
            None,
        )
    assert sleep_d23.call_args_list == [((0.5,), {}), ((0.5,), {})], (
        "D2: backoff_seconds=0.5 with 3 attempts -> sleep called exactly 2x with 0.5 "
        "(bounded by max_attempts-1)"
    )
    assert egress_d23.call_count == 3 and sleep_d23.call_count == 2, (
        "D3: 3 egress calls but 2 sleeps proves the ``break`` after last attempt runs "
        "BEFORE the sleep guard (no post-exhaustion sleep)"
    )

    orch_d4, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[OSError("x" * 5000)],
        ),
        patch("hermes_orchestrator.pipeline.time.sleep"),
        pytest.raises(RuntimeError) as exc_d4,
    ):
        orch_d4._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=1, backoff_seconds=0.0),
            None,
        )
    assert len(str(exc_d4.value)) == 2000 and str(exc_d4.value) == "x" * 2000, (
        "D4: 5000-char OSError message truncated to exactly 2000 via str(last_err)[:2000]"
    )

    resp_mock = MagicMock(spec=httpx.Response)
    orch_d5a, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[resp_mock],
        ) as egress_d5a,
        patch("hermes_orchestrator.pipeline.time.sleep"),
    ):
        orch_d5a._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=1),
            None,
        )
    assert "max_response_bytes" not in egress_d5a.call_args.kwargs, (
        "D5a: max_response_bytes=None -> kwarg EXCLUDED from fetch_kw (conditional add guard)"
    )

    orch_d5b, _ = make_dev_orchestrator()
    with (
        patch(
            "hermes_orchestrator.pipeline.egress_checked_get_for_run",
            side_effect=[resp_mock],
        ) as egress_d5b,
        patch("hermes_orchestrator.pipeline.time.sleep"),
    ):
        orch_d5b._scraper_get_with_retries(  # noqa: SLF001
            uuid4(),
            "https://www.example.test/",
            uuid4(),
            None,
            _make_cfg(max_attempts=1),
            8192,
        )
    assert egress_d5b.call_args.kwargs.get("max_response_bytes") == 8192, (
        "D5b: max_response_bytes=8192 -> kwarg INCLUDED in fetch_kw with exact value"
    )

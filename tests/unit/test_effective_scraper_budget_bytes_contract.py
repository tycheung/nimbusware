"""_effective_scraper_budget_bytes`` direct contract."""


from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.scraper_stage import ScraperFetchConfig


def _make_cfg(max_bytes: int | None = None) -> ScraperFetchConfig:
    """Neutral ScraperFetchConfig with only ``max_bytes`` variable per axis."""
    return ScraperFetchConfig(
        enabled=False,
        fetch_urls=(),
        actor_role_key="backend_writer",
        max_attempts=1,
        backoff_seconds=0.0,
        max_bytes=max_bytes,
        body_snippet_max_bytes=0,
        persist_artifacts_max_bytes_per_url=None,
    )


def test_effective_scraper_budget_bytes_snapshot_type_guards_4_axis() -> None:
    """Pin the 4 snapshot-side type-guard arms at pipeline.py:342-348.

    In every axis cfg.max_bytes=None so the overall return must be None
    when policy_b stays None (proves all 4 reject arms short-circuit
    policy_b cleanly).

    A1 -- snap not a dict (helper returns int 42 -> isinstance False).
    A2 -- snap dict missing network_egress key (ne = None).
    A3 -- snap['network_egress'] not a dict (string).
    A4 -- network_egress dict missing budget_bytes_per_run (pb = None).
    """
    cfg = _make_cfg(max_bytes=None)

    orch_a1, _ = make_dev_orchestrator()
    with patch.object(orch_a1, "policy_snapshot_for_run", return_value=42):
        result_a1 = orch_a1._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_a1 is None, (
        "A1: snap not a dict must short-circuit ne to None; with cfg.max_bytes=None, "
        "overall return must be None"
    )

    orch_a2, _ = make_dev_orchestrator()
    snap_a2 = {"finding_fix_strictness": {}}
    with patch.object(orch_a2, "policy_snapshot_for_run", return_value=snap_a2):
        result_a2 = orch_a2._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_a2 is None, (
        "A2: snap dict missing network_egress key -> ne = None -> return None"
    )

    orch_a3, _ = make_dev_orchestrator()
    snap_a3 = {"network_egress": "not a dict"}
    with patch.object(orch_a3, "policy_snapshot_for_run", return_value=snap_a3):
        result_a3 = orch_a3._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_a3 is None, (
        "A3: snap['network_egress'] not a dict -> isinstance(ne, dict) False -> return None"
    )

    orch_a4, _ = make_dev_orchestrator()
    snap_a4 = {"network_egress": {"domain_allowlist": []}}
    with patch.object(orch_a4, "policy_snapshot_for_run", return_value=snap_a4):
        result_a4 = orch_a4._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_a4 is None, (
        "A4: network_egress dict missing budget_bytes_per_run -> pb = None -> return None"
    )

    assert cfg.max_bytes is None, (
        "Cross-cut precondition: cfg.max_bytes stayed None across all 4 axes "
        "so the None return is attributable to the snapshot-side guards"
    )


def test_effective_scraper_budget_bytes_value_guard_matrix_5_axis() -> None:
    """Pin the pb value-guard at pipeline.py:347 (isinstance(pb, int) and pb >= 0).

    All axes provide a valid snap dict with valid network_egress dict; only
    budget_bytes_per_run varies. cfg.max_bytes=None so return reflects exactly
    the policy_b decision (None when rejected, value when accepted).

    B1 -- pb None: isinstance(None, int) False -> rejected.
    B2 -- pb string '100': type-strict reject (no coercion).
    B3 -- pb float 100.5: float reject.
    B4 -- pb negative -1: int but pb >= 0 False -> rejected.
    B5 -- pb 0 (boundary inclusive) AND positive 1024 both accepted.
    """
    cfg = _make_cfg(max_bytes=None)

    def _snap_with_pb(pb: object) -> dict[str, object]:
        return {"network_egress": {"budget_bytes_per_run": pb}}

    orch_b1, _ = make_dev_orchestrator()
    with patch.object(orch_b1, "policy_snapshot_for_run", return_value=_snap_with_pb(None)):
        result_b1 = orch_b1._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_b1 is None, "B1: pb=None rejected via isinstance(None, int) False"

    orch_b2, _ = make_dev_orchestrator()
    with patch.object(orch_b2, "policy_snapshot_for_run", return_value=_snap_with_pb("100")):
        result_b2 = orch_b2._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_b2 is None, (
        "B2: pb='100' string rejected (type-strict guard, no implicit coercion)"
    )

    orch_b3, _ = make_dev_orchestrator()
    with patch.object(orch_b3, "policy_snapshot_for_run", return_value=_snap_with_pb(100.5)):
        result_b3 = orch_b3._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_b3 is None, "B3: pb=100.5 float rejected (isinstance False)"

    orch_b4, _ = make_dev_orchestrator()
    with patch.object(orch_b4, "policy_snapshot_for_run", return_value=_snap_with_pb(-1)):
        result_b4 = orch_b4._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_b4 is None, "B4: pb=-1 negative int rejected via pb >= 0 boundary"

    orch_b5a, _ = make_dev_orchestrator()
    with patch.object(orch_b5a, "policy_snapshot_for_run", return_value=_snap_with_pb(0)):
        result_b5a = orch_b5a._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_b5a == 0, (
        "B5a: pb=0 must be ACCEPTED at the >= 0 boundary (inclusive); "
        "result is 0 not None"
    )

    orch_b5b, _ = make_dev_orchestrator()
    with patch.object(orch_b5b, "policy_snapshot_for_run", return_value=_snap_with_pb(1024)):
        result_b5b = orch_b5b._effective_scraper_budget_bytes(uuid4(), cfg)  # noqa: SLF001
    assert result_b5b == 1024, "B5b: pb=1024 positive int accepted (happy path)"


def test_effective_scraper_budget_bytes_min_composition_4_axis() -> None:
    """Pin cap composition + min() ordering at pipeline.py:349-354.

    All axes use a structurally valid snap; only the cap sources vary.

    C1 -- policy only (cfg.max_bytes=None): return policy_b.
    C2 -- cfg only (snap returns no usable policy_b): return cfg.max_bytes.
    C3 -- both with policy stricter: min picks policy.
    C4 -- both with cfg stricter: min order-invariant; picks cfg.
    """
    snap_500 = {"network_egress": {"budget_bytes_per_run": 500}}
    snap_2048 = {"network_egress": {"budget_bytes_per_run": 2048}}

    orch_c1, _ = make_dev_orchestrator()
    with patch.object(orch_c1, "policy_snapshot_for_run", return_value=snap_500):
        result_c1 = orch_c1._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=None),
        )
    assert result_c1 == 500, (
        "C1: policy_b=500, cfg.max_bytes=None -> single-cap policy-only arm returns 500"
    )

    orch_c2, _ = make_dev_orchestrator()
    with patch.object(orch_c2, "policy_snapshot_for_run", return_value={}):
        result_c2 = orch_c2._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=2048),
        )
    assert result_c2 == 2048, (
        "C2: policy absent, cfg.max_bytes=2048 -> single-cap config-only arm returns 2048"
    )

    orch_c3, _ = make_dev_orchestrator()
    with patch.object(orch_c3, "policy_snapshot_for_run", return_value=snap_500):
        result_c3 = orch_c3._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=2048),
        )
    assert result_c3 == 500, (
        "C3: policy_b=500 < cfg.max_bytes=2048 -> min picks the stricter policy"
    )

    orch_c4, _ = make_dev_orchestrator()
    with patch.object(orch_c4, "policy_snapshot_for_run", return_value=snap_2048):
        result_c4 = orch_c4._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=500),
        )
    assert result_c4 == 500, (
        "C4: cfg.max_bytes=500 < policy_b=2048 -> min picks cfg (order-invariant; "
        "stricter cap wins regardless of source)"
    )

    assert result_c3 == result_c4, (
        "C3/C4 cross-cut: both stricter-wins arrangements must yield the same numeric "
        "result, proving min is symmetric over its inputs"
    )


def test_effective_scraper_budget_bytes_empty_caps_and_zero_budget_3_axis() -> None:
    """Pin the ``return min(caps) if caps else None`` edge at pipeline.py:354.

    D1 -- both absent -> caps == [] -> short-circuit to None.
    D2 -- both equal -> min returns that shared value (no surprise ordering).
    D3 -- zero policy_b is a valid deny-all budget (pb=0 admitted; min(0, X) == 0).
    """
    orch_d1, _ = make_dev_orchestrator()
    with patch.object(orch_d1, "policy_snapshot_for_run", return_value={}):
        result_d1 = orch_d1._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=None),
        )
    assert result_d1 is None, (
        "D1: both caps absent -> caps == [] -> short-circuit to None"
    )

    orch_d2, _ = make_dev_orchestrator()
    snap_equal = {"network_egress": {"budget_bytes_per_run": 1024}}
    with patch.object(orch_d2, "policy_snapshot_for_run", return_value=snap_equal):
        result_d2 = orch_d2._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=1024),
        )
    assert result_d2 == 1024, (
        "D2: policy_b == cfg.max_bytes == 1024 -> min returns the shared value"
    )

    orch_d3, _ = make_dev_orchestrator()
    snap_zero = {"network_egress": {"budget_bytes_per_run": 0}}
    with patch.object(orch_d3, "policy_snapshot_for_run", return_value=snap_zero):
        result_d3 = orch_d3._effective_scraper_budget_bytes(  # noqa: SLF001
            uuid4(), _make_cfg(max_bytes=100),
        )
    assert result_d3 == 0, (
        "D3: policy_b=0 admitted by >= 0 boundary AND min(0, 100) == 0 -> "
        "operator can set 0 as a deny-all budget that short-circuits any cfg cap"
    )

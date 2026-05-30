"""RunOrchestrator.create_run`` construction-segment contract."""


from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore

_RUN_CREATED = "run.created"


def _only_run_created_row(mem: InMemoryEventStore) -> dict[str, Any]:
    """Return the single RUN_CREATED row or fail with a clear diagnostic."""
    rows = [r for r in mem._rows if r["event_type"] == _RUN_CREATED]  # noqa: SLF001
    assert len(rows) == 1, f"expected exactly 1 run.created row, got {len(rows)}"
    return rows[0]


def _all_run_created_rows(mem: InMemoryEventStore) -> list[dict[str, Any]]:
    """Return all RUN_CREATED rows in append order."""
    return [r for r in mem._rows if r["event_type"] == _RUN_CREATED]  # noqa: SLF001


def test_create_run_construction_metadata_4_axis_contract() -> None:
    """Pin the RunCreatedEvent.metadata block at pipeline.py:181-190.

    Axis A1 -- ``roles_registry.yaml_version`` equals
    ``orch._registry.yaml_version`` (int from ``RoleRegistry.from_yaml``).
    Axis A2 -- ``roles_registry.content_digest_sha256_16`` is a
    16-hex-char string matching ``orch._registry`` and is identical
    across two orchestrators on the same repo (deterministic
    SHA-256-truncated digest).
    Axis A3 -- ``policy_snapshot.domain_allowlist_normalized`` is
    the literal ``True`` regardless of workflow / overrides
    (pins line 187 hard-coded constant).
    Axis A4 -- ``policy_snapshot.network_egress_domain_count``
    equals ``len(stored domain_allowlist)`` -- 0 for bare
    ``default`` workflow, 2 with a 2-domain override.
    """
    orch_a, mem_a = make_dev_orchestrator()
    orch_a.create_run("default")
    row_a = _only_run_created_row(mem_a)
    md_a = row_a["metadata"]

    expected_version = orch_a._registry.yaml_version  # noqa: SLF001
    assert md_a["roles_registry"]["yaml_version"] == expected_version, (
        f"yaml_version mismatch: stored={md_a['roles_registry']['yaml_version']!r} "
        f"registry={expected_version!r}"
    )

    expected_digest = orch_a._registry.content_digest_sha256_16  # noqa: SLF001
    stored_digest = md_a["roles_registry"]["content_digest_sha256_16"]
    assert stored_digest == expected_digest
    assert isinstance(stored_digest, str) and len(stored_digest) == 16, (
        f"content_digest_sha256_16 must be a 16-char hex string; got {stored_digest!r}"
    )

    orch_b, mem_b = make_dev_orchestrator()
    orch_b.create_run("default")
    row_b = _only_run_created_row(mem_b)
    assert (
        row_b["metadata"]["roles_registry"]["content_digest_sha256_16"] == stored_digest
    ), "deterministic digest broken: two orchestrators on same repo produced different digests"

    assert md_a["policy_snapshot"]["domain_allowlist_normalized"] is True, (
        "domain_allowlist_normalized must be the literal True (line 187)"
    )

    assert md_a["policy_snapshot"]["network_egress_domain_count"] == 0
    payload_a = row_a["payload"]
    stored_domains_a = payload_a["policy_snapshot"]["network_egress"]["domain_allowlist"]
    assert md_a["policy_snapshot"]["network_egress_domain_count"] == len(stored_domains_a)

    orch_c, mem_c = make_dev_orchestrator()
    orch_c.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".example.test", ".pypi.org"]},
        },
    )
    row_c = _only_run_created_row(mem_c)
    md_c = row_c["metadata"]
    stored_domains_c = row_c["payload"]["policy_snapshot"]["network_egress"][
        "domain_allowlist"
    ]
    assert md_c["policy_snapshot"]["network_egress_domain_count"] == 2
    assert md_c["policy_snapshot"]["network_egress_domain_count"] == len(stored_domains_c), (
        f"metadata count {md_c['policy_snapshot']['network_egress_domain_count']} "
        f"must equal len(snapshot.domain_allowlist) {len(stored_domains_c)}"
    )


def test_create_run_construction_payload_4_axis_contract() -> None:
    """Pin the RunCreatedPayload shape at pipeline.py:191-196.

    Axis B1 -- ``payload.workflow_profile`` echoes the input arg
    for both ``default`` and ``agent_evaluator_on``.
    Axis B2 -- ``payload.policy_version`` is the literal ``"1"``
    (pins line 193 hard-coded constant).
    Axis B3 -- ``payload.config_snapshot_id`` is a parseable UUID
    string and two consecutive calls on the same orchestrator
    produce **different** values (proves ``str(uuid4())`` runs
    per-call at line 194).
    Axis B4 -- ``payload.policy_snapshot.network_egress.domain_allowlist``
    reflects the merged + normalized snapshot when overrides
    supply domains (pins the line-170 ``policy_snapshot_from_files``
    -> line-195 ``policy_snapshot=`` propagation).
    """
    orch_default, mem_default = make_dev_orchestrator()
    orch_default.create_run("default")
    payload_default = _only_run_created_row(mem_default)["payload"]
    assert payload_default["workflow_profile"] == "default", (
        f"workflow_profile echo broken for default: got {payload_default['workflow_profile']!r}"
    )

    orch_ae, mem_ae = make_dev_orchestrator()
    orch_ae.create_run("agent_evaluator_on")
    payload_ae = _only_run_created_row(mem_ae)["payload"]
    assert payload_ae["workflow_profile"] == "agent_evaluator_on", (
        f"workflow_profile echo broken for agent_evaluator_on: "
        f"got {payload_ae['workflow_profile']!r}"
    )

    assert payload_default["policy_version"] == "1"
    assert payload_ae["policy_version"] == "1", (
        "policy_version must be the literal '1' regardless of workflow (line 193)"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    orch_b3.create_run("default")
    orch_b3.create_run("default")
    rows_b3 = _all_run_created_rows(mem_b3)
    assert len(rows_b3) == 2
    csi_1 = rows_b3[0]["payload"]["config_snapshot_id"]
    csi_2 = rows_b3[1]["payload"]["config_snapshot_id"]
    UUID(csi_1)
    UUID(csi_2)
    assert csi_1 != csi_2, (
        f"config_snapshot_id must be regenerated per call (str(uuid4()) at line 194); "
        f"got identical values {csi_1!r}"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    orch_b4.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {
                "scraper_role_allowlist": ["11111111-1111-4111-8111-111111111101"],
                "domain_allowlist": [".Example.TEST", ".PyPI.org"],
            },
        },
    )
    payload_b4 = _only_run_created_row(mem_b4)["payload"]
    stored_domains = payload_b4["policy_snapshot"]["network_egress"]["domain_allowlist"]
    assert stored_domains == [".example.test", ".pypi.org"], (
        f"policy_snapshot merge + normalize plumbing broken: "
        f"expected lowercased [.example.test, .pypi.org]; got {stored_domains!r}"
    )


def test_create_run_run_policy_overrides_propagation_and_idempotency_lockout_3_axis_contract() -> (
    None
):
    """Pin the ``run_policy_overrides`` kwarg behaviour + cross-fo85 lockout.

    Axis C1 -- ``None`` vs ``{}`` are equivalent: both skip the
    third merge layer (``if not layer: continue`` in
    ``_merge_*_allowlist``) and produce identical empty
    ``domain_allowlist`` for the bare ``default`` workflow.
    Axis C2 -- non-empty override propagates: stored
    ``policy_snapshot.network_egress.domain_allowlist`` matches
    the override (after normalization) AND
    ``metadata.policy_snapshot.network_egress_domain_count``
    reflects the same count (pins the override -> snapshot ->
    metadata count chain).
    Axis C3 -- **STRONG cross-fo85 pin**: when call 2
    short-circuits via idempotency (same ``correlation_id`` as
    call 1), call-2 overrides are silently dropped. The single
    stored row's ``domain_allowlist`` matches call-1 alpha only;
    call-2 beta never reaches ``policy_snapshot_from_files``
    because line 162-166 short-circuits before line 170. This
    closes the documented fo85 deferral.
    """
    orch_none, mem_none = make_dev_orchestrator()
    orch_none.create_run("default", run_policy_overrides=None)
    row_none = _only_run_created_row(mem_none)
    domains_none = row_none["payload"]["policy_snapshot"]["network_egress"][
        "domain_allowlist"
    ]

    orch_empty, mem_empty = make_dev_orchestrator()
    orch_empty.create_run("default", run_policy_overrides={})
    row_empty = _only_run_created_row(mem_empty)
    domains_empty = row_empty["payload"]["policy_snapshot"]["network_egress"][
        "domain_allowlist"
    ]
    assert domains_none == domains_empty == [], (
        f"None vs empty-dict override should produce identical empty domain_allowlist; "
        f"got None->{domains_none!r} {{}}->{domains_empty!r}"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    orch_c2.create_run(
        "default",
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".example.test", ".pypi.org"]},
        },
    )
    row_c2 = _only_run_created_row(mem_c2)
    stored_c2 = row_c2["payload"]["policy_snapshot"]["network_egress"]["domain_allowlist"]
    count_c2 = row_c2["metadata"]["policy_snapshot"]["network_egress_domain_count"]
    assert stored_c2 == [".example.test", ".pypi.org"], (
        f"non-empty override should propagate to stored snapshot; got {stored_c2!r}"
    )
    assert count_c2 == 2, (
        f"metadata.network_egress_domain_count should track override count; got {count_c2}"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    corr = uuid4()
    r1 = orch_c3.create_run(
        "default",
        correlation_id=corr,
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".alpha.test"]},
        },
    )
    r2 = orch_c3.create_run(
        "default",
        correlation_id=corr,
        run_policy_overrides={
            "network_egress": {"domain_allowlist": [".beta.test"]},
        },
    )
    assert r1 == r2, (
        f"idempotent return broken: same correlation_id {corr} should return same "
        f"run_id; got r1={r1} r2={r2}"
    )
    rows_c3 = _all_run_created_rows(mem_c3)
    assert len(rows_c3) == 1, (
        f"idempotency-lockout broken: expected 1 RUN_CREATED row after 2 calls with "
        f"same correlation_id; got {len(rows_c3)}"
    )
    stored_c3 = rows_c3[0]["payload"]["policy_snapshot"]["network_egress"]["domain_allowlist"]
    assert stored_c3 == [".alpha.test"], (
        f"idempotency-lockout broken: call-2 beta override should be SILENTLY DROPPED "
        f"because line 162-166 short-circuits before line 170 policy_snapshot_from_files; "
        f"expected stored domain_allowlist == ['.alpha.test'] (call-1 alpha only); "
        f"got {stored_c3!r}"
    )
    count_c3 = rows_c3[0]["metadata"]["policy_snapshot"]["network_egress_domain_count"]
    assert count_c3 == 1, (
        f"metadata count must also reflect call-1 alpha only (1), not call-2 beta; "
        f"got {count_c3}"
    )

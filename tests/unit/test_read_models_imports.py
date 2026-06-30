from __future__ import annotations

import nimbusware_api.routes.runs as runs_package
import nimbusware_projections.builders as projections_builders


def test_projection_builders_public_exports_match_runs_package() -> None:
    for name in projections_builders.__all__:
        assert hasattr(projections_builders, name)
        assert hasattr(runs_package, name)


def test_timeline_helpers_importable_from_projections() -> None:
    from nimbusware_api.routes.runs.list_helpers import _decode_run_list_cursor
    from nimbusware_projections.builders.integrator_gate import integrator_gate_timeline_summary
    from nimbusware_projections.builders.universal_critique import universal_critique_timeline_summary

    assert integrator_gate_timeline_summary([]) is None
    assert universal_critique_timeline_summary([]) is None
    assert _decode_run_list_cursor(
        "eyJzIjoxLCJyIjoiMTExMTExMTEtMTExMS00MTExLTgxMTEtMTExMTExMTExMTExIn0"
    ) == (
        1,
        __import__("uuid").UUID("11111111-1111-4111-8111-111111111111"),
    )

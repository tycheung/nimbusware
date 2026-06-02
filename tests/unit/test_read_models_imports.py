"""Read-model module import and runs package shim parity tests."""

from __future__ import annotations

import nimbusware_api.read_models as read_models
import nimbusware_api.routes.runs as runs_package


def test_read_models_public_exports_match_runs_package() -> None:
    for name in read_models.__all__:
        assert hasattr(read_models, name)
        assert hasattr(runs_package, name) or name.startswith("_")


def test_timeline_helpers_importable_from_read_models_submodules() -> None:
    from nimbusware_api.read_models.integrator_gate import integrator_gate_timeline_summary
    from nimbusware_api.read_models.run_list import _decode_run_list_cursor
    from nimbusware_api.read_models.universal_critique import universal_critique_timeline_summary

    assert integrator_gate_timeline_summary([]) is None
    assert universal_critique_timeline_summary([]) is None
    assert _decode_run_list_cursor(
        "eyJzIjoxLCJyIjoiMTExMTExMTEtMTExMS00MTExLTgxMTEtMTExMTExMTExMTExIn0"
    ) == (
        1,
        __import__("uuid").UUID("11111111-1111-4111-8111-111111111111"),
    )

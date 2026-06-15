from __future__ import annotations

from pathlib import Path

from nimbusware_console.explainer_core.payload import payload_mapping, payload_str_field
from nimbusware_console.explainer_core.time import age_seconds_utc
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_true_count,
    universal_critique_top_level_nonempty_count,
    universal_critique_yaml_value_nonempty,
)


def test_payload_mapping_guard() -> None:
    assert payload_mapping({"a": 1}) == {"a": 1}
    assert payload_mapping(None) is None
    assert payload_mapping([]) is None  # type: ignore[arg-type]


def test_payload_str_field() -> None:
    assert payload_str_field({"k": "  x  "}, "k") == "x"
    assert payload_str_field({"k": "   "}, "k") is None
    assert payload_str_field(None, "k") is None


def test_age_seconds_utc_parses_z_suffix() -> None:
    assert age_seconds_utc("2020-01-01T00:00:00Z") is not None


def test_universal_critique_counts() -> None:
    block = {"a": {"enabled": True}, "b": "", "c": {"enabled": False}}
    assert universal_critique_yaml_value_nonempty("x") is True
    assert universal_critique_yaml_value_nonempty("") is False
    assert universal_critique_top_level_nonempty_count(block) == 2
    assert universal_critique_top_level_enabled_true_count(block) == 1


_ALLOWED_EXPLAINER_PACKAGES = frozenset(
    {
        "agent_evaluator_workflow_explainer",
        "escalation_suppress_workflow_explainer",
        "security_scan_metadata_workflow_explainer",
        "self_refinement_workflow_explainer",
        "universal_critique_workflow_explainer",
    }
)


def test_explainer_package_allowlist_frozen() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "nimbusware_console"
    found = {
        p.name for p in root.iterdir() if p.is_dir() and p.name.endswith("_workflow_explainer")
    }
    assert found == _ALLOWED_EXPLAINER_PACKAGES, (
        "New *_workflow_explainer packages require allowlist update (fo714): "
        f"extra={found - _ALLOWED_EXPLAINER_PACKAGES} missing={_ALLOWED_EXPLAINER_PACKAGES - found}"
    )

from __future__ import annotations

from pathlib import Path

from console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    default_operator_metrics,
    metrics_caption,
    metrics_table_rows,
)
from console.explainer_core.payload import payload_mapping, payload_str_field
from console.explainer_core.time import age_seconds_utc
from console.explainer_core.universal_critique_counts import (
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


_ALLOWED_EXPLAINER_SLUGS = frozenset(
    {
        "agent_evaluator",
        "escalation_suppress",
        "integration_adapter_writer",
        "integrator_threshold",
        "security_scan_metadata",
        "self_refinement",
        "universal_critique",
    }
)


def test_metrics_scaffold_field_map() -> None:
    metrics = default_operator_metrics({"enabled": False, "count": 0})
    apply_bool_payload_fields(metrics, {"on": True, "off": False}, (("on", "enabled"),))
    rows = metrics_table_rows(metrics, (("Enabled", "enabled"), ("Count", "count")))
    assert rows[0]["value"] == "true"
    assert metrics_caption("Test: ", ["a", "b"]) == "Test: a, b."


def test_explainer_package_allowlist_frozen() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "console" / "workflow_explainers"
    found = {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")}
    assert found == _ALLOWED_EXPLAINER_SLUGS, (
        "New workflow_explainers/* packages require allowlist update: "
        f"extra={found - _ALLOWED_EXPLAINER_SLUGS} missing={_ALLOWED_EXPLAINER_SLUGS - found}"
    )

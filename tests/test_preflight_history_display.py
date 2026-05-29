"""Tests for `nimbusware_console.preflight_history_display` (fo124).

Covers the three pure functions consumed by the new Streamlit expander:

* `preflight_history_from_timeline` (3 axes): None / non-mapping inputs,
  missing key, non-dict ``preflight`` value, happy path.
* `preflight_history_summary_rows` (3 axes): empty summary returns [], rows
  match declared field order, absent keys are omitted (not rendered as "—").
* `preflight_history_histogram_payload` (4 axes): raw samples win, synthetic
  fallback from ``p95_latency_ms``, None summary returns None, summary with
  no samples and no p95 returns the zeroed empty_histogram().
"""

from __future__ import annotations

import json

from nimbusware_console.preflight_history_display import (
    preflight_history_checks_passed_caption,
    preflight_history_context_tokens_caption,
    preflight_history_event_id_caption,
    preflight_history_export_filename_slug,
    preflight_history_export_json,
    preflight_history_from_timeline,
    preflight_history_histogram_mode_caption,
    preflight_history_histogram_payload,
    preflight_history_latency_samples_table_rows,
    preflight_history_operator_metrics,
    preflight_history_operator_metrics_caption,
    preflight_history_operator_metrics_export_filename_slug,
    preflight_history_operator_metrics_export_json,
    preflight_history_operator_metrics_table_rows,
    preflight_history_operator_metrics_table_rows_csv,
    preflight_history_p95_latency_caption,
    preflight_history_p95_source_caption,
    preflight_history_provider_caption,
    preflight_history_sample_count_caption,
    preflight_history_samples_table_caption,
    preflight_history_summary_rows,
    preflight_history_summary_rows_csv,
    preflight_history_validated_model_caption,
)
from hermes_orchestrator.preflight_histogram import BUCKET_EDGES_MS

# ---------------------------------------------------------------------------
# preflight_history_from_timeline
# ---------------------------------------------------------------------------


def test_from_timeline_none_or_non_mapping_returns_none() -> None:
    assert preflight_history_from_timeline(None) is None
    assert preflight_history_from_timeline("not-a-mapping") is None  # type: ignore[arg-type]
    assert preflight_history_from_timeline([1, 2, 3]) is None  # type: ignore[arg-type]


def test_from_timeline_missing_or_wrongly_typed_key_returns_none() -> None:
    assert preflight_history_from_timeline({}) is None
    # `preflight` field present but not a dict ⇒ ignore
    assert preflight_history_from_timeline({"preflight": "not-a-dict"}) is None
    assert preflight_history_from_timeline({"preflight": [1, 2]}) is None
    assert preflight_history_from_timeline({"preflight": None}) is None


def test_from_timeline_happy_path_returns_inner_dict() -> None:
    inner = {"validated_model_id": "llama3.1:8b", "p95_latency_ms": 135}
    body = {"events": [], "preflight": inner}
    assert preflight_history_from_timeline(body) is inner


# ---------------------------------------------------------------------------
# preflight_history_summary_rows
# ---------------------------------------------------------------------------


def test_summary_rows_empty_summary_returns_empty_list() -> None:
    assert preflight_history_summary_rows(None) == []
    assert preflight_history_summary_rows({}) == []


def test_summary_rows_match_declared_field_order() -> None:
    """Order is critical for operator readability — model id first, occurred_at last."""
    summary = {
        "occurred_at": "2026-05-12T20:00:00+00:00",
        "checks_passed": ["a", "b"],
        "p95_latency_source": "max(...)",
        "preflight_latency_sample_count": 3,
        "p95_latency_ms": 135,
        "context_tokens": 8192,
        "provider": "ollama",
        "validated_model_id": "llama3.1:8b",
        "event_id": "abc-def",
    }
    rows = preflight_history_summary_rows(summary)
    field_names = [r["field"] for r in rows]
    # Declared order: model id, provider, context_tokens, p95, samples_used,
    # p95_source, checks_passed, event_id, occurred_at
    assert field_names == [
        "Validated model id",
        "Provider",
        "Context tokens",
        "p95 latency (ms)",
        "Samples used",
        "p95 source",
        "Checks passed",
        "Event id",
        "Occurred at",
    ]


def test_summary_rows_omits_absent_keys() -> None:
    """Legacy events without health_latency_samples_ms should NOT render an extra row."""
    minimal = {"validated_model_id": "llama3.1:8b", "p95_latency_ms": 100}
    rows = preflight_history_summary_rows(minimal)
    field_names = [r["field"] for r in rows]
    # Only two known keys present ⇒ two rows
    assert field_names == ["Validated model id", "p95 latency (ms)"]


def test_summary_rows_renders_none_values_as_em_dash() -> None:
    """Keys present in summary with None value still render (as '—')."""
    summary = {"validated_model_id": "llama3.1:8b", "p95_latency_source": None}
    rows = preflight_history_summary_rows(summary)
    by_field = {r["field"]: r["value"] for r in rows}
    assert by_field["p95 source"] == "—"


def test_preflight_history_summary_export_helpers() -> None:
    summary = {"validated_model_id": "m1", "p95_latency_ms": 99}
    rows = preflight_history_summary_rows(summary)
    csv_text = preflight_history_summary_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert "m1" in csv_text
    assert json.loads(preflight_history_export_json(summary))["p95_latency_ms"] == 99
    assert preflight_history_summary_rows_csv([]) == ""
    assert json.loads(preflight_history_export_json(None)) == {}
    assert preflight_history_export_filename_slug("Pf@x") == "pf_x"


# ---------------------------------------------------------------------------
# preflight_history_histogram_mode_caption
# ---------------------------------------------------------------------------


def test_histogram_mode_caption_multisample() -> None:
    cap = preflight_history_histogram_mode_caption(
        {
            "health_latency_samples_ms": [100, 200],
            "preflight_latency_sample_count": 2,
        },
    )
    assert cap is not None
    assert "2" in cap
    assert "sample_count=2" in cap


def test_histogram_mode_caption_legacy_p95_fallback() -> None:
    cap = preflight_history_histogram_mode_caption({"p95_latency_ms": 180})
    assert cap is not None
    assert "legacy single-bar" in cap


def test_histogram_mode_caption_none_when_no_histogram_signal() -> None:
    assert preflight_history_histogram_mode_caption(None) is None
    assert preflight_history_histogram_mode_caption({}) is None
    assert (
        preflight_history_histogram_mode_caption({"validated_model_id": "x"}) is None
    )


def test_checks_passed_caption() -> None:
    cap = preflight_history_checks_passed_caption(
        {"checks_passed": ["b_check", "a_check", "a_check"]},
    )
    assert cap is not None
    assert "2)" in cap or "(2)" in cap
    assert "a_check" in cap
    assert preflight_history_checks_passed_caption(None) is None
    assert preflight_history_checks_passed_caption({}) is None
    assert preflight_history_checks_passed_caption({"checks_passed": []}) is None


def test_p95_source_caption() -> None:
    cap = preflight_history_p95_source_caption(
        {"p95_latency_source": "max(health_p95_ms,show_latency_ms)"},
    )
    assert cap is not None
    assert "max(health_p95_ms" in cap
    assert preflight_history_p95_source_caption(None) is None
    assert preflight_history_p95_source_caption({}) is None
    assert preflight_history_p95_source_caption({"p95_latency_source": ""}) is None
    assert preflight_history_p95_source_caption({"p95_latency_source": "   "}) is None


def test_preflight_history_p95_latency_caption() -> None:
    cap = preflight_history_p95_latency_caption({"p95_latency_ms": 250})
    assert cap is not None
    assert "**250**" in cap
    assert preflight_history_p95_latency_caption(None) is None
    assert preflight_history_p95_latency_caption({}) is None
    assert preflight_history_p95_latency_caption({"p95_latency_ms": -1}) is None
    assert preflight_history_p95_latency_caption({"p95_latency_ms": True}) is None


def test_preflight_history_event_id_caption() -> None:
    cap = preflight_history_event_id_caption({"event_id": "evt-abc"})
    assert cap is not None
    assert "evt-abc" in cap
    assert preflight_history_event_id_caption(None) is None
    assert preflight_history_event_id_caption({}) is None
    assert preflight_history_event_id_caption({"event_id": ""}) is None


# ---------------------------------------------------------------------------
# preflight_history_histogram_payload
# ---------------------------------------------------------------------------


def test_histogram_uses_raw_samples_when_present() -> None:
    summary = {
        "p95_latency_ms": 135,
        "health_latency_samples_ms": [120, 130, 140],
    }
    h = preflight_history_histogram_payload(summary)
    assert h is not None
    assert h["count"] == 3
    assert h["samples_ms"] == [120, 130, 140]
    assert h["p95_ms"] == 140  # nearest-rank p95 over n=3 ⇒ s[2]


def test_histogram_falls_back_to_synthetic_single_sample_from_p95() -> None:
    """Legacy event (no raw samples) ⇒ synthetic histogram with one entry."""
    summary = {"p95_latency_ms": 180}
    h = preflight_history_histogram_payload(summary)
    assert h is not None
    assert h["count"] == 1
    assert h["samples_ms"] == [180]
    # 180 falls into (100, 250] bucket
    by_edge = {b["le_ms"]: b["count"] for b in h["buckets"]}
    assert by_edge[250] == 1


def test_histogram_returns_none_for_empty_summary() -> None:
    assert preflight_history_histogram_payload(None) is None
    assert preflight_history_histogram_payload({}) is None


def test_histogram_returns_empty_when_summary_lacks_samples_and_p95() -> None:
    """Operator sees the table but the chart hides (count == 0)."""
    summary = {"validated_model_id": "llama3.1:8b"}
    h = preflight_history_histogram_payload(summary)
    assert h is not None
    assert h["count"] == 0
    # Empty histogram still carries the canonical bucket edges
    assert h["bucket_edges_ms"] == list(BUCKET_EDGES_MS)


def test_histogram_ignores_corrupt_sample_entries() -> None:
    """Defensive: a stray string in samples list must not crash the histogram."""
    summary = {
        "p95_latency_ms": 100,
        "health_latency_samples_ms": [100, "bad", 200, None, True, 300],
    }
    h = preflight_history_histogram_payload(summary)
    assert h is not None
    # bool/None/str filtered; only 100, 200, 300 survive (True is bool, not int)
    assert h["samples_ms"] == [100, 200, 300]
    assert h["count"] == 3


def test_preflight_history_validated_model_caption() -> None:
    cap = preflight_history_validated_model_caption(
        {"validated_model_id": "llama3.1:8b"},
    )
    assert cap is not None
    assert "llama3.1:8b" in cap
    assert preflight_history_validated_model_caption(None) is None
    assert preflight_history_validated_model_caption({}) is None
    assert preflight_history_validated_model_caption(
        {"validated_model_id": "   "},
    ) is None


def test_preflight_history_provider_caption() -> None:
    cap = preflight_history_provider_caption({"provider": "ollama"})
    assert cap is not None
    assert "ollama" in cap
    assert preflight_history_provider_caption(None) is None
    assert preflight_history_provider_caption({}) is None
    assert preflight_history_provider_caption(
        {"provider": "   "},
    ) is None
    assert preflight_history_provider_caption({"provider": 1}) is None


def test_preflight_history_sample_count_caption() -> None:
    cap = preflight_history_sample_count_caption(
        {"preflight_latency_sample_count": 3},
    )
    assert cap is not None
    assert "**3**" in cap
    assert "samples" in cap
    cap_one = preflight_history_sample_count_caption(
        {"preflight_latency_sample_count": 1},
    )
    assert cap_one is not None
    assert "sample" in cap_one
    assert "samples" not in cap_one
    assert preflight_history_sample_count_caption(None) is None
    assert preflight_history_sample_count_caption({}) is None
    assert preflight_history_sample_count_caption(
        {"preflight_latency_sample_count": 0},
    ) is None
    assert preflight_history_sample_count_caption(
        {"preflight_latency_sample_count": True},
    ) is None


def test_preflight_history_context_tokens_caption() -> None:
    cap = preflight_history_context_tokens_caption({"context_tokens": 8192})
    assert cap is not None
    assert "**8192**" in cap
    assert preflight_history_context_tokens_caption(None) is None
    assert preflight_history_context_tokens_caption({}) is None
    assert preflight_history_context_tokens_caption({"context_tokens": 0}) is None
    assert preflight_history_context_tokens_caption({"context_tokens": True}) is None


def test_preflight_history_latency_samples_table_rows_multisample() -> None:
    rows = preflight_history_latency_samples_table_rows(
        {"health_latency_samples_ms": [120, 130, 140]},
    )
    assert len(rows) == 3
    assert rows[0] == {"#": "1", "Latency ms": "120"}
    assert rows[2]["Latency ms"] == "140"


def test_preflight_history_latency_samples_table_rows_legacy_p95_only() -> None:
    assert preflight_history_latency_samples_table_rows({"p95_latency_ms": 100}) == []


def test_preflight_history_latency_samples_table_rows_skips_non_ints() -> None:
    rows = preflight_history_latency_samples_table_rows(
        {"health_latency_samples_ms": [100, "bad", 200, None, True]},
    )
    assert len(rows) == 2
    assert rows[1]["Latency ms"] == "200"


def test_preflight_history_samples_table_caption_thresholds() -> None:
    assert (
        preflight_history_samples_table_caption(
            {"health_latency_samples_ms": [100]},
        )
        is None
    )
    cap = preflight_history_samples_table_caption(
        {"health_latency_samples_ms": [100, 200]},
    )
    assert cap is not None
    assert "2" in cap


def test_preflight_history_operator_metrics_empty() -> None:
    m = preflight_history_operator_metrics(None)
    assert m["has_p95_latency"] is False
    assert m["sample_count"] == 0
    assert preflight_history_operator_metrics_caption(m) is None
    assert preflight_history_operator_metrics_table_rows(m) == []


def test_preflight_history_operator_metrics_multisample_fixture() -> None:
    summary = {
        "p95_latency_ms": 120,
        "preflight_latency_sample_count": 3,
        "checks_passed": ["health", "model"],
        "health_latency_samples_ms": [100, 120, 140],
        "validated_model_id": "llama3.1:8b",
    }
    m = preflight_history_operator_metrics(summary)
    assert m["has_p95_latency"] is True
    assert m["sample_count"] == 3
    assert m["multisample"] is True
    assert m["checks_passed_count"] == 2
    assert m["health_latency_samples_count"] == 3
    assert m["validated_model_present"] is True
    cap = preflight_history_operator_metrics_caption(m)
    assert cap is not None
    assert "multisample" in cap
    rows = preflight_history_operator_metrics_table_rows(m)
    fields = {r["field"] for r in rows}
    assert "Multisample" in fields
    assert "Checks passed count" in fields


def test_preflight_history_operator_metrics_export() -> None:
    summary = {"p95_latency_ms": 100, "preflight_latency_sample_count": 1}
    m = preflight_history_operator_metrics(summary)
    parsed = json.loads(preflight_history_operator_metrics_export_json(m))
    assert parsed["has_p95_latency"] is True
    assert json.loads(preflight_history_operator_metrics_export_json(None)) == {}
    rows = preflight_history_operator_metrics_table_rows(m)
    csv_text = preflight_history_operator_metrics_table_rows_csv(rows)
    assert csv_text.splitlines()[0].startswith("field")
    assert preflight_history_operator_metrics_table_rows_csv([]) == ""
    assert preflight_history_operator_metrics_export_filename_slug("Run@1") == "run_1"

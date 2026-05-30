"""Maker progress projection."""

from __future__ import annotations

from nimbusware_projections.builders.maker_progress import (
    maker_progress_from_events,
    pytest_bullets,
    strip_operator_fields,
)


def test_pytest_bullets_extracts_pass_lines() -> None:
    output = "tests/test_app.py::test_ok PASSED\n==== 1 passed in 0.12s ===="
    bullets = pytest_bullets(output)
    assert any("PASSED" in b for b in bullets)


def test_maker_progress_from_created_run() -> None:
    events = [
        {
            "event_type": "run.created",
            "metadata": {
                "requirements": {"business_prompt": "Inventory tracker"},
                "micro_slice_effective": {"enabled": True},
            },
        },
    ]
    body = maker_progress_from_events(events)
    assert "Inventory tracker" in body["plan_summary"]
    assert body["status"] == "awaiting_plan"
    assert body["current_headline"].startswith("Run created")


def test_maker_progress_slice_pass_sentence() -> None:
    events = [
        {
            "event_type": "run.created",
            "metadata": {
                "requirements": {"business_prompt": "Inventory tracker"},
                "micro_slice_effective": {"enabled": True},
            },
        },
        {
            "event_type": "stage.started",
            "payload": {"stage_name": "slice.plan"},
            "metadata": {
                "slice_plan": True,
                "slice_id": "slice-1",
                "rationale": "Add model",
                "target_paths": ["app.py"],
            },
        },
        {
            "event_type": "stage.passed",
            "payload": {"stage_name": "slice.gate"},
            "metadata": {
                "slice_id": "slice-1",
                "slice_gate_verdict": "PASS",
                "tests_passed": True,
                "slice_context_packet": {
                    "test_output": "tests/test_app.py::test_ok PASSED",
                },
            },
        },
    ]
    body = maker_progress_from_events(events)
    assert body["slices_completed"] == 1
    assert any("tests passed" in s.lower() for s in body["sentences"])
    assert body["slices"][0]["test_summary"]["bullets"]


def test_strip_operator_fields() -> None:
    payload = {"status": "ok", "critic_matrix_live": {}, "sentences": ["hi"]}
    stripped = strip_operator_fields(payload)
    assert "critic_matrix_live" not in stripped
    assert stripped["sentences"] == ["hi"]

"""Console Phase 3 timeline display helpers."""

from __future__ import annotations

from hermes_console.phase3_critique_display import (
    phase3_critique_caption,
    phase3_critique_table_rows,
)


def test_phase3_critique_caption_empty() -> None:
    assert "No Phase 3" in phase3_critique_caption({})


def test_phase3_critique_table_rows() -> None:
    rows = phase3_critique_table_rows(
        {
            "security_critique": {"verdict": "PASS", "failing_critics": []},
        },
    )
    assert len(rows) == 1
    assert rows[0]["Verdict"] == "PASS"

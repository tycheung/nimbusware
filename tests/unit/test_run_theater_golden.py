"""Golden theater projection hash — update GOLDEN_THEATER_HASH when projection changes intentionally."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "theater"
_FIXTURE = _FIXTURE_DIR / "micro_slice_research_stitch.jsonl"
_AGENT_TOOL_FIXTURE = _FIXTURE_DIR / "agent_tool_prune.jsonl"

_spec = importlib.util.spec_from_file_location(
    "canonical_theater_hash",
    _FIXTURE_DIR / "canonical_theater_hash.py",
)
assert _spec and _spec.loader
_canonical = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_canonical)
theater_messages_hash = _canonical.theater_messages_hash

# Regenerate: poetry run python -c "from tests.unit.test_run_theater_golden import _load_rows, theater_messages_hash; print(theater_messages_hash(_load_rows()))"
GOLDEN_THEATER_HASH = "a9981291034dd6136e815405f73a23bf539d3dbfdf0136b09bdabd53ccd500ff"
GOLDEN_AGENT_TOOL_THEATER_HASH = (
    "03ad2c83f8460838703cbb8dc61739e592ad41b66c4abeb2f13f8a17be9c08ef"
)


def _load_rows() -> list[dict]:
    rows: list[dict] = []
    for line in _FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def test_golden_theater_message_hash() -> None:
    digest = theater_messages_hash(_load_rows())
    assert digest == GOLDEN_THEATER_HASH, (
        f"theater hash changed to {digest}; update GOLDEN_THEATER_HASH if intentional"
    )


def _load_agent_tool_rows() -> list[dict]:
    rows: list[dict] = []
    for line in _AGENT_TOOL_FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def test_golden_agent_tool_theater_hash() -> None:
    digest = theater_messages_hash(_load_agent_tool_rows())
    assert digest == GOLDEN_AGENT_TOOL_THEATER_HASH, (
        f"agent_tool theater hash changed to {digest}; "
        "update GOLDEN_AGENT_TOOL_THEATER_HASH if intentional"
    )

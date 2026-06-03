from __future__ import annotations

from nimbusware_maker.services.progress_stream import _parse_sse_chunk


def test_parse_sse_progress_event() -> None:
    text = 'event: progress\ndata: {"status": "in_progress", "current_headline": "Planning"}\n\n'
    parsed = _parse_sse_chunk(text)
    assert parsed["progress"]["status"] == "in_progress"

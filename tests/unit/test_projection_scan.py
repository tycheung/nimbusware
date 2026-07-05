from __future__ import annotations

from projections.scan import collect_stage_metadata, latest_stage_metadata, metadata_chain


def test_latest_stage_metadata_returns_last_match() -> None:
    events = [
        {"payload": {"stage_name": "slice.verify"}, "metadata": {"a": 1}},
        {"payload": {"stage_name": "slice.verify"}, "metadata": {"b": 2}},
    ]
    assert latest_stage_metadata(events, "slice.verify") == {"b": 2}


def test_collect_stage_metadata_all_matches() -> None:
    events = [
        {"payload": {"stage_name": "x"}, "metadata": {"n": 1}},
        {"payload": {"stage_name": "y"}, "metadata": {"n": 2}},
        {"payload": {"stage_name": "x"}, "metadata": {"n": 3}},
    ]
    assert collect_stage_metadata(events, "x") == [{"n": 1}, {"n": 3}]


def test_metadata_chain_merges_from_reversed_scan() -> None:
    events = [
        {"metadata": {"enforcement": {"level": 5}}},
        {"metadata": {"standards": {"facade_id": "python-fastapi"}}},
    ]
    merged = metadata_chain(events, "enforcement", "standards")
    assert merged == {"level": 5, "facade_id": "python-fastapi"}

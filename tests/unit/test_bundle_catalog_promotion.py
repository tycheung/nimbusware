from __future__ import annotations

import json
from pathlib import Path

from hermes_research.bundle_promotion import (
    candidate_to_bundle_entry,
    load_catalog_candidate,
    mark_catalog_candidate_promoted,
    write_catalog_candidate,
)


def test_candidate_to_bundle_entry() -> None:
    entry = candidate_to_bundle_entry(
        {
            "candidate_id": "oss-auth",
            "title": "OSS Auth",
            "tags": ["auth"],
        },
    )
    assert entry["id"] == "oss-auth"
    assert entry["title"] == "OSS Auth"
    assert entry["tags"] == ["auth"]


def test_promote_candidate_mark_status(tmp_path: Path) -> None:
    from uuid import uuid4

    run_id = uuid4()
    write_catalog_candidate(
        tmp_path,
        run_id=run_id,
        candidate_id="c1",
        bundle_hints={"title": "Demo", "tags": ["demo"]},
    )
    loaded = load_catalog_candidate(tmp_path, run_id=str(run_id), candidate_id="c1")
    assert loaded["candidate_id"] == "c1"
    mark_catalog_candidate_promoted(tmp_path, run_id=str(run_id), candidate_id="c1")
    again = json.loads(
        (
            tmp_path / ".hermes" / "research" / "catalog_candidates" / str(run_id) / "c1.json"
        ).read_text(encoding="utf-8"),
    )
    assert again["status"] == "promoted"

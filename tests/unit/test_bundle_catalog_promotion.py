from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from hermes_research.bundle_promotion import list_catalog_candidates, write_catalog_candidate


def test_list_catalog_candidates_reads_pending_files(tmp_path: Path) -> None:
    rid = uuid4()
    write_catalog_candidate(
        tmp_path,
        run_id=rid,
        candidate_id="pat-1",
        bundle_hints={"repo_url": "https://example.com/a"},
    )
    rows = list_catalog_candidates(tmp_path, limit=10)
    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "pat-1"
    assert rows[0]["status"] == "pending_integrator_review"
    assert rows[0]["run_id"] == str(rid)


def test_list_catalog_candidates_empty_when_missing(tmp_path: Path) -> None:
    assert list_catalog_candidates(tmp_path) == []

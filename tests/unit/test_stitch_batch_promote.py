from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from research.bundle_promotion import (
    list_pending_stitch_catalog_candidates,
    write_catalog_candidate,
    write_stitch_catalog_candidate,
)


def test_list_pending_stitch_catalog_candidates_filters_source(tmp_path: Path) -> None:
    run_id = uuid4()
    write_stitch_catalog_candidate(
        tmp_path,
        run_id=run_id,
        manifest_id="manifest-1",
        files_added=["packages/stub/__init__.py"],
    )
    write_catalog_candidate(
        tmp_path,
        run_id=run_id,
        candidate_id="research-only",
        bundle_hints={"title": "Research", "tags": ["research"], "source": "research_pattern"},
    )
    pending = list_pending_stitch_catalog_candidates(tmp_path)
    assert len(pending) == 1
    assert pending[0]["source"] == "stitch_applied"
    assert pending[0]["status"] == "pending_integrator_review"

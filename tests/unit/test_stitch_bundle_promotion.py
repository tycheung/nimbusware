from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from nimbusware_research.bundle_promotion import (
    load_catalog_candidate,
    write_stitch_catalog_candidate,
)


def test_write_stitch_catalog_candidate_on_disk(tmp_path: Path) -> None:
    run_id = uuid4()
    out = write_stitch_catalog_candidate(
        tmp_path,
        run_id=run_id,
        manifest_id="manifest-abc-123",
        files_added=["packages/stub_transplant/__init__.py"],
        bundle_hints={"title": "Auth transplant", "tags": ["auth", "stitch"]},
    )
    loaded = load_catalog_candidate(
        tmp_path,
        run_id=str(run_id),
        candidate_id=out["candidate_id"],
    )
    assert loaded["source"] == "stitch_applied"
    assert loaded["manifest_id"] == "manifest-abc-123"
    assert loaded["status"] == "pending_integrator_review"
    assert loaded["title"] == "Auth transplant"
    assert "stitch" in loaded["tags"]

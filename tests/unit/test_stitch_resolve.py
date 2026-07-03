from __future__ import annotations

from pathlib import Path

from research.stages_stitch import resolve_stitch_manifest


def test_resolve_stitch_manifest_empty_without_catalog(tmp_path: Path) -> None:
    manifest, wiring, write_catalog = resolve_stitch_manifest(tmp_path, [])
    assert manifest is None
    assert wiring is None
    assert write_catalog is True

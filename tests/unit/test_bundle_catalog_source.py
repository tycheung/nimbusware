from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from nimbusware_api.routes.bundles import get_bundle_catalog_source


def test_bundle_catalog_source_yaml(tmp_path: Path) -> None:
    orch = MagicMock()
    orch.repo_root = tmp_path
    orch.config_materializer = None
    body = get_bundle_catalog_source(orch)
    assert body["authoritative"] == "yaml"
    assert "catalog.yaml" in body["path"]


def test_bundle_catalog_source_postgres(tmp_path: Path) -> None:
    orch = MagicMock()
    orch.repo_root = tmp_path
    mat = MagicMock()
    mat.use_db = True
    orch.config_materializer = mat
    body = get_bundle_catalog_source(orch)
    assert body["authoritative"] == "postgres"

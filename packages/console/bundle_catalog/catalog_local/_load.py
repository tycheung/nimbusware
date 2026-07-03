from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from extensions.catalog import load_bundle_catalog_content


def catalog_yaml_path(repo_root: Path) -> Path:
    from console.bundle_catalog.catalog_local._constants import (
        _LOCAL_CATALOG_RELPATH,
    )

    return repo_root / _LOCAL_CATALOG_RELPATH


def load_catalog_doc(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    if config_materializer is None:
        from console.config_materializer import console_config_materializer

        config_materializer = console_config_materializer(repo_root)
    try:
        raw = load_bundle_catalog_content(repo_root, config_materializer=config_materializer)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return raw if isinstance(raw, dict) else None


def catalog_bundle_rows(doc: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return []
    return [b for b in bundles if isinstance(b, dict)]

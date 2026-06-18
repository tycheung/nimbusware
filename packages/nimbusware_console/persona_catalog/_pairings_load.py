from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CRITIQUE_PAIRINGS_RELPATH = "configs/personas/critique_pairings.yaml"


def critique_pairings_yaml_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "personas" / "critique_pairings.yaml"


def load_critique_pairings_doc(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    if config_materializer is None:
        from nimbusware_console.config_materializer import console_config_materializer

        config_materializer = console_config_materializer(repo_root)
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            raw = config_materializer.get_critique_pairings()
        except (AttributeError, KeyError):
            return None
        return raw if isinstance(raw, dict) else None
    path = critique_pairings_yaml_path(repo_root)
    if not path.is_file():
        return None
    from nimbusware_orchestrator.merge import load_yaml

    try:
        raw = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return raw if isinstance(raw, dict) else None

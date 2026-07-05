from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root
from standards.profile import (
    facade_stream_ids,
    read_workspace_standards_overlay,
    streams_for_enforcement_level,
)
from standards.registry import load_facade_manifest


def _config_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "standards" / "preset_defaults.yaml"


@lru_cache(maxsize=1)
def load_preset_defaults_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _language_meta(language: str) -> dict[str, Any]:
    langs = load_preset_defaults_config().get("languages")
    if not isinstance(langs, dict):
        return {}
    block = langs.get(language)
    return block if isinstance(block, dict) else {}


def infer_facade_from_workspace(workspace: Path | None) -> str | None:
    if workspace is None or not workspace.is_dir():
        return None
    overlay = read_workspace_standards_overlay(workspace)
    facade_raw = overlay.get("facade_id")
    if isinstance(facade_raw, str) and facade_raw.strip():
        return facade_raw.strip()
    if (workspace / "go.mod").is_file():
        return "go-service"
    if (workspace / "package.json").is_file() and not (workspace / "pyproject.toml").is_file():
        return "typescript-react"
    if (workspace / "pyproject.toml").is_file() or (workspace / "requirements.txt").is_file():
        return "python-fastapi"
    return None


def facade_language(facade_id: str, *, repo_root: Path | None = None) -> str | None:
    cfg = load_preset_defaults_config()
    facades = cfg.get("facades")
    if isinstance(facades, dict):
        entry = facades.get(facade_id)
        if isinstance(entry, dict):
            lang = str(entry.get("language") or "").strip()
            if lang:
                return lang
    manifest = load_facade_manifest(facade_id)
    if manifest is None:
        return None
    stacks = manifest.get("stacks")
    if not isinstance(stacks, list):
        return None
    stack_set = {str(s).lower() for s in stacks}
    if "go" in stack_set:
        return "go"
    if "node" in stack_set and "python" not in stack_set:
        return "typescript"
    if "python" in stack_set:
        return "python"
    if "rust" in stack_set:
        return "rust"
    return None


def _rule_applies(
    rule: dict[str, Any],
    *,
    language: str,
    enforcement_level: int,
    memory_safe: bool,
) -> bool:
    min_level = int(rule.get("min_level") or 0)
    if enforcement_level < min_level:
        return False
    langs = rule.get("languages")
    if isinstance(langs, list) and language not in [str(x) for x in langs]:
        return False
    if rule.get("skip_if_memory_safe") and memory_safe:
        return False
    return True


def default_bundle_ids_for_preset(
    facade_id: str,
    enforcement_level: int,
    *,
    repo_root: Path | None = None,
) -> tuple[str, ...]:
    language = facade_language(facade_id, repo_root=repo_root)
    if not language:
        return ()
    level = max(0, min(10, enforcement_level))
    if level <= 0:
        return ()
    meta = _language_meta(language)
    memory_safe = bool(meta.get("memory_safe"))
    cfg = load_preset_defaults_config()
    bundle_rules = cfg.get("bundle_rules")
    if not isinstance(bundle_rules, dict):
        return ()
    selected: list[str] = []
    for bundle_id, rule in bundle_rules.items():
        if not isinstance(rule, dict):
            continue
        if _rule_applies(rule, language=language, enforcement_level=level, memory_safe=memory_safe):
            selected.append(str(bundle_id))
    facades = cfg.get("facades")
    if isinstance(facades, dict):
        entry = facades.get(facade_id)
        if isinstance(entry, dict):
            extra = entry.get("extra_bundles")
            if isinstance(extra, list):
                for bundle_id in extra:
                    bid = str(bundle_id)
                    rule = bundle_rules.get(bid)
                    if isinstance(rule, dict) and _rule_applies(
                        rule,
                        language=language,
                        enforcement_level=level,
                        memory_safe=memory_safe,
                    ):
                        selected.append(bid)
    return tuple(dict.fromkeys(selected))


def default_connector_ids_for_preset(
    facade_id: str,
    enforcement_level: int,
    *,
    repo_root: Path | None = None,
) -> tuple[str, ...]:
    language = facade_language(facade_id, repo_root=repo_root)
    if not language:
        return ()
    level = max(0, min(10, enforcement_level))
    meta = _language_meta(language)
    memory_safe = bool(meta.get("memory_safe"))
    cfg = load_preset_defaults_config()
    connector_rules = cfg.get("connector_rules")
    if not isinstance(connector_rules, dict):
        return ()
    selected: list[str] = []
    for connector_id, rule in connector_rules.items():
        if not isinstance(rule, dict):
            continue
        if _rule_applies(rule, language=language, enforcement_level=level, memory_safe=memory_safe):
            selected.append(str(connector_id))
    return tuple(dict.fromkeys(selected))


def default_stream_ids_for_preset(
    facade_id: str,
    enforcement_level: int,
) -> tuple[str, ...]:
    manifest = load_facade_manifest(facade_id)
    facade_streams = set(facade_stream_ids(facade_id)) if manifest else set()
    level_streams = set(streams_for_enforcement_level(enforcement_level))
    if facade_streams:
        return tuple(sorted(facade_streams & level_streams))
    return streams_for_enforcement_level(enforcement_level)


def workspace_standards_is_custom(workspace: Path | None) -> bool:
    if workspace is None:
        return False
    overlay = read_workspace_standards_overlay(workspace)
    if not overlay:
        return False
    if overlay.get("custom") is True:
        return True
    if overlay.get("bundles"):
        return True
    if overlay.get("connectors"):
        return True
    if overlay.get("verdict_overrides"):
        return True
    return False


def preset_defaults_summary(
    facade_id: str,
    enforcement_level: int,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    language = facade_language(facade_id, repo_root=repo_root)
    meta = _language_meta(language or "")
    return {
        "facade_id": facade_id,
        "enforcement_level": max(0, min(10, enforcement_level)),
        "language": language,
        "memory_safe": bool(meta.get("memory_safe")) if language else None,
        "bundle_ids": list(
            default_bundle_ids_for_preset(
                facade_id,
                enforcement_level,
                repo_root=repo_root,
            ),
        ),
        "connector_ids": list(
            default_connector_ids_for_preset(
                facade_id,
                enforcement_level,
                repo_root=repo_root,
            ),
        ),
        "stream_ids": list(default_stream_ids_for_preset(facade_id, enforcement_level)),
    }

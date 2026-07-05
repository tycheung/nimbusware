from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from standards.registry import load_facade_manifest
from standards.verdict import VerdictMode


@dataclass(frozen=True)
class StandardsProfile:
    profile_id: str
    facade_id: str | None = None
    bundle_ids: tuple[str, ...] = ()
    connector_ids: tuple[str, ...] = ()
    stream_ids: tuple[str, ...] = ()
    verdict_overrides: dict[str, VerdictMode] = field(default_factory=dict)
    custom: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "facade_id": self.facade_id,
            "bundle_ids": list(self.bundle_ids),
            "connector_ids": list(self.connector_ids),
            "stream_ids": list(self.stream_ids),
            "verdict_overrides": dict(self.verdict_overrides),
            "custom": self.custom,
        }


def standards_platform_enabled() -> bool:
    from env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_STANDARDS_PLATFORM", default=True)


def facade_bundle_ids(facade_id: str) -> list[str]:
    manifest = load_facade_manifest(facade_id)
    if manifest is None:
        return []
    bundles = manifest.get("bundles")
    if not isinstance(bundles, list):
        return []
    return [str(b) for b in bundles]


def facade_stream_ids(facade_id: str) -> list[str]:
    manifest = load_facade_manifest(facade_id)
    if manifest is None:
        return []
    streams = manifest.get("streams")
    if not isinstance(streams, dict):
        return []
    return [str(k) for k, v in streams.items() if isinstance(v, dict) and v.get("enabled", True)]


def read_workspace_standards_overlay(workspace: Path) -> dict[str, Any]:
    path = workspace / ".nimbusware" / "standards.yaml"
    if not path.is_file():
        return {}
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def resolve_standards_profile(
    *,
    workspace: Path | None = None,
    facade_id: str | None = None,
    profile_id: str = "default",
    enforcement_level: int | None = None,
    user_profile_id: str | None = None,
    repo_root: Path | None = None,
) -> StandardsProfile:
    from standards.preset_defaults import (
        default_bundle_ids_for_preset,
        default_connector_ids_for_preset,
        default_stream_ids_for_preset,
        infer_facade_from_workspace,
        workspace_standards_is_custom,
    )

    if user_profile_id and str(user_profile_id).strip():
        from standards.user_profiles import resolve_user_standards_profile

        user_resolved = resolve_user_standards_profile(
            str(user_profile_id).strip(),
            repo_root=repo_root,
        )
        if user_resolved is not None:
            return StandardsProfile(
                profile_id=user_resolved.profile_id,
                facade_id=user_resolved.facade_id,
                bundle_ids=user_resolved.bundle_ids,
                connector_ids=user_resolved.connector_ids,
                stream_ids=user_resolved.stream_ids,
                verdict_overrides=user_resolved.verdict_overrides,
                custom=True,
            )

    overlay: dict[str, Any] = {}
    if workspace is not None:
        overlay = read_workspace_standards_overlay(workspace)
    overlay_custom = overlay.get("custom") is True or workspace_standards_is_custom(workspace)
    effective_facade = str(overlay.get("facade_id") or facade_id or "").strip() or None
    if effective_facade is None and workspace is not None:
        effective_facade = infer_facade_from_workspace(workspace)

    if overlay_custom:
        extra = overlay.get("bundles")
        if isinstance(extra, list) and extra:
            bundles = [str(b) for b in extra]
        else:
            bundles = facade_bundle_ids(effective_facade) if effective_facade else []
        streams = facade_stream_ids(effective_facade) if effective_facade else []
        overrides_raw = overlay.get("verdict_overrides")
        overrides: dict[str, VerdictMode] = {}
        if isinstance(overrides_raw, dict):
            for k, v in overrides_raw.items():
                if v in ("skip", "warn", "critique", "hard_gate"):
                    overrides[str(k)] = v
        connectors_raw = overlay.get("connectors")
        connectors: list[str] = []
        if isinstance(connectors_raw, list):
            connectors = [str(c) for c in connectors_raw]
        return StandardsProfile(
            profile_id=profile_id,
            facade_id=effective_facade,
            bundle_ids=tuple(bundles),
            connector_ids=tuple(connectors),
            stream_ids=tuple(streams),
            verdict_overrides=overrides,
            custom=True,
        )

    level = 5 if enforcement_level is None else max(0, min(10, enforcement_level))
    if effective_facade:
        bundles = list(
            default_bundle_ids_for_preset(
                effective_facade,
                level,
                repo_root=repo_root,
            ),
        )
        connectors = list(
            default_connector_ids_for_preset(
                effective_facade,
                level,
                repo_root=repo_root,
            ),
        )
        streams = list(default_stream_ids_for_preset(effective_facade, level))
    else:
        bundles = []
        connectors = []
        streams = list(streams_for_enforcement_level(level))
    return StandardsProfile(
        profile_id=profile_id,
        facade_id=effective_facade,
        bundle_ids=tuple(bundles),
        connector_ids=tuple(connectors),
        stream_ids=tuple(streams),
        verdict_overrides={},
        custom=False,
    )


def streams_for_enforcement_level(level: int) -> tuple[str, ...]:
    if level <= 0:
        return ()
    if level <= 2:
        return ("lint",)
    if level <= 3:
        return ("lint", "test")
    if level <= 4:
        return ("lint", "test")
    if level <= 6:
        return ("lint", "test", "security", "performance")
    if level <= 9:
        return ("lint", "types", "test", "security", "hygiene", "complexity", "performance")
    return (
        "lint",
        "types",
        "test",
        "security",
        "hygiene",
        "architecture",
        "complexity",
        "performance",
        "standards",
    )

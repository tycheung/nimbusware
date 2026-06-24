from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.mapping import mapping_or_empty
from nimbusware_config.workflow_read import load_yaml, workflow_profile_path
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_core.repo_yaml import relative_under

_LOAD_ERRORS = (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError)


def workflow_profile_expected_path(repo_root: Path, profile: str) -> Path:
    key = profile.strip()
    return repo_root / "configs" / "workflows" / f"{key}.yaml"


def workflow_profile_disk_snapshot(
    repo_root: Path,
    profile: str,
) -> tuple[dict[str, Any], Path, int | None]:
    wp = workflow_profile_path(repo_root, profile)
    file_bytes: int | None = None
    try:
        file_bytes = int(wp.stat().st_size)
    except OSError:
        file_bytes = None
    return load_yaml(wp), wp, file_bytes


def load_workflow_profile_documents(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None,
) -> tuple[dict[str, Any], dict[str, Any], Path, int | None]:
    wp = workflow_profile_expected_path(repo_root, profile)
    use_db = materializer is not None and getattr(materializer, "use_db", False)

    if use_db:
        assert materializer is not None
        effective_doc = materializer.get_workflow_profile_dict(profile)
        if wp.is_file():
            disk_doc, _, file_bytes = workflow_profile_disk_snapshot(repo_root, profile)
        else:
            disk_doc = effective_doc
            file_bytes = None
        return disk_doc, effective_doc, wp, file_bytes

    disk_doc, wp, file_bytes = workflow_profile_disk_snapshot(repo_root, profile)
    return disk_doc, disk_doc, wp, file_bytes


@dataclass(frozen=True)
class WorkflowDiskSnapshot:
    workflow_profile: str | None
    materializer: Any
    disk_doc: dict[str, Any]
    workflow_yaml_relpath: str | None
    file_bytes: int | None
    load_error: str | None
    version_int: int | None


def select_workflow_profile(workflow_profile: str | None) -> str | None:
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    return wf_key if wf_key else None


def load_workflow_disk_snapshot(
    repo_root: Path,
    workflow_profile: str | None,
) -> WorkflowDiskSnapshot:
    wf_sel = select_workflow_profile(workflow_profile)
    mat = console_config_materializer(repo_root)
    disk_doc: dict[str, Any] = {}
    relpath: str | None = None
    file_bytes: int | None = None
    load_error: str | None = None
    version_int: int | None = None
    if wf_sel:
        try:
            raw, _eff, wp, fb = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            disk_doc = mapping_or_empty(raw)
            relpath = relative_under(repo_root, wp)
            file_bytes = fb
            vtop = disk_doc.get("version")
            if type(vtop) is int and not isinstance(vtop, bool):
                version_int = vtop
        except _LOAD_ERRORS as err:
            load_error = str(err)
    return WorkflowDiskSnapshot(
        workflow_profile=wf_sel,
        materializer=mat,
        disk_doc=disk_doc,
        workflow_yaml_relpath=relpath,
        file_bytes=file_bytes,
        load_error=load_error,
        version_int=version_int,
    )


def yaml_section(doc: dict[str, Any], key: str) -> dict[str, Any]:
    return mapping_or_empty(doc.get(key))

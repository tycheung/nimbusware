"""Thin mesh workspace merge (`sak417-c` / `sak432-c`).

Legacy under ``=0``. Non-absorb paths refuse when COMPUTE enabled (``=1|2``).
Absorb helpers remain allowed under ``=2``.
"""

from __future__ import annotations

from pathlib import Path

from broker_client.flags import broker_compute_enabled

_MSG = (
    "compute mesh_workspace_merge local path unavailable under NIMBUSWARE_BROKER_COMPUTE=1|2; "
    "use SwissArmyNoife compute_work"
)


def _guard() -> None:
    if broker_compute_enabled():
        raise RuntimeError(_MSG)


def _legacy():
    from compute import mesh_workspace_merge_legacy as legacy

    return legacy


def workspace_file_digests(workspace: Path) -> dict[str, str]:
    _guard()
    return _legacy().workspace_file_digests(workspace)


def diff_workspace_files(
    before: dict[str, str],
    after: dict[str, str],
    workspace: Path,
    *,
    max_bytes: int | None = None,
) -> dict[str, str]:
    _guard()
    if max_bytes is None:
        return _legacy().diff_workspace_files(before, after, workspace)
    return _legacy().diff_workspace_files(before, after, workspace, max_bytes=max_bytes)


def apply_workspace_files(workspace: Path, files: dict[str, str]) -> list[str]:
    _guard()
    return _legacy().apply_workspace_files(workspace, files)


def apply_workspace_files_absorb(workspace: Path, files: dict[str, str]) -> list[str]:
    """Absorb-safe apply — allowed under COMPUTE=1|2 (`sak425-c` / `sak432-c`)."""
    return _legacy().apply_workspace_files(workspace, files)

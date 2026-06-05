from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from nimbusware_agent_tools.allowlist import normalise_rel

DENIED_BASENAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".git",
        ".gitignore",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    },
)

DENIED_PATH_GLOBS: tuple[str, ...] = (
    "**/.env",
    "**/.env.*",
    "**/.git/**",
    "**/secrets/**",
    "**/*credentials*",
    "**/*secret*",
    "**/node_modules/**",
)


@dataclass(frozen=True)
class FilesystemJailPolicy:
    enabled: bool = True
    deny_globs: tuple[str, ...] = DENIED_PATH_GLOBS

    def rel_denied(self, rel: str) -> str | None:
        n = normalise_rel(rel)
        if not n:
            return "empty path"
        parts = n.split("/")
        if ".." in parts:
            return "path traversal"
        for part in parts:
            low = part.lower()
            if part in DENIED_BASENAMES or low in DENIED_BASENAMES:
                return f"denied basename: {part}"
        for pattern in self.deny_globs:
            if fnmatch.fnmatch(n, pattern):
                return f"denied by policy: {pattern}"
            alt = pattern.removeprefix("**/") if pattern.startswith("**/") else pattern
            if alt != pattern and fnmatch.fnmatch(n, alt):
                return f"denied by policy: {pattern}"
        return None


def default_jail_policy() -> FilesystemJailPolicy:
    import os

    if os.environ.get("NIMBUSWARE_FILESYSTEM_JAIL", "1").lower() in ("0", "false", "no"):
        return FilesystemJailPolicy(enabled=False)
    return FilesystemJailPolicy()


def assert_rel_allowed(rel: str, *, policy: FilesystemJailPolicy | None = None) -> None:
    pol = policy or default_jail_policy()
    if not pol.enabled:
        return
    reason = pol.rel_denied(rel)
    if reason:
        msg = f"filesystem jail: {reason} ({rel!r})"
        raise ValueError(msg)


def resolve_jailed_workspace_file(
    workspace: Path,
    rel: str,
    *,
    policy: FilesystemJailPolicy | None = None,
) -> Path:
    assert_rel_allowed(rel, policy=policy)
    from nimbusware_agent_tools.allowlist import resolve_workspace_file

    return resolve_workspace_file(workspace, rel)

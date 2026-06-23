from __future__ import annotations

from pathlib import Path


def render_custom_agents_sidebar(repo_root: Path) -> str | None:
    del repo_root
    raise RuntimeError("Custom agents UI moved to /v1/admin/app/.")

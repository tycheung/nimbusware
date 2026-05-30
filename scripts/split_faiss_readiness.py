"""Mechanical split of bundles/faiss_readiness.py into faiss_readiness/."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/pages/config_tooling/bundles/faiss_readiness.py"
OUT = REPO / "packages/nimbusware_console/pages/config_tooling/bundles/faiss_readiness"

HEADER = '''from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
'''

def _indent_block(text: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        out.append(prefix + line if line.strip() else line)
    return "".join(out)


def _module(name: str, func_sig: str, body: str, *, indent_body: bool = True) -> str:
    body_text = _indent_block(body) if indent_body else body
    if indent_body and body_text and not body_text.endswith("\n"):
        body_text += "\n"
    elif not indent_body and body_text and not body_text.endswith("\n"):
        body_text += "\n"
    return (
        f'"""Bundle FAISS readiness — {name}."""\n\n'
        + HEADER
        + f"\n{func_sig}\n"
        + body_text
    )


def _dedent(lines: list[str], spaces: int) -> str:
    prefix = " " * spaces
    out: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            out.append(line[spaces:])
        elif line.strip() == "":
            out.append(line)
        else:
            out.append(line)
    return "".join(out)


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    OUT.mkdir(parents=True, exist_ok=True)

    status_body = _dedent(lines[11:225], 4)
    drilldown_body = _dedent(lines[225:289], 4)
    exports_body = _dedent(lines[289:398], 4)
    search_body = "".join(lines[398:527])

    (OUT / "status_panel.py").write_text(
        _module(
            "status panel",
            "def render_faiss_status_panel(\n"
            "    repo_root: Path,\n"
            "    *,\n"
            "    _faiss: dict[str, Any],\n"
            "    _faiss_sum: dict[str, Any],\n"
            ") -> None:",
            status_body,
        ),
        encoding="utf-8",
    )

    (OUT / "drilldown.py").write_text(
        _module(
            "drilldown",
            "def render_faiss_drilldown_panel(*, repo_root: Path) -> None:",
            drilldown_body,
        ),
        encoding="utf-8",
    )

    (OUT / "exports.py").write_text(
        _module(
            "exports",
            "def render_faiss_exports_panel(\n"
            "    repo_root: Path,\n"
            "    *,\n"
            "    _faiss: dict[str, Any],\n"
            "    _faiss_sum: dict[str, Any],\n"
            ") -> None:",
            exports_body,
        ),
        encoding="utf-8",
    )

    (OUT / "local_search.py").write_text(
        _module(
            "local search",
            "def render_faiss_local_search_panel(*, repo_root: Path) -> None:",
            search_body,
            indent_body=False,
        ),
        encoding="utf-8",
    )

    (OUT / "__init__.py").write_text(
        '''"""Bundle config tooling — FAISS readiness section."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.drilldown import (
    render_faiss_drilldown_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.exports import (
    render_faiss_exports_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.local_search import (
    render_faiss_local_search_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness.status_panel import (
    render_faiss_status_panel,
)


def render_faiss_readiness_section(*, repo_root: Path) -> None:
    with st.expander("FAISS index readiness (paths & catalog freshness)", expanded=False):
        _faiss = bundle_faiss_index_status(repo_root)
        _faiss_sum = bundle_faiss_readiness_summary(repo_root)
        render_faiss_status_panel(repo_root, _faiss=_faiss, _faiss_sum=_faiss_sum)
        render_faiss_drilldown_panel(repo_root=repo_root)
        render_faiss_exports_panel(repo_root, _faiss=_faiss, _faiss_sum=_faiss_sum)
    render_faiss_local_search_panel(repo_root=repo_root)
''',
        encoding="utf-8",
    )

    SRC.unlink()
    print(f"Split {SRC} -> {OUT}/")


if __name__ == "__main__":
    main()

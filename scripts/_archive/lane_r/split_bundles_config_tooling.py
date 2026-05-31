"""Mechanical split of config_tooling/bundles.py into bundles/ package."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/pages/config_tooling/bundles.py"
OUT = REPO / "packages/nimbusware_console/pages/config_tooling/bundles"


def _dedent_block(lines: list[str], spaces: int) -> list[str]:
    prefix = " " * spaces
    out: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            out.append(line[spaces:])
        elif line.strip() == "":
            out.append(line)
        else:
            out.append(line)
    return out


def _write_module(name: str, func_name: str, body_lines: list[str], *, dedent: int) -> None:
    body = _dedent_block(body_lines, dedent)
    text = body_text = "".join(body)
    text = f'''"""Bundle config tooling — {name}."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def {func_name}(*, repo_root: Path) -> None:
{body_text.rstrip()}
'''
    if not text.endswith("\n"):
        text += "\n"
    (OUT / f"{name}.py").write_text(text, encoding="utf-8")


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    OUT.mkdir(parents=True, exist_ok=True)

    shared_lines = lines[0:802] + lines[803:815]  # imports + helper + settings imports
    (OUT / "_shared.py").write_text("".join(shared_lines), encoding="utf-8")

    # catalog search body inside outer expander (excludes nested FAISS expander)
    catalog_body = lines[818:1231]  # from st.caption through else branch before FAISS
    catalog_dedented = _dedent_block(catalog_body, 4)
    catalog_text = "".join(
        line.replace("_root", "repo_root") for line in catalog_dedented
    )
    catalog_py = f'''"""Bundle config tooling — catalog search section."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness import (
    render_faiss_readiness_section,
)


def render_bundle_catalog_search_section() -> None:
    with st.expander("Bundle catalog search (local repo)", expanded=False):
{catalog_text}        render_faiss_readiness_section(repo_root=repo_root)
'''
    (OUT / "catalog_search.py").write_text(catalog_py, encoding="utf-8")

    faiss_body = lines[1231:1748]  # includes `with st.expander("FAISS...`
    faiss_dedented = _dedent_block(faiss_body, 8)
    faiss_inner = "".join(line.replace("_root", "repo_root") for line in faiss_dedented)
    faiss_py = f'''"""Bundle config tooling — FAISS readiness section."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def render_faiss_readiness_section(*, repo_root: Path) -> None:
{faiss_inner.rstrip()}
'''
    if not faiss_py.endswith("\n"):
        faiss_py += "\n"
    (OUT / "faiss_readiness.py").write_text(faiss_py, encoding="utf-8")

    init = '''"""Config tooling — bundle catalog and FAISS sections."""

from __future__ import annotations

from nimbusware_console.pages.config_tooling.bundles.catalog_search import (
    render_bundle_catalog_search_section,
)


def render_config_tooling_bundles_section() -> None:
    render_bundle_catalog_search_section()
'''
    (OUT / "__init__.py").write_text(init, encoding="utf-8")
    print(f"Wrote bundles package to {OUT}")


if __name__ == "__main__":
    main()

"""Regenerate faiss_readiness.py from historical bundles.py (pre-split)."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "packages/nimbusware_console/pages/config_tooling/bundles/faiss_readiness.py"
BUNDLES_REF = "f1d62dd:packages/nimbusware_console/pages/config_tooling/bundles.py"


def main() -> None:
    raw = subprocess.check_output(
        ["git", "show", BUNDLES_REF],
        cwd=REPO,
        text=True,
        encoding="utf-8",
    )
    lines = raw.splitlines(keepends=True)
    faiss_body = lines[1231:1747]
    prefix = "        "
    out: list[str] = []
    for line in faiss_body:
        if line.startswith(prefix):
            out.append(line[8:])
        elif line.strip() == "":
            out.append(line)
        else:
            out.append(line)
    text = (
        '"""Bundle config tooling — FAISS readiness section."""\n\n'
        "from __future__ import annotations\n\n"
        "from pathlib import Path\n\n"
        "from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403\n\n\n"
        "def render_faiss_readiness_section(*, repo_root: Path) -> None:\n"
        + "".join(out).replace("_root", "repo_root")
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT} ({len(out)} body lines)")


if __name__ == "__main__":
    main()

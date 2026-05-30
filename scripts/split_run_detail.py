#!/usr/bin/env python3
"""Split pages/run_detail.py into run_detail/ package (mechanical, run once)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages" / "nimbusware_console" / "pages" / "run_detail.py"
PKG = REPO / "packages" / "nimbusware_console" / "pages" / "run_detail"

SECTIONS: list[tuple[str, int, int, str]] = [
    ("summary", 825, 900, "run_id: str) -> None"),
    ("timeline_integrator", 989, 1400, "run_id: str, data: dict) -> None"),
    ("timeline_personas", 1401, 1715, "run_id: str, data: dict) -> None"),
    ("timeline_escalation", 1716, 2197, "run_id: str, data: dict) -> None"),
    ("timeline_misc", 2198, 3064, "run_id: str, data: dict) -> None"),
    ("critic_matrix", 3065, 3146, "run_id: str, events: list) -> None"),
    ("findings", 3148, 3239, "run_id: str) -> None"),
    ("actions", 3241, 3268, "run_id: str) -> None"),
]


def _read_lines() -> list[str]:
    return SRC.read_text(encoding="utf-8").splitlines(keepends=True)


def _dedent_block(lines: list[str], spaces: int) -> str:
    out: list[str] = []
    for line in lines:
        if line.strip() == "":
            out.append("")
        elif line.startswith(" " * spaces):
            out.append(line[spaces:].rstrip("\n"))
        else:
            out.append(line.rstrip("\n"))
    return "\n".join(out)


def _write_section(name: str, start: int, end: int, sig_suffix: str, lines: list[str]) -> None:
    body = _dedent_block(lines[start - 1 : end], 8)
    fn = f"render_run_detail_{name}"
    parts = [
        f'"""Run detail — {name.replace("_", " ")} panel."""\n',
        "\n",
        "from __future__ import annotations\n",
        "\n",
        "from typing import Any\n",
        "\n",
        "import streamlit as st\n",
        "\n",
        "from nimbusware_console.pages.run_detail._imports import *  # noqa: F403\n",
        "\n",
        "\n",
        f"def {fn}({sig_suffix}:\n",
    ]
    for line in body.splitlines():
        parts.append(f"    {line}\n" if line else "\n")
    (PKG / f"{name}.py").write_text("".join(parts), encoding="utf-8")


def _write_timeline_core(lines: list[str]) -> None:
    body = _dedent_block(lines[900:988], 8)  # lines 901-988 inside else
    header = lines[900:908]  # button + try load
    header_body = _dedent_block(header, 8)
    content = [
        '"""Run detail — timeline load and event table."""\n',
        "\n",
        "from __future__ import annotations\n",
        "\n",
        "from typing import Any\n",
        "\n",
        "import httpx\n",
        "import streamlit as st\n",
        "\n",
        "from nimbusware_console.pages.run_detail._imports import *  # noqa: F403\n",
        "from nimbusware_console.settings import API_BASE\n",
        "\n",
        "\n",
        "def render_run_detail_timeline_core(run_id: str) -> tuple[dict[str, Any], list] | None:\n",
        f"    {header_body.splitlines()[0]}\n",
        "        try:\n",
        "            r = httpx.get(f\"{API_BASE}/runs/{run_id.strip()}/timeline\", timeout=30.0)\n",
        "            r.raise_for_status()\n",
        "            data = r.json()\n",
        "        except httpx.HTTPError as exc:\n",
        "            st.error(f\"API error: {exc}\")\n",
        "            return None\n",
        "        events = timeline_events_from_body(data)\n",
    ]
    for line in body.splitlines()[1:]:  # skip duplicate events = line
        content.append(f"    {line}\n" if line else "\n")
    content.append("        return data, events\n")
    content.append("    return None\n")
    (PKG / "timeline_core.py").write_text("".join(content), encoding="utf-8")


def main() -> None:
    lines = _read_lines()
    PKG.mkdir(parents=True, exist_ok=True)

    import_lines = lines[4:805]
    imports_header = [
        '"""Shared imports for run_detail section modules."""\n',
        "\n",
        "from __future__ import annotations\n",
        "\n",
    ]
    (PKG / "_imports.py").write_text("".join(imports_header + import_lines), encoding="utf-8")

    _write_timeline_core(lines)
    for name, start, end, sig in SECTIONS:
        _write_section(name, start, end, sig, lines)

    init = '''"""Run detail page — composed section panels."""

from __future__ import annotations

import streamlit as st

from nimbusware_console.pages import _state as rl
from nimbusware_console.pages.run_detail.actions import render_run_detail_actions
from nimbusware_console.pages.run_detail.critic_matrix import render_run_detail_critic_matrix
from nimbusware_console.pages.run_detail.findings import render_run_detail_findings
from nimbusware_console.pages.run_detail.summary import render_run_detail_summary
from nimbusware_console.pages.run_detail.timeline_core import render_run_detail_timeline_core
from nimbusware_console.pages.run_detail.timeline_escalation import (
    render_run_detail_timeline_escalation,
)
from nimbusware_console.pages.run_detail.timeline_integrator import (
    render_run_detail_timeline_integrator,
)
from nimbusware_console.pages.run_detail.timeline_misc import render_run_detail_timeline_misc
from nimbusware_console.pages.run_detail.timeline_personas import (
    render_run_detail_timeline_personas,
)
from nimbusware_console.settings import API_BASE


def render_run_detail_section() -> None:
    st.divider()
    with st.container(border=True):
        st.subheader("Run detail")
        run_id = st.text_input("Run ID (detail)", placeholder="uuid", key=rl._SS_DETAIL)

        if run_id.strip():
            rid = run_id.strip()
            st.markdown(
                "Artifact-style **read-only JSON** (existing API; no separate artifact store yet):"
            )
            st.caption("Copy full URL from a line below (select text or use your terminal).")
            st.code(f"{API_BASE}/runs/{rid}", language=None)
            st.code(f"{API_BASE}/runs/{rid}/timeline", language=None)
            st.code(f"{API_BASE}/runs/{rid}/findings", language=None)

        c1, c2 = st.columns(2)
        with c1:
            render_run_detail_summary(run_id)
            timeline_ctx = render_run_detail_timeline_core(run_id)
            if timeline_ctx is not None:
                data, events = timeline_ctx
                render_run_detail_timeline_integrator(run_id, data)
                render_run_detail_timeline_personas(run_id, data)
                render_run_detail_timeline_escalation(run_id, data)
                render_run_detail_timeline_misc(run_id, data)
                render_run_detail_critic_matrix(run_id, events)
        with c2:
            render_run_detail_findings(run_id)

        st.divider()
        render_run_detail_actions(run_id)
'''
    (PKG / "__init__.py").write_text(init, encoding="utf-8")
    print(f"Split into {PKG}/ ({len(SECTIONS) + 1} sections)")
    print("Remove monolithic run_detail.py — package replaces it.")


if __name__ == "__main__":
    main()

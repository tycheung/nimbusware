#!/usr/bin/env python3
"""Rebuild run_detail/__init__.py as one module from section sources."""

from __future__ import annotations

import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "packages" / "nimbusware_console" / "pages" / "run_detail"


def _extract_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^def render_run_detail_\w+\([^)]*\)[^:]*:\n", text, re.M)
    if not match:
        return ""
    return text[match.end() :].rstrip() + "\n"


def main() -> None:
    imports = (PKG / "_imports.py").read_text(encoding="utf-8")
    imports = imports.split("from __future__ import annotations\n", 1)[-1].lstrip()

    summary = _extract_body(PKG / "summary.py")
    timeline_core = _extract_body(PKG / "timeline_core.py")
    timeline_integrator = _extract_body(PKG / "timeline_integrator.py")
    timeline_personas = _extract_body(PKG / "timeline_personas.py")
    timeline_escalation = _extract_body(PKG / "timeline_escalation.py")
    timeline_misc = _extract_body(PKG / "timeline_misc.py")
    critic = _extract_body(PKG / "critic_matrix.py")
    findings = _extract_body(PKG / "findings.py")
    actions = _extract_body(PKG / "actions.py")

    init = f'''"""Run detail page — composed section panels."""

from __future__ import annotations

{imports}
from nimbusware_console.settings import API_BASE
from nimbusware_console.pages import _state as rl


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
            st.code(f"{{API_BASE}}/runs/{{rid}}", language=None)
            st.code(f"{{API_BASE}}/runs/{{rid}}/timeline", language=None)
            st.code(f"{{API_BASE}}/runs/{{rid}}/findings", language=None)

        c1, c2 = st.columns(2)
        with c1:
{_indent(summary, 3)}
{_indent(timeline_core, 3)}
{_indent(timeline_integrator, 4)}
{_indent(timeline_personas, 4)}
{_indent(timeline_escalation, 4)}
{_indent(timeline_misc, 4)}
{_indent(critic, 4)}
        with c2:
{_indent(findings, 3)}
{_indent(actions, 2)}


def _indent(text: str, levels: int) -> str:
    pad = "    " * levels
    return "".join(pad + line if line.strip() else line for line in text.splitlines(keepends=True))
'''

    # Fix: inline helper at bottom won't work - compute indented blocks in Python
    def indent(text: str, levels: int) -> str:
        pad = "    " * levels
        out_lines = []
        for line in text.splitlines():
            if line.strip():
                out_lines.append(pad + line)
            else:
                out_lines.append("")
        return "\n".join(out_lines)

    init = f'''"""Run detail page — composed section panels."""

from __future__ import annotations

{imports}
from nimbusware_console.settings import API_BASE
from nimbusware_console.pages import _state as rl


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
            st.code(f"{{API_BASE}}/runs/{{rid}}", language=None)
            st.code(f"{{API_BASE}}/runs/{{rid}}/timeline", language=None)
            st.code(f"{{API_BASE}}/runs/{{rid}}/findings", language=None)

        c1, c2 = st.columns(2)
        with c1:
{indent(summary, 3)}
{indent(timeline_core, 3)}
            if timeline_ctx is not None:
                data, events = timeline_ctx
{indent(timeline_integrator, 4)}
{indent(timeline_personas, 4)}
{indent(timeline_escalation, 4)}
{indent(timeline_misc, 4)}
{indent(critic, 4)}
        with c2:
{indent(findings, 3)}
{indent(actions, 2)}
'''

    (PKG / "__init__.py").write_text(init, encoding="utf-8")

    # Remove broken section modules; keep _imports for reference only
    for name in (
        "summary.py",
        "timeline_core.py",
        "timeline_integrator.py",
        "timeline_personas.py",
        "timeline_escalation.py",
        "timeline_misc.py",
        "critic_matrix.py",
        "findings.py",
        "actions.py",
    ):
        (PKG / name).unlink(missing_ok=True)

    print("Rebuilt run_detail/__init__.py monolith from sections")


if __name__ == "__main__":
    main()

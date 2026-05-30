#!/usr/bin/env python3
"""Repair timeline_personas.py indentation after mechanical split."""

from __future__ import annotations

from pathlib import Path

PATH = (
    Path(__file__).resolve().parents[1]
    / "packages/nimbusware_console/pages/run_detail/timeline_personas.py"
)


def main() -> None:
    lines = PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    in_fn = False
    for i, line in enumerate(lines):
        if line.startswith("def render_run_detail_"):
            in_fn = True
            out.append(line)
            continue
        if not in_fn:
            out.append(line)
            continue
        if not line.strip():
            out.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")
        # Function-level statements (4 spaces)
        if stripped.startswith("_pa ") or stripped.startswith("_ae ") or stripped.startswith("_sr "):
            out.append("    " + stripped)
            continue
        if stripped.startswith("_pa_") or stripped.startswith("_ae_") or stripped.startswith("_sr_"):
            if stripped.startswith("_sr_marker"):
                continue  # moved to escalation module
            out.append("    " + stripped)
            continue
        if stripped.startswith("with st.expander") and "Persona" in stripped:
            out.append("    " + stripped)
            continue
        if stripped.startswith("with st.expander") and "Agent evaluator" in stripped:
            out.append("    " + stripped)
            continue
        if stripped.startswith("with st.expander") and "Self-refinement" in stripped:
            out.append("    " + stripped)
            continue
        # Body lines that lost indentation entirely
        if indent == 0:
            out.append("        " + stripped)
            continue
        # One-level short indent (4 spaces) inside expander -> 8 spaces
        if indent == 4 and not stripped.startswith("with st.expander"):
            out.append("        " + stripped)
            continue
        out.append(line)
    PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("Repaired", PATH.name)


if __name__ == "__main__":
    main()

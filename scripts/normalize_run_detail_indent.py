#!/usr/bin/env python3
"""Normalize function-body indentation in run_detail section modules."""

from __future__ import annotations

from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "packages" / "nimbusware_console" / "pages" / "run_detail"

FILES = [
    "timeline_integrator.py",
    "timeline_personas.py",
    "timeline_escalation.py",
    "timeline_misc.py",
    "critic_matrix.py",
]


def _normalize(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    body: list[str] = []
    header: list[str] = []
    in_fn = False
    for line in lines:
        if line.startswith("def render_run_detail_"):
            header = out[:]
            body = [line]
            in_fn = True
            out = []
            continue
        if in_fn:
            body.append(line)
        else:
            out.append(line)
    if not body:
        return
    fn_line = body[0]
    rest = body[1:]
    indents = [len(l) - len(l.lstrip(" ")) for l in rest if l.strip()]
    if not indents:
        return
    min_indent = min(indents)
    shift = min_indent - 4
    fixed_rest: list[str] = []
    for line in rest:
        if not line.strip():
            fixed_rest.append("")
        elif line.startswith(" " * min_indent) or (
            len(line) - len(line.lstrip(" ")) >= min_indent
        ):
            current = len(line) - len(line.lstrip(" "))
            new_indent = max(0, current - shift)
            fixed_rest.append(" " * new_indent + line.lstrip(" "))
        else:
            fixed_rest.append(line)
    path.write_text(
        "\n".join(header + [fn_line] + fixed_rest) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    for name in FILES:
        _normalize(PKG / name)
    print("Normalized indentation in", len(FILES), "files")


if __name__ == "__main__":
    main()

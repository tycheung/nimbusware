"""Mechanical split of workflows/integrator.py into integrator/ package."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages/nimbusware_console/pages/config_tooling/workflows/integrator.py"
OUT = REPO / "packages/nimbusware_console/pages/config_tooling/workflows/integrator"

SECTIONS: tuple[tuple[str, str, int, int], ...] = (
    ("universal_critique", "render_universal_critique_section", 40, 293),
    ("self_refinement", "render_self_refinement_section", 294, 540),
    ("security_scan", "render_security_scan_section", 541, 729),
    ("escalation_suppress", "render_escalation_suppress_section", 730, 1048),
    ("agent_evaluator", "render_agent_evaluator_section", 1049, 1230),
    ("thresholds", "render_thresholds_section", 1237, 1386),
    ("preview", "render_integrator_preview_section", 1387, 1453),
    ("apply_integrator_gate", "render_apply_integrator_gate_section", 1454, 1507),
    ("apply_agent_evaluator", "render_apply_agent_evaluator_section", 1508, 1576),
    ("apply_full_profile", "render_apply_full_profile_section", 1577, 1960),
)


def _dedent_block(lines: list[str], spaces: int = 4) -> list[str]:
    prefix = " " * spaces
    out: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            out.append(line[spaces:])
        else:
            out.append(line)
    return out


def _write_section(name: str, func_name: str, body_lines: list[str]) -> None:
    header = f'''"""Integrator workflow section — {name}."""

from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def {func_name}(*, repo_root: Path, workflow_profile: str | None) -> None:
'''
    body = _dedent_block(body_lines)
    # rewrite _iroot -> repo_root, _wf_pick -> workflow_profile
    text = header + "".join(
        line.replace("_iroot", "repo_root").replace("_wf_pick", "workflow_profile")
        for line in body
    )
    if not text.endswith("\n"):
        text += "\n"
    (OUT / f"{name}.py").write_text(text, encoding="utf-8")


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    OUT.mkdir(parents=True, exist_ok=True)

    header_block = lines[9:39]  # caption + repo + profile picker (inside outer expander)

    for name, func_name, start, end in SECTIONS:
        _write_section(name, func_name, lines[start - 1 : end])

    print(f"Wrote integrator package to {OUT}")
    print("NOTE: compose __init__.py manually or run r0 script; header indent must stay at 8 spaces.")


if __name__ == "__main__":
    main()

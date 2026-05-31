"""Split remaining console modules still over 400 lines (batch 3)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSOLE = ROOT / "packages/nimbusware_console"
RUN_DETAIL = CONSOLE / "pages/run_detail"


def _split_explainer(
    *,
    rel_module: str,
    slices: tuple[tuple[str, int, int, str], ...],
    init_imports: tuple[str, ...],
) -> None:
    src_path = CONSOLE / f"{rel_module}.py"
    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    header_end = next(
        i for i, line in enumerate(lines) if line.startswith("def ") or line.startswith("class ")
    )
    header = "".join(lines[:header_end])

    pkg = CONSOLE / rel_module
    pkg.mkdir(exist_ok=True)

    for filename, start, end, extra_imports in slices:
        chunk = "".join(lines[start - 1 : min(end - 1, len(lines))])
        body = header + extra_imports + (
            "\n" if extra_imports and not extra_imports.endswith("\n") else ""
        ) + chunk
        (pkg / filename).write_text(body, encoding="utf-8")

    mod = rel_module.replace("/", ".")
    init = f'"""Console helpers for ``{rel_module}``."""\n\n'
    for name in init_imports:
        init += f"from nimbusware_console.{mod}.{name} import *  # noqa: F403\n"
    (pkg / "__init__.py").write_text(init, encoding="utf-8")
    src_path.write_text(f"from nimbusware_console.{mod} import *  # noqa: F403\n", encoding="utf-8")


def _extract_body(lines: list[str], start: int, end: int, *, dedent: int = 0) -> str:
    out: list[str] = []
    for line in lines[start - 1 : end - 1]:
        if line.strip() == "":
            out.append("\n")
        elif len(line) >= dedent and line[:dedent].isspace():
            out.append(line[dedent:])
        else:
            out.append(line)
    return "".join(out)


def _split_timeline_sections(
    *,
    rel_path: str,
    render_name: str,
    render_params: str,
    sections: tuple[tuple[str, str, int, int, str], ...] | tuple[tuple[str, str, int, int], ...],
    helper_lines: tuple[int, int] | None = None,
) -> None:
    src = CONSOLE / rel_path
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    render_idx = next(i for i, line in enumerate(lines) if line.startswith(f"def {render_name}"))
    header = "".join(lines[:render_idx])
    helpers = ""
    if helper_lines:
        helpers = "".join(lines[helper_lines[0] - 1 : helper_lines[1] - 1]) + "\n"

    pkg = src.parent / src.stem
    pkg.mkdir(exist_ok=True)

    imports: list[str] = []
    calls: list[str] = []
    for section in sections:
        if len(section) == 5:
            filename, func_name, start, end, preamble = section
        else:
            filename, func_name, start, end = section  # type: ignore[misc]
            preamble = ""
        body = _extract_body(lines, start, end, dedent=0)
        (pkg / filename).write_text(
            header
            + helpers
            + f"\ndef {func_name}({render_params}) -> None:\n"
            + preamble
            + body,
            encoding="utf-8",
        )
        mod = f"nimbusware_console.pages.run_detail.{src.stem}.{filename[:-3]}"
        imports.append(f"from {mod} import {func_name}")
        arg_names = [p.split(":")[0].strip().split("=")[0].strip() for p in render_params.split(",")]
        calls.append(f"    {func_name}({', '.join(arg_names)})")

    init = f'"""``{src.stem}`` timeline sections."""\n\n' + "\n".join(imports) + "\n\n"
    init += f"def {render_name}({render_params}) -> None:\n" + "\n".join(calls) + "\n"
    (pkg / "__init__.py").write_text(init, encoding="utf-8")
    src.write_text(
        f"from nimbusware_console.pages.run_detail.{src.stem} import {render_name}\n",
        encoding="utf-8",
    )


def _split_imports_facade(src_rel: str, split_line: int, parts: tuple[str, str]) -> None:
    src = CONSOLE / src_rel
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    stem = Path(src_rel).stem
    pkg = src.parent / stem
    pkg.mkdir(exist_ok=True)
    (pkg / f"{parts[0]}.py").write_text("".join(lines[: split_line - 1]), encoding="utf-8")
    (pkg / f"{parts[1]}.py").write_text("".join(lines[split_line - 1 :]), encoding="utf-8")
    facade = (
        f'"""Re-export run-detail display imports."""\n\n'
        f"import nimbusware_console.pages.run_detail.{stem}.{parts[0]} as _a\n"
        f"import nimbusware_console.pages.run_detail.{stem}.{parts[1]} as _b\n\n"
        "globals().update({k: v for k, v in vars(_a).items() if not k.startswith('__')})\n"
        "globals().update({k: v for k, v in vars(_b).items() if not k.startswith('__')})\n"
    )
    (pkg / "__init__.py").write_text(facade, encoding="utf-8")
    src.write_text(
        f"from nimbusware_console.pages.run_detail.{stem} import *  # noqa: F403\n",
        encoding="utf-8",
    )


def _split_config_page(
    *,
    rel_path: str,
    render_name: str,
    sections: tuple[tuple[str, str, int, int], ...],
    init_template: str,
) -> None:
    src = CONSOLE / rel_path
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    render_idx = next(i for i, line in enumerate(lines) if line.startswith(f"def {render_name}"))
    header = "".join(lines[:render_idx])

    pkg = src.parent / src.stem
    pkg.mkdir(exist_ok=True)

    for filename, func_name, start, end in sections:
        body = _extract_body(lines, start, end, dedent=4)
        (pkg / filename).write_text(
            header + f"\ndef {func_name}(repo_root: Path) -> None:\n" + body,
            encoding="utf-8",
        )

    (pkg / "__init__.py").write_text(init_template, encoding="utf-8")
    pkg_name = src.parent.name
    src.write_text(
        f"from nimbusware_console.pages.config_tooling.{pkg_name}.{src.stem} import {render_name}\n",
        encoding="utf-8",
    )


def split_timeline_and_config_pages() -> None:
    ts_slug = (
        "    _ts = datetime.now(timezone.utc).strftime(\"%Y%m%dT%H%M%SZ\")\n"
        "    _slug = _run_slug(run_id.strip())\n\n"
    )
    persona_ctx = (
        "    _wf_pick = _workflow_profile_pick(data)\n"
        "    _iroot = Path(os.environ.get(\"NIMBUSWARE_REPO_ROOT\", \".\")).resolve()\n"
        + ts_slug
    )

    _split_timeline_sections(
        rel_path="pages/run_detail/timeline_escalation.py",
        render_name="render_run_detail_timeline_escalation",
        render_params="run_id: str, data: dict",
        sections=(
            ("marker_history.py", "_render_self_refinement_marker_history", 69, 211),
            ("run_escalated.py", "_render_run_escalated", 211, 327),
            ("escalated_history.py", "_render_run_escalated_history", 327, 445),
            ("escalated_delta.py", "_render_run_escalated_delta", 445, 9999),
        ),
    )
    _split_timeline_sections(
        rel_path="pages/run_detail/timeline_integrator.py",
        render_name="render_run_detail_timeline_integrator",
        render_params="run_id: str, data: dict",
        sections=(
            ("gate_latest.py", "_render_integrator_gate_latest", 57, 199),
            ("gate_history.py", "_render_integrator_gate_history", 199, 338),
            ("gate_delta.py", "_render_integrator_gate_delta", 338, 9999),
        ),
    )
    _split_timeline_sections(
        rel_path="pages/run_detail/timeline_personas.py",
        render_name="render_run_detail_timeline_personas",
        render_params="run_id: str, data: dict",
        helper_lines=(103, 113),
        sections=(
            ("persona_assignment.py", "_render_persona_assignment", 121, 160, ts_slug),
            ("agent_evaluator.py", "_render_agent_evaluator", 160, 322, persona_ctx),
            ("self_refinement.py", "_render_self_refinement", 322, 9999, persona_ctx),
        ),
    )
    _split_timeline_sections(
        rel_path="pages/run_detail/timeline_misc_security.py",
        render_name="_render_timeline_misc_security",
        render_params="run_id: str, data: dict, _wf_pick: str",
        sections=(
            ("scan_on_verify.py", "_render_security_scan_on_verify", 64, 318),
            ("scan_history.py", "_render_security_scan_history", 318, 9999),
        ),
    )

    _split_config_page(
        rel_path="pages/config_tooling/bundles/catalog_search.py",
        render_name="render_bundle_catalog_search_section",
        sections=(
            ("summary_panel.py", "_render_catalog_summary_panel", 20, 149),
            ("rollups_panel.py", "_render_catalog_rollups_panel", 149, 421),
        ),
        init_template='''"""``catalog_search`` config tooling section."""

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.bundles.catalog_search.rollups_panel import (
    _render_catalog_rollups_panel,
)
from nimbusware_console.pages.config_tooling.bundles.catalog_search.summary_panel import (
    _render_catalog_summary_panel,
)
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness import (
    render_faiss_readiness_section,
)


def render_bundle_catalog_search_section() -> None:
    with st.expander("Bundle catalog search (local repo)", expanded=False):
        st.caption(
            "Read-only: same ``search_bundles`` helper as **GET /v1/bundles/search** over "
            "``configs/bundles/catalog.yaml``. Uses **NIMBUSWARE_REPO_ROOT** (resolved); "
            "matches the API frozen repo root when both use the same env.",
        )
        repo_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{repo_root}`")
        _render_catalog_summary_panel(repo_root)
        _render_catalog_rollups_panel(repo_root)
    render_faiss_readiness_section(repo_root=repo_root)
''',
    )
    _split_config_page(
        rel_path="pages/config_tooling/workflows/persona_shelves.py",
        render_name="render_workflows_persona_shelves_section",
        sections=(
            ("critique_panel.py", "_render_critique_pairings_panel", 15, 205),
            ("catalog_panel.py", "_render_persona_catalog_panel", 205, 9999),
        ),
        init_template='''"""``persona_shelves`` config tooling section."""

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.workflows.persona_shelves.catalog_panel import (
    _render_persona_catalog_panel,
)
from nimbusware_console.pages.config_tooling.workflows.persona_shelves.critique_panel import (
    _render_critique_pairings_panel,
)


def render_workflows_persona_shelves_section() -> None:
    with st.expander("Persona shelves (local repo)", expanded=False):
        st.caption(
            "Read-only: same ``PersonaShelf`` + ``configs/personas/shelves.yaml`` shape as "
            "**GET /v1/personas** (``NIMBUSWARE_REPO_ROOT`` / frozen repo root). No API call.",
        )
        st.caption(persona_catalog_taxonomy_scope_frozen_caption())
        _proot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{_proot}`")
        _render_critique_pairings_panel(_proot)
        _render_persona_catalog_panel(_proot)
''',
    )


def main() -> None:
    _split_explainer(
        rel_module="bundle_catalog/catalog_local/search",
        slices=(
            ("captions.py", 17, 166, ""),
            ("metrics.py", 166, 285, ""),
            ("local_bundles.py", 285, 359, ""),
            ("hits.py", 359, 411, ""),
            ("run_search.py", 411, 9999, ""),
        ),
        init_imports=("captions", "metrics", "local_bundles", "hits", "run_search"),
    )

    _split_explainer(
        rel_module="bundle_catalog/faiss_status/drilldown",
        slices=(
            (
                "core.py",
                31,
                169,
                "from nimbusware_console.bundle_catalog.faiss_status.index_status import (\n"
                "    bundle_faiss_index_status,\n"
                ")\n",
            ),
            ("captions.py", 169, 211, ""),
            ("tables.py", 211, 348, ""),
            ("dir_captions.py", 348, 9999, ""),
        ),
        init_imports=("core", "captions", "tables", "dir_captions"),
    )

    _split_explainer(
        rel_module="universal_critique_timeline_display",
        slices=(
            ("rows.py", 11, 134, ""),
            (
                "captions.py",
                134,
                189,
                "from nimbusware_console.universal_critique_timeline_display.rows import (\n"
                "    universal_critique_from_timeline,\n"
                ")\n",
            ),
            (
                "metrics.py",
                189,
                9999,
                "from nimbusware_console.universal_critique_timeline_display.rows import (\n"
                "    universal_critique_timeline_export_filename_slug,\n"
                ")\n",
            ),
        ),
        init_imports=("rows", "captions", "metrics"),
    )

    _split_imports_facade(
        "pages/run_detail/_imports_display_a.py",
        233,
        ("agent_through_escalation", "findings_through_persona"),
    )

    split_timeline_and_config_pages()

    print("console displays batch3 split done")


if __name__ == "__main__":
    main()

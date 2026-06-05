#!/usr/bin/env python3
"""Mechanical file splits for R2–R5 (run once)."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _write(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {rel} ({len(content.splitlines())} lines)")


def split_run_escalated_display() -> None:
    src = _read("packages/nimbusware_console/run_escalated_display.py")
    func_pat = re.compile(r"^(def \w+\([^)]*\)[^:]*:.*?)(?=^def |\Z)", re.M | re.S)
    funcs = {m.group(1).split("(")[0].replace("def ", ""): m.group(1) for m in func_pat.finditer(src)}
    header = textwrap.dedent(
        '''\
        """Run escalated display helpers."""

        from __future__ import annotations

        import csv
        import json
        import re
        from collections.abc import Mapping, Sequence
        from io import StringIO
        from pathlib import Path
        from typing import Any

        from nimbusware_projections.fields.run_escalated import RUN_ESCALATED_DISPLAY_FIELDS

        '''
    )
    common = header + funcs["_stringify"]
    rows_names = [
        n
        for n in funcs
        if n != "_stringify"
        and "caption" not in n
        and "operator_metrics" not in n
    ]
    caption_names = [n for n in funcs if "caption" in n]
    metrics_names = [n for n in funcs if "operator_metrics" in n]

    rows_body = header.replace(
        "from nimbusware_projections.fields.run_escalated import RUN_ESCALATED_DISPLAY_FIELDS\n\n",
        "from nimbusware_console.run_escalated._common import _stringify\n"
        "from nimbusware_projections.fields.run_escalated import RUN_ESCALATED_DISPLAY_FIELDS\n\n",
    )
    rows_body += "\n\n".join(funcs[n] for n in rows_names)
    rows_body = rows_body.replace("_RUN_ESCALATED_FIELDS", "RUN_ESCALATED_DISPLAY_FIELDS")

    captions_body = header.replace(
        "from nimbusware_projections.fields.run_escalated import RUN_ESCALATED_DISPLAY_FIELDS\n\n",
        "",
    ) + "\n\n".join(funcs[n] for n in caption_names)

    metrics_body = header.replace(
        "from nimbusware_projections.fields.run_escalated import RUN_ESCALATED_DISPLAY_FIELDS\n\n",
        "",
    ) + "\n\n".join(funcs[n] for n in metrics_names)

    _write("packages/nimbusware_console/run_escalated/_common.py", common)
    _write("packages/nimbusware_console/run_escalated/rows.py", rows_body)
    _write("packages/nimbusware_console/run_escalated/captions.py", captions_body)
    _write("packages/nimbusware_console/run_escalated/metrics.py", metrics_body)

    all_public = sorted(set(rows_names + caption_names + metrics_names))
    init_lines = [
        '"""Run escalated Streamlit display (rows, captions, metrics)."""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for mod, names in (
        ("rows", rows_names),
        ("captions", caption_names),
        ("metrics", metrics_names),
    ):
        if names:
            init_lines.append(f"from nimbusware_console.run_escalated.{mod} import (")
            for n in names:
                init_lines.append(f"    {n},")
            init_lines.append(")")
            init_lines.append("")
    init_lines.append("__all__ = [")
    for n in all_public:
        init_lines.append(f'    "{n}",')
    init_lines.append("]")
    _write("packages/nimbusware_console/run_escalated/__init__.py", "\n".join(init_lines) + "\n")

    shim = textwrap.dedent(
        '''\
        """Backward-compatible re-export of run escalated display helpers."""

        from __future__ import annotations

        from nimbusware_console.run_escalated import *  # noqa: F403
        from nimbusware_console.run_escalated import __all__  # noqa: F401
        '''
    )
    _write("packages/nimbusware_console/run_escalated_display.py", shim)


def split_workflows() -> None:
    src_path = ROOT / "packages/nimbusware_console/pages/config_tooling/workflows.py"
    lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)
    shared_end = 816  # through blank line before render fn
    shared = "".join(lines[:shared_end])
    shared = shared.replace(
        "from nimbusware_console.settings import API_BASE\nfrom nimbusware_console.pages import _state as rl\n",
        "",
    )
    shared += "\nfrom nimbusware_console.settings import API_BASE\nfrom nimbusware_console.pages import _state as rl\n"

    sections: list[tuple[str, str, int, int]] = [
        ("bundle_memory", "render_workflows_bundle_memory_section", 817, 828),
        ("bundle_editor", "render_workflows_bundle_editor_section", 829, 901),
        ("integrator", "render_workflows_integrator_section", 902, 2853),
        ("persona_shelves", "render_workflows_persona_shelves_section", 2854, 3275),
        ("persona_editor", "render_workflows_persona_editor_section", 3276, 3578),
        ("prune", "render_workflows_prune_section", 3579, len(lines)),
    ]

    pkg = ROOT / "packages/nimbusware_console/pages/config_tooling/workflows"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "_shared.py").write_text(
        '"""Shared imports for config tooling workflow sections."""\n\n' + shared,
        encoding="utf-8",
    )

    render_calls: list[str] = []
    for stem, fn_name, start, end in sections:
        body_lines = lines[start - 1 : end]
        body = "".join(body_lines)
        # drop outer function wrapper indentation (8 spaces -> 4)
        body = textwrap.dedent(body)
        if body.startswith("def render_config_tooling_workflows_section"):
            body = body.split("\n", 1)[1] if "\n" in body else ""
        content = textwrap.dedent(
            f'''\
            """Config tooling — {stem.replace("_", " ")} section."""

            from __future__ import annotations

            from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


            def {fn_name}() -> None:
            '''
        )
        indented = textwrap.indent(body.strip(), "    ")
        (pkg / f"{stem}.py").write_text(content + indented + "\n", encoding="utf-8")
        render_calls.append(f"    {fn_name}()")

    init = textwrap.dedent(
        '''\
        """Config tooling — workflow explainers and disk apply sections."""

        from __future__ import annotations

        from nimbusware_console.pages.config_tooling.workflows.bundle_editor import (
            render_workflows_bundle_editor_section,
        )
        from nimbusware_console.pages.config_tooling.workflows.bundle_memory import (
            render_workflows_bundle_memory_section,
        )
        from nimbusware_console.pages.config_tooling.workflows.integrator import (
            render_workflows_integrator_section,
        )
        from nimbusware_console.pages.config_tooling.workflows.persona_editor import (
            render_workflows_persona_editor_section,
        )
        from nimbusware_console.pages.config_tooling.workflows.persona_shelves import (
            render_workflows_persona_shelves_section,
        )
        from nimbusware_console.pages.config_tooling.workflows.prune import (
            render_workflows_prune_section,
        )


        def render_config_tooling_workflows_section() -> None:
        '''
    )
    init += "\n".join(render_calls) + "\n\n__all__ = [\"render_config_tooling_workflows_section\"]\n"
    (pkg / "__init__.py").write_text(init, encoding="utf-8")
    src_path.unlink()
    print("split workflows.py -> workflows/ package")


def split_timeline_misc() -> None:
    src_path = ROOT / "packages/nimbusware_console/pages/run_detail/timeline_misc.py"
    lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)
    header = "".join(lines[:12])
    body = "".join(lines[12:])
    # function body starts at line 14 with 4-space indent inside render fn
    inner = textwrap.dedent(body)

    cuts: list[tuple[str, str, str]] = [
        (
            "timeline_misc_core",
            "_render_timeline_misc_core",
            r'_wf_pick = data\.get\("workflow_profile"\).*?(?=    _ss = security_scan)',
        ),
        (
            "timeline_misc_security",
            "_render_timeline_misc_security",
            r'    _ss = security_scan_on_verify_from_timeline\(data\).*?(?=    _uc_tl = universal_critique_from_timeline)',
        ),
        (
            "timeline_misc_universal_critique",
            "_render_timeline_misc_universal_critique",
            r'    _uc_tl = universal_critique_from_timeline\(data\).*?(?=    _sf = scraper_fetch_from_timeline)',
        ),
        (
            "timeline_misc_scraper",
            "_render_timeline_misc_scraper",
            r'    _sf = scraper_fetch_from_timeline\(data\).*?(?=    _pf = preflight_history_from_timeline)',
        ),
        (
            "timeline_misc_preflight",
            "_render_timeline_misc_preflight",
            r'    _pf = preflight_history_from_timeline\(data\).*?\Z',
        ),
    ]

    pkg_dir = ROOT / "packages/nimbusware_console/pages/run_detail"
    extracted: list[tuple[str, str]] = []
    for filename, fn_name, pattern in cuts:
        m = re.search(pattern, inner, re.S)
        if not m:
            raise RuntimeError(f"timeline_misc split failed for {filename}")
        chunk = m.group(0).rstrip() + "\n"
        extracted.append((fn_name, chunk))
        mod = textwrap.dedent(
            f'''\
            """Run detail — timeline misc ({filename.replace("timeline_misc_", "")})."""

            from __future__ import annotations

            import os
            from typing import Any

            import streamlit as st

            from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


            def {fn_name}(run_id: str, data: dict, _wf_pick: str) -> None:
            '''
        )
        mod += textwrap.indent(textwrap.dedent(chunk), "    ")
        (pkg_dir / f"{filename}.py").write_text(mod, encoding="utf-8")

    orchestrator = textwrap.dedent(
        '''\
        """Run detail — timeline misc panel (orchestrator)."""

        from __future__ import annotations

        import os
        from typing import Any

        import streamlit as st

        from nimbusware_console.pages.run_detail.timeline_misc_core import (
            _render_timeline_misc_core,
        )
        from nimbusware_console.pages.run_detail.timeline_misc_preflight import (
            _render_timeline_misc_preflight,
        )
        from nimbusware_console.pages.run_detail.timeline_misc_scraper import (
            _render_timeline_misc_scraper,
        )
        from nimbusware_console.pages.run_detail.timeline_misc_security import (
            _render_timeline_misc_security,
        )
        from nimbusware_console.pages.run_detail.timeline_misc_universal_critique import (
            _render_timeline_misc_universal_critique,
        )


        def _workflow_profile_pick(data: dict[str, Any]) -> str:
            wf = data.get("workflow_profile") if isinstance(data, dict) else None
            if isinstance(wf, str) and wf.strip():
                return wf.strip()
            return os.environ.get("NIMBUSWARE_WORKFLOW_PROFILE", "nimbusware_production")


        def render_run_detail_timeline_misc(run_id: str, data: dict) -> None:
            _wf_pick = _workflow_profile_pick(data)
            _render_timeline_misc_core(run_id, data, _wf_pick)
            _render_timeline_misc_security(run_id, data, _wf_pick)
            _render_timeline_misc_universal_critique(run_id, data, _wf_pick)
            _render_timeline_misc_scraper(run_id, data, _wf_pick)
            _render_timeline_misc_preflight(run_id, data, _wf_pick)
        '''
    )
    src_path.write_text(orchestrator, encoding="utf-8")
    print("split timeline_misc.py")


def split_test_api() -> None:
    src_path = ROOT / "tests/api/test_api.py"
    content = src_path.read_text(encoding="utf-8")
    header_end = content.index("@pytest.fixture")
    header = content[:header_end]
    fixture_and_rest = content[header_end:]
    fixture_end = fixture_and_rest.index("\n\n", fixture_and_rest.index("yield c\n"))
    fixture_block = fixture_and_rest[: fixture_end + 2]
    tests_body = fixture_and_rest[fixture_end + 2 :]

    conftest = header.replace("from nimbusware_api.app import app  # noqa: E402\n\n\n", "") + fixture_block.replace("@pytest.fixture\ndef client", "import pytest\nfrom fastapi.testclient import TestClient\n\nfrom nimbusware_api.app import app  # noqa: E402\n\n\n@pytest.fixture\ndef client")
    _write("tests/api/conftest.py", conftest)

    func_pat = re.compile(r"^(def test_\w+\(.*?\n(?:    .*\n)*?)(?=^def test_|\Z)", re.M)
    buckets: dict[str, list[str]] = {
        "openapi": [],
        "bundles": [],
        "timeline": [],
        "runs": [],
    }
    for m in func_pat.finditer(tests_body):
        block = m.group(1)
        name = block.split("(")[0].replace("def ", "")
        if name.startswith("test_openapi") or "openapi" in name or "rfc5988" in name.lower() or "link_header" in name:
            buckets["openapi"].append(block)
        elif "bundle" in name or "persona_shelves" in name or "persona_edit" in name:
            buckets["bundles"].append(block)
        elif name.startswith("test_timeline") or "timeline" in name:
            buckets["timeline"].append(block)
        else:
            buckets["runs"].append(block)

    for stem, blocks in buckets.items():
        if not blocks:
            continue
        mod = textwrap.dedent(
            '''\
            from __future__ import annotations

            from pathlib import Path

            import pytest
            from fastapi.testclient import TestClient

            pytestmark = pytest.mark.slow

            '''
        )
        if stem == "bundles":
            mod += "from uuid import UUID, uuid4\n\n"
        mod += "\n".join(blocks)
        _write(f"tests/api/test_api_{stem}.py", mod)

    src_path.unlink()
    print("split test_api.py")


def main() -> None:
    split_run_escalated_display()
    split_workflows()
    split_timeline_misc()
    split_test_api()


if __name__ == "__main__":
    main()

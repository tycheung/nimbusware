from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSOLE = ROOT / "packages/nimbusware_console"


def _split_explainer(
    *,
    module: str,
    slices: tuple[tuple[str, int, int, str], ...],
    init_imports: tuple[str, ...],
) -> None:
    src_path = CONSOLE / f"{module}.py"
    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    header_end = next(
        i for i, line in enumerate(lines) if line.startswith("def ") or line.startswith("class ")
    )
    header = "".join(lines[:header_end])

    pkg = CONSOLE / module
    pkg.mkdir(exist_ok=True)

    for filename, start, end, extra_imports in slices:
        chunk = "".join(lines[start - 1 : min(end - 1, len(lines))])
        body = header + extra_imports + (
            "\n" if extra_imports and not extra_imports.endswith("\n") else ""
        ) + chunk
        (pkg / filename).write_text(body, encoding="utf-8")

    init = ""
    for name in init_imports:
        init += f"from nimbusware_console.{module}.{name} import *  # noqa: F403\n"
    (pkg / "__init__.py").write_text(init, encoding="utf-8")

    src_path.write_text(
        f"from nimbusware_console.{module} import *  # noqa: F403\n",
        encoding="utf-8",
    )


def _split_submodule(
    *,
    package: str,
    submodule: str,
    slices: tuple[tuple[str, int, int, str], ...],
    init_imports: tuple[str, ...],
) -> None:
    src_path = CONSOLE / package / f"{submodule}.py"
    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    header_end = next(
        i for i, line in enumerate(lines) if line.startswith("def ") or line.startswith("class ")
    )
    header = "".join(lines[:header_end])

    subpkg = CONSOLE / package / submodule
    subpkg.mkdir(exist_ok=True)

    for filename, start, end, extra_imports in slices:
        chunk = "".join(lines[start - 1 : min(end - 1, len(lines))])
        body = header + extra_imports + (
            "\n" if extra_imports and not extra_imports.endswith("\n") else ""
        ) + chunk
        (subpkg / filename).write_text(body, encoding="utf-8")

    init = ""
    for name in init_imports:
        init += (
            f"from nimbusware_console.{package}.{submodule}.{name} import *  # noqa: F403\n"
        )
    (subpkg / "__init__.py").write_text(init, encoding="utf-8")

    src_path.write_text(
        f"from nimbusware_console.{package}.{submodule} import *  # noqa: F403\n",
        encoding="utf-8",
    )


def main() -> None:
    _split_explainer(
        module="preflight_cross_run_display",
        slices=(
            ("history.py", 10, 235, ""),
            ("fetch.py", 235, 261, ""),
            ("trend.py", 261, 389, ""),
            (
                "operator_metrics.py",
                389,
                477,
                "from nimbusware_console.preflight_cross_run_display.trend import (\n"
                "    preflight_cross_run_trend_export_filename_slug,\n"
                ")\n",
            ),
            (
                "depth_captions.py",
                477,
                9999,
                "from nimbusware_console.preflight_cross_run_display.trend import (\n"
                "    preflight_cross_run_trend_summary,\n"
                ")\n",
            ),
        ),
        init_imports=("history", "fetch", "trend", "operator_metrics", "depth_captions"),
    )

    _split_explainer(
        module="prune_status_display",
        slices=(
            ("status_captions.py", 16, 295, ""),
            (
                "inventory_captions.py",
                295,
                424,
                "from nimbusware_console.prune_status_display.status_captions import (\n"
                "    _parse_wrote_at,\n"
                ")\n",
            ),
            (
                "metrics.py",
                424,
                9999,
                "from nimbusware_console.prune_status_display.status_captions import (\n"
                "    _parse_wrote_at,\n"
                ")\n",
            ),
        ),
        init_imports=("status_captions", "inventory_captions", "metrics"),
    )

    _split_explainer(
        module="run_list_pagination_display",
        slices=(
            ("list_captions.py", 11, 280, ""),
            ("run_detail_summary.py", 280, 405, ""),
            (
                "timeline_events.py",
                405,
                9999,
                "from nimbusware_console.run_list_pagination_display.run_detail_summary import (\n"
                "    run_detail_summary_export_filename_slug,\n"
                ")\n",
            ),
        ),
        init_imports=("list_captions", "run_detail_summary", "timeline_events"),
    )

    _split_explainer(
        module="agent_evaluator_display",
        slices=(
            ("captions.py", 44, 257, ""),
            (
                "metrics.py",
                257,
                9999,
                "from nimbusware_console.agent_evaluator_display.captions import (\n"
                "    agent_evaluator_timeline_export_filename_slug,\n"
                ")\n",
            ),
        ),
        init_imports=("captions", "metrics"),
    )

    _split_submodule(
        package="integrator_gate",
        submodule="latest_delta",
        slices=(
            ("exports.py", 25, 179, ""),
            ("latest.py", 179, 485, ""),
            ("delta.py", 485, 9999, ""),
        ),
        init_imports=("exports", "latest", "delta"),
    )

    _split_submodule(
        package="integrator_preview",
        submodule="merge",
        slices=(
            ("diff.py", 37, 112, ""),
            (
                "top_level_captions.py",
                112,
                291,
                "from nimbusware_console.integrator_preview.merge.diff import (\n"
                "    _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS,\n"
                "    _SUBTREE_CHANGED_KEYS_CAP,\n"
                ")\n",
            ),
            (
                "subtree_captions.py",
                291,
                494,
                "from nimbusware_console.integrator_preview.merge.diff import (\n"
                "    _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS,\n"
                "    _SUBTREE_CHANGED_KEYS_CAP,\n"
                ")\n",
            ),
            (
                "attention.py",
                494,
                9999,
                "from nimbusware_console.integrator_preview.merge.diff import (\n"
                "    _SUBTREE_CHANGED_KEYS_CAP,\n"
                ")\n",
            ),
        ),
        init_imports=("diff", "top_level_captions", "subtree_captions", "attention"),
    )

    _split_submodule(
        package="persona_catalog",
        submodule="summary",
        slices=(
            ("build.py", 17, 254, ""),
            ("metrics_captions.py", 254, 9999, ""),
        ),
        init_imports=("build", "metrics_captions"),
    )

    print("console displays batch2 split done")


if __name__ == "__main__":
    main()

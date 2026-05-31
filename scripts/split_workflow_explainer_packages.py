"""Split monolithic workflow explainer modules into packages with facades."""

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
        body = header + extra_imports + ("\n" if extra_imports and not extra_imports.endswith("\n") else "") + chunk
        (pkg / filename).write_text(body, encoding="utf-8")

    init = f'"""Workflow explainer package for ``{module}``."""\n\n'
    for name in init_imports:
        init += f"from nimbusware_console.{module}.{name} import *  # noqa: F403\n"
    (pkg / "__init__.py").write_text(init, encoding="utf-8")

    src_path.write_text(
        f"from nimbusware_console.{module} import *  # noqa: F403\n",
        encoding="utf-8",
    )


def main() -> None:
    _split_explainer(
        module="integrator_threshold_explainer",
        slices=(
            ("snapshots.py", 36, 194, ""),
            ("captions.py", 194, 305, ""),
            (
                "payload.py",
                305,
                393,
                "from nimbusware_console.integrator_threshold_explainer.snapshots import (\n"
                "    _emit_integrator_gate_breakdown,\n"
                "    _env_min_score_to_pass_breakdown,\n"
                "    _thresholds_snapshot,\n"
                ")\n",
            ),
            ("exports.py", 393, 425, ""),
            ("metrics.py", 425, 9999, ""),
        ),
        init_imports=("snapshots", "captions", "payload", "exports", "metrics"),
    )

    _split_explainer(
        module="security_scan_metadata_workflow_explainer",
        slices=(
            ("env.py", 27, 60, ""),
            (
                "payload.py",
                60,
                147,
                "from nimbusware_console.security_scan_metadata_workflow_explainer.env import (\n"
                "    _hermes_attach_security_scan_metadata_env_summary,\n"
                ")\n",
            ),
            ("captions.py", 147, 316, ""),
            ("exports.py", 316, 369, ""),
            ("metrics.py", 369, 9999, ""),
        ),
        init_imports=("env", "payload", "captions", "exports", "metrics"),
    )

    _split_explainer(
        module="agent_evaluator_workflow_explainer",
        slices=(
            ("env.py", 25, 122, ""),
            ("captions.py", 122, 377, ""),
            (
                "payload.py",
                377,
                467,
                "from nimbusware_console.agent_evaluator_workflow_explainer.env import (\n"
                "    _would_emit_agent_evaluator_stage,\n"
                "    _would_emit_llm_evaluation,\n"
                ")\n",
            ),
            ("exports.py", 467, 499, ""),
            ("metrics.py", 499, 9999, ""),
        ),
        init_imports=("env", "captions", "payload", "exports", "metrics"),
    )

    _split_explainer(
        module="escalation_suppress_workflow_explainer",
        slices=(
            ("helpers.py", 34, 53, ""),
            (
                "payload.py",
                53,
                243,
                "from nimbusware_console.escalation_suppress_workflow_explainer.helpers import (\n"
                "    _age_seconds_utc,\n"
                ")\n",
            ),
            ("captions.py", 243, 559, ""),
            ("exports.py", 559, 595, ""),
            ("metrics.py", 595, 733, ""),
            ("policy_tables.py", 733, 9999, ""),
        ),
        init_imports=("helpers", "payload", "captions", "exports", "metrics", "policy_tables"),
    )

    _split_explainer(
        module="self_refinement_workflow_explainer",
        slices=(
            ("env.py", 36, 245, ""),
            (
                "captions.py",
                245,
                377,
                "from nimbusware_console.self_refinement_workflow_explainer.env import (\n"
                "    _hermes_self_refinement_stage_marker_env_summary,\n"
                "    _hermes_self_refinement_ungated_loop_env_summary,\n"
                ")\n",
            ),
            (
                "payload.py",
                377,
                441,
                "from nimbusware_console.self_refinement_workflow_explainer.env import (\n"
                "    _hermes_self_refinement_ungated_loop_env_summary,\n"
                "    _load_policy_or_default,\n"
                "    _marker_preview,\n"
                ")\n",
            ),
            ("compare.py", 441, 541, ""),
            ("exports.py", 541, 573, ""),
            ("metrics.py", 573, 709, ""),
            ("marker_exports.py", 709, 9999, ""),
        ),
        init_imports=(
            "env",
            "captions",
            "payload",
            "compare",
            "exports",
            "metrics",
            "marker_exports",
        ),
    )

    _split_explainer(
        module="universal_critique_workflow_explainer",
        slices=(
            ("helpers.py", 29, 79, ""),
            (
                "payload.py",
                79,
                182,
                "from nimbusware_console.universal_critique_workflow_explainer.helpers import (\n"
                "    _universal_critique_top_level_enabled_false_count,\n"
                "    _universal_critique_top_level_enabled_true_count,\n"
                "    _universal_critique_top_level_enabled_unset_mapping_count,\n"
                "    _universal_critique_top_level_list_child_count,\n"
                "    _universal_critique_top_level_mapping_child_count,\n"
                "    _universal_critique_top_level_nonempty_count,\n"
                "    _universal_critique_top_level_scalar_leaf_count,\n"
                ")\n",
            ),
            (
                "captions.py",
                182,
                454,
                "from nimbusware_console.universal_critique_workflow_explainer.compare import (\n"
                "    universal_critique_env_override_deltas,\n"
                ")\n",
            ),
            ("compare.py", 454, 531, ""),
            ("exports.py", 531, 563, ""),
            ("metrics.py", 563, 9999, ""),
        ),
        init_imports=("helpers", "payload", "captions", "compare", "exports", "metrics"),
    )

    print("workflow explainer packages split done")


if __name__ == "__main__":
    main()

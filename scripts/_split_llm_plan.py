"""Split llm_plan.py into hermes_orchestrator/llm/ with patch-compatible shim."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages" / "hermes_orchestrator" / "llm_plan.py"
PKG = REPO / "packages" / "hermes_orchestrator" / "llm"

HEADER_END = 29
COMMON_IMPORT = "from hermes_orchestrator.llm.common import *  # noqa: F403\n\n"
PATCH_HELPER = (
    "def _ollama_chat_json(*args: object, **kwargs: object) -> object:\n"
    "    import hermes_orchestrator.llm_plan as _patch\n"
    "    return _patch.ollama_chat_json(*args, **kwargs)\n\n"
)

# (filename, list of (start, end) 1-based inclusive line ranges)
MODULE_RANGES: list[tuple[str, list[tuple[int, int]]]] = [
    ("common.py", [(32, 187)]),
    ("plan_stage.py", [(188, 391)]),
    ("implementation_critique.py", [(238, 294), (392, 502)]),
    ("test_writer_critique.py", [(503, 667)]),
    ("planner_critique.py", [(668, 831)]),
    ("frontend_writer_critique.py", [(832, 984)]),
    ("module_integrator_critique.py", [(985, 1137)]),
    ("self_refinement_critique.py", [(1138, 1295)]),
    ("agent_evaluator.py", [(1296, 99999)]),
]


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    header = lines[0:HEADER_END]
    PKG.mkdir(parents=True, exist_ok=True)

    for fname, ranges in MODULE_RANGES:
        chunks: list[str] = []
        for start, end in ranges:
            chunks.extend(lines[start - 1 : min(end, len(lines))])
        if fname != "common.py":
            body = (
                header
                + [COMMON_IMPORT, PATCH_HELPER]
                + [ln.replace("ollama_chat_json(", "_ollama_chat_json(") for ln in chunks]
            )
        else:
            body = header + chunks + [
                "\n__all__ = [name for name in globals() if not name.startswith('__')]\n"
            ]
        (PKG / fname).write_text("".join(body), encoding="utf-8")

    (PKG / "__init__.py").write_text(
        '"""LLM plan/critique stages — composed facade."""\n\n'
        "from hermes_orchestrator.llm.agent_evaluator import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.common import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.frontend_writer_critique import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.implementation_critique import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.module_integrator_critique import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.plan_stage import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.planner_critique import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.self_refinement_critique import *  # noqa: F403\n"
        "from hermes_orchestrator.llm.test_writer_critique import *  # noqa: F403\n",
        encoding="utf-8",
    )

    SRC.write_text(
        '"""LLM-backed plan/critique — stable import and patch target."""\n\n'
        "from hermes_orchestrator.ollama_chat import ollama_chat_json\n"
        "from hermes_orchestrator.llm import *  # noqa: F403\n",
        encoding="utf-8",
    )
    print("llm split ok")


if __name__ == "__main__":
    main()

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_STAGES = _REPO / "packages" / "nimbusware_research" / "stages.py"

# Call sites allowed to read business_prompt (classification / routing only).
_ALLOWED_LINES = {37, 38, 39, 40, 41, 42}


def test_stages_business_prompt_only_via_wrap() -> None:
    tree = ast.parse(_STAGES.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "get"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "requirements"
        ):
            continue
        if len(node.args) != 1 or not isinstance(node.args[0], ast.Constant):
            continue
        if node.args[0].value != "business_prompt":
            continue
        line = node.lineno
        if line in _ALLOWED_LINES:
            continue
        parent_fn = _enclosing_function(tree, line)
        if parent_fn and _function_assigns_to_summary_without_wrap(tree, parent_fn, line):
            offenders.append(f"line {line} in {parent_fn}")
    assert not offenders, "raw business_prompt may reach summaries: " + ", ".join(offenders)


def _enclosing_function(tree: ast.Module, line: int) -> str | None:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= line <= getattr(node, "end_lineno", node.lineno + 9999):
                return node.name
    return None


def _function_assigns_to_summary_without_wrap(
    tree: ast.Module, func_name: str, prompt_line: int
) -> bool:
    fn = next(
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func_name
    )
    wrap_seen = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "wrap_researcher_prompt":
                wrap_seen = True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and "summary" in target.id:
                    if node.lineno >= prompt_line and not wrap_seen:
                        return True
    return False

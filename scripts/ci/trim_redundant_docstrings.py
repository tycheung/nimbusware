from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TARGETS = (_ROOT / "packages", _ROOT / "tests", _ROOT / "scripts")

_SKIP_REL = {
    "packages/nimbusware_api/schemas/openapi_problem.py",
    "packages/nimbusware_api/schemas/openapi_route_docs.py",
    "scripts/ci/coverage_package_floors.py",
    "scripts/ci/mypy_ci_targets.py",
    "scripts/ops/e2e_smoke.py",
    "scripts/ops/prune_scraper_artifacts.py",
}

_REDUNDANT_PREFIXES = (
    "Unit tests for ",
    "Integration tests for ",
    "API tests for ",
    "Console tests for ",
    "Contract tests for ",
    "Tests for ",
    "Postgres ",
    "Focused smoke tests to ratchet",
    "Fail when key packages fall below",
    "Trim redundant one-line module docstrings",
    "Smoke-test ",
    "Pilot: ",
    "Replay a run's event-store rows",
    "Remove scraper response artifact files",
    "Rebuild bundle FAISS index when catalog",
    "Nimbusware end-to-end operator smoke checks",
    "Smoke coverage for ",
    "Additional coverage for ",
    "AST guard: ",
    "EventStore protocol and ",
    "MCP stdio bridge for ",
    "Backward-compatible re-export shim",
    "CLI entrypoint for ",
    "CLI: ",
    "re-export facade",
    "Internal pipeline mixins",
    "delegates to ",
    "composed facade",
    "Read-only ",
    "Load launch eval ",
    "Minimal Ollama ",
    "Map verifier logs",
    "Library-level tests for ",
    "Script-level tests for ",
    "Orchestrator outbound HTTP",
    "per-tool exit codes",
    "workflow ``",
    "Egress allowlist",
    "Campaign dispatch worker journey",
    "Demo application module",
    "Outbound HTTP gated by",
    "Auto-escalation thresholds from",
    "Enterprise routes under",
    "Maker slice execution boundary",
    "Product edition gate",
    "Integrator gate —",
    "Campaign driver state machine",
    "MVP run lifecycle:",
    "Legacy Enterprise fleet UI",
    "On-disk scraper artifact",
    "Deterministic PASS plan stage",
    "Unified diff or scope",
    "Hash-based unit vector",
    "Call Ollama ``/api/embeddings``",
    "NIMBUSWARE_SELF_REFINEMENT",
    "yaml.YAMLError``",
    "Orchestrator outbound HTTP",
    "Materialized configuration for",
    "Nimbusware platform edition",
)


def _rel(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _first_line(doc: str) -> str:
    return doc.strip().splitlines()[0].strip()


def _should_drop(doc: str) -> bool:
    stripped = doc.strip()
    if not stripped:
        return False
    head = _first_line(doc)
    if any(head.startswith(p) for p in _REDUNDANT_PREFIXES):
        return True
    if " projections — delegates to " in head:
        return True
    if head.endswith(" — single source of truth for API projections."):
        return True
    if head.startswith("Pytest:"):
        return True
    if head.endswith(" module.") or head.endswith(" package."):
        return True
    if head.startswith("GET /") and len(head) < 100:
        return True
    if head.endswith(" .") or head.endswith("."):
        if head.startswith("LLM-backed plan stage"):
            return True
    if head == "Backward-compatible shim.":
        return True
    if head.startswith("Mechanical split of ") or head.startswith("Split "):
        return True
    if " direct contract" in head or " direct-contract" in head:
        return True
    if head.endswith(" contract.") or head.endswith(" contracts."):
        return True
    if head.endswith(" composite.") or head.endswith(" matrix."):
        return True
    if head.endswith(" closure."):
        return True
    if head.startswith("Wrapper so ``pytest"):
        return True
    if head.endswith(" trilogy."):
        return True
    if head.endswith(" propagation."):
        return True
    if re.search(r"\(fo\d+[^)]*\)", head) and len(head) < 100:
        return True
    if "\n" in stripped:
        return False
    if len(stripped) > 120:
        return True
    if (
        head.endswith(".")
        and "``" not in head
        and " — " not in head
        and len(head.split()) <= 12
        and head.count(".") == 1
    ):
        return True
    return False


_VERBOSE_MULTILINE_MARKERS = (
    "Paired critics come from",
    "Returns ``True`` if critic + gate events were appended",
    "Gating (``NIMBUSWARE_",
    "``None`` and empty lists are treated as",
    "without juggling ``None`` checks",
    "Returns a structured result with ``local_removed``",
    "When ``dry_run`` is true, counts stale files",
    "Missing file or invalid profile returns",
    "Appends ``self_refinement.critique``",
    "Delegate to cloud routing",
    "Emit paired critics + gate for",
)

_ONELINE_FUNCTION_DOC_PREFIXES = (
    "Raise if ",
    "Return ",
    "True when ",
    "Parse ",
    "Emit ",
    "Merge ",
    "Record ",
    "Fan-out ",
    "Load ",
    "Derive ",
    "Add ",
    "Set or add ",
    "Directory containing ",
    "RFC 5988 ",
    "Best-effort ",
    "Compact timeline ",
    "Optional ",
    "Stage names ",
    "Freeze-safe ",
    "Validate optional ",
    "When workflow ",
    "Sequential plan ",
    "Lowercase hostnames",
    "Treat missing ",
    "Named export/",
    "Bind ``{slug}_*``",
    "Split `serialize_event",
    "Reconstruct dict for ",
    "Hash-based unit vector",
    "Call Ollama ``/api/embeddings``",
    "Latest ``",
    "Structured ",
    "Write ",
    "Run ",
    "Hook ",
    "Static ",
    "Mandatory ",
    "Build ",
    "Admin-only ",
    "Stable ",
    "Parsed ``",
    "Default ",
    "Data-driven ",
    "When true,",
    "Map ",
    "Normalize ",
    "Combined ",
    "Keep ",
    "Replace ",
    "Extract ",
    "Prune ",
    "List ",
    "Compare ",
    "Scan ",
    "Resolve ",
    "Identical ",
    "Nimbusware repo root",
    "Directory used when",
    "Named export/",
)


def _should_strip_oneline_function_doc(doc: str) -> bool:
    stripped = doc.strip()
    if not stripped or "\n" in stripped:
        return False
    head = _first_line(stripped)
    if len(head) > 150:
        return False
    return any(head.startswith(p) for p in _ONELINE_FUNCTION_DOC_PREFIXES)


def _should_strip_verbose_multiline(doc: str) -> bool:
    stripped = doc.strip()
    if "\n" not in stripped:
        return False
    return any(m in stripped for m in _VERBOSE_MULTILINE_MARKERS)


def _strip_oneline_class_docstrings(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    lines = text.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.body or len(node.body) != 1:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        doc = first.value.value
        if not _should_strip_oneline_function_doc(doc):
            continue
        removals.append((first.lineno - 1, first.end_lineno))
    if not removals:
        return False
    for start, end in sorted(removals, reverse=True):
        lines = lines[:start] + lines[end:]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def _strip_oneline_function_docstrings(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    lines = text.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.body:
            continue
        if len(node.body) == 1:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        doc = first.value.value
        if not _should_strip_oneline_function_doc(doc):
            continue
        removals.append((first.lineno - 1, first.end_lineno))
    if not removals:
        return False
    for start, end in sorted(removals, reverse=True):
        lines = lines[:start] + lines[end:]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def _strip_verbose_multiline_docstrings(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    lines = text.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        doc = first.value.value
        if not _should_strip_verbose_multiline(doc):
            continue
        removals.append((first.lineno - 1, first.end_lineno))
    if not removals:
        return False
    for start, end in sorted(removals, reverse=True):
        lines = lines[:start] + lines[end:]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def _is_contract_test(path: Path) -> bool:
    name = path.name
    return "contract" in name or "matrix" in name


def _strip_contract_test_docstrings(path: Path) -> bool:
    if not _is_contract_test(path):
        return False
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    lines = text.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        doc = first.value.value.strip()
        if not doc or "\n" in doc:
            if len(doc.splitlines()) <= 3:
                continue
        start = first.lineno - 1
        end = first.end_lineno
        removals.append((start, end))
    if not removals:
        return False
    for start, end in sorted(removals, reverse=True):
        lines = lines[:start] + lines[end:]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def _strip_test_module_docstring(path: Path) -> bool:
    rel = _rel(path)
    if not rel.startswith("tests/") or rel.startswith("tests/fixtures/"):
        return False
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    if not tree.body:
        return False
    first = tree.body[0]
    if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
        return False
    if not isinstance(first.value.value, str):
        return False
    doc = first.value.value.strip()
    if not doc:
        return False
    if "\n" in doc and len(doc.splitlines()) > 3:
        return False
    if len(doc) > 160:
        return False
    lines = text.splitlines(keepends=True)
    start = first.lineno - 1
    end = first.end_lineno
    new_lines = lines[:start] + lines[end:]
    while len(new_lines) > 1 and new_lines[0].strip() == "":
        new_lines = new_lines[1:]
    path.write_text("".join(new_lines), encoding="utf-8")
    return True


def _process(path: Path) -> bool:
    rel = _rel(path)
    if rel in _SKIP_REL:
        return False
    if rel.startswith("tests/fixtures/"):
        return False
    if "_archive" in path.parts:
        return False
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    if not tree.body:
        return False
    first = tree.body[0]
    if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
        return False
    if not isinstance(first.value.value, str):
        return False
    doc = first.value.value
    if not _should_drop(doc):
        return False
    lines = text.splitlines(keepends=True)
    start = first.lineno - 1
    end = first.end_lineno
    new_lines = lines[:start] + lines[end:]
    while len(new_lines) > 1 and new_lines[0].strip() == "":
        new_lines = new_lines[1:]
    path.write_text("".join(new_lines), encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for root in _TARGETS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            file_changed = False
            if _process(path):
                file_changed = True
            if _strip_contract_test_docstrings(path):
                file_changed = True
            if _strip_test_module_docstring(path):
                file_changed = True
            if _strip_oneline_class_docstrings(path):
                file_changed = True
            if _strip_oneline_function_docstrings(path):
                file_changed = True
            if _strip_verbose_multiline_docstrings(path):
                file_changed = True
            if file_changed:
                changed += 1
                print(_rel(path))
    print(f"trimmed {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

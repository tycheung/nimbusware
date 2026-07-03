#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_count_loc():
    spec = importlib.util.spec_from_file_location(
        "count_loc", ROOT / "scripts" / "ci" / "count_loc.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["count_loc"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    count_loc = _load_count_loc()
    source, generated = count_loc.collect(
        git_tracked=False,
        include_docs=False,
        include_config=False,
    )
    packages_py = sum(
        f.non_blank for f in source if f.path.startswith("packages/") and f.extension == ".py"
    )
    tests_py = sum(
        f.non_blank for f in source if f.path.startswith("tests/") and f.extension == ".py"
    )
    scripts_py = sum(
        f.non_blank for f in source if f.path.startswith("scripts/") and f.extension == ".py"
    )
    generated_nb = sum(f.non_blank for f in generated)
    summary = {
        "packages_python_non_blank_lines": packages_py,
        "tests_python_non_blank_lines": tests_py,
        "scripts_python_non_blank_lines": scripts_py,
        "generated_marked_non_blank_lines": generated_nb,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

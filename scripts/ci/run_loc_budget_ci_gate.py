#!/usr/bin/env python3
"""CI gate: fail when packages/ Python LOC exceeds the committed baseline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "scripts" / "ci" / "loc_baseline.json"


def _packages_python_non_blank_from_count_loc() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ci" / "count_loc.py"), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout)
        raise SystemExit(proc.returncode)
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "count_loc",
        ROOT / "scripts" / "ci" / "count_loc.py",
    )
    assert spec is not None and spec.loader is not None
    count_loc = importlib.util.module_from_spec(spec)
    sys.modules["count_loc"] = count_loc
    spec.loader.exec_module(count_loc)
    source, _generated = count_loc.collect(
        git_tracked=False,
        include_docs=False,
        include_config=False,
    )
    return sum(
        f.non_blank for f in source if f.path.startswith("packages/") and f.extension == ".py"
    )


def _load_baseline() -> int:
    if not BASELINE_PATH.is_file():
        return 94392
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return int(data["packages_python_non_blank_lines"])


def main() -> int:
    baseline = _load_baseline()
    current = _packages_python_non_blank_from_count_loc()
    if current > baseline:
        print(
            f"packages/ Python LOC budget exceeded: {current:,} non-blank lines "
            f"(baseline {baseline:,}). Update scripts/ci/loc_baseline.json only when "
            "growth is intentional.",
            file=sys.stderr,
        )
        return 1
    print(f"loc budget gate: ok ({current:,} / {baseline:,} non-blank Python lines in packages/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

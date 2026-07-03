from __future__ import annotations

from pathlib import Path


def test_no_legacy_root_level_test_modules() -> None:
    tests_root = Path(__file__).resolve().parents[1]
    offenders = sorted(p.name for p in tests_root.glob("test_*.py"))
    assert not offenders, (
        "Move tests into themed folders (tests/unit, tests/api_http, etc.): " + ", ".join(offenders)
    )

#!/usr/bin/env python3
"""Split tests/api/test_api.py into themed modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tests/api/test_api.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

CONFTEST = "".join(lines[:45]).replace(
    "@pytest.fixture\ndef client() -> TestClient:\n    with TestClient(app) as c:\n        yield c\n\n\n",
    "",
)
CONFTEST = CONFTEST.rstrip() + "\n\n\n@pytest.fixture\ndef client() -> TestClient:\n    with TestClient(app) as c:\n        yield c\n"
(ROOT / "tests/api/conftest.py").write_text(CONFTEST, encoding="utf-8")

MODULES: list[tuple[str, int, int]] = [
    ("test_api_bundles.py", 58, 271),
    ("test_api_openapi.py", 273, 484),
    ("test_api_timeline.py", 486, 1515),
    ("test_api_runs.py", 1517, len(lines)),
]

STUB = """from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow

"""

for rel, start, end in MODULES:
    body = "".join(lines[start - 1 : end])
    if rel == "test_api_bundles.py":
        stub = STUB
    else:
        stub = STUB.replace("from uuid import UUID, uuid4\n\n", "")
    (ROOT / "tests/api" / rel.split("/")[-1]).write_text(stub + body, encoding="utf-8")
    print(f"wrote {rel} ({end - start + 1} lines)")

SRC.unlink()
print("removed test_api.py")

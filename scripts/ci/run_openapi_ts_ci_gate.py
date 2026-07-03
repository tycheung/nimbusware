#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "NIMBUSWARE_OPENAPI_TS_REQUIRE_FULL": "1"}
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "codegen" / "openapi_to_ts.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout)
        return proc.returncode
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        sys.stderr.write(proc.stdout or "openapi_to_ts produced no JSON status line\n")
        return 1
    schema = Path(payload.get("path", ""))
    if not schema.is_file():
        sys.stderr.write(f"missing generated schema: {schema}\n")
        return 1
    source = payload.get("source", "unknown")
    if source != "openapi-typescript":
        sys.stderr.write(
            f"openapi TS gate requires openapi-typescript output (got {source!r}); install Node/npx\n"
        )
        return 1
    print(f"openapi TS gate OK ({source})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

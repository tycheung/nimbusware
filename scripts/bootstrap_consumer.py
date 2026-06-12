#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "packages" / "nimbusware_bootstrap"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from nimbusware_bootstrap.cli import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())

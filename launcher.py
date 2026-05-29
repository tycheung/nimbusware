#!/usr/bin/env python3
"""Nimbusware desktop launcher — install, update, and run."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PACKAGES = _ROOT / "packages"
if str(_PACKAGES) not in sys.path:
    sys.path.insert(0, str(_PACKAGES))

from nimbusware_env.launcher_app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

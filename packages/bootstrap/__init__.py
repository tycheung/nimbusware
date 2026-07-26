"""Bootstrap package shim for ``packages/`` on PYTHONPATH.

Hatch still builds from the nested ``bootstrap/bootstrap/`` tree; pytest/poetry
put ``packages/`` on ``sys.path``, so this outer ``__init__`` redirects
``__path__`` at the nested sources.
"""

from __future__ import annotations

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent / "bootstrap")]

from bootstrap.cli import run


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))

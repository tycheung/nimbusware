from __future__ import annotations

from bootstrap.cli import run


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))

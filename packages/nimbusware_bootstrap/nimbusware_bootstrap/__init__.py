from __future__ import annotations

from nimbusware_bootstrap.cli import run


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))

from __future__ import annotations

import sys

from nimbusware_env.run_app import main as run_main


def main(argv: list[str] | None = None) -> int:
    args = ["--admin", *(argv if argv is not None else sys.argv[1:])]
    return run_main(args)


if __name__ == "__main__":
    raise SystemExit(main())

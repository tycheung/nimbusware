from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from nimbusware_maker.quick_mode import apply_quick_mode_env


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Nimbusware Maker Streamlit app.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="In-memory event store, stub critics, quick_local workflow (no Postgres).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args, streamlit_argv = parser.parse_known_args(raw)
    if args.quick:
        apply_quick_mode_env()
    app = Path(__file__).resolve().parent / "app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app), *streamlit_argv],
        check=True,
    )


if __name__ == "__main__":
    main()

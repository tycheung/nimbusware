from __future__ import annotations

import faulthandler
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / ".ci_unit_full.log"
ERR = ROOT / ".ci_unit_full.err"
STALL_S = 90


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    ERR.write_text("", encoding="utf-8")
    cmd = [
        sys.executable,
        "-u",
        "-c",
        "\n".join(
            [
                "import faulthandler, sys",
                "faulthandler.enable()",
                "faulthandler.dump_traceback_later(60, repeat=True, file=sys.stderr)",
                "class Tracker:",
                "    def pytest_runtest_logstart(self, nodeid, location):",
                "        print(f'START {nodeid}', flush=True)",
                "import pytest",
                "raise SystemExit(pytest.main(",
                "    ['tests/unit', '-q', '--tb=line', '-p', 'no:cacheprovider', '-p', 'no:benchmark'],",
                "    plugins=[Tracker()],",
                "))",
            ]
        ),
    ]
    with LOG.open("w", encoding="utf-8") as out, ERR.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=out,
            stderr=err,
            env={
                **dict(**{k: v for k, v in __import__("os").environ.items()}),
                "PYTHONUNBUFFERED": "1",
                "NIMBUSWARE_REPO_ROOT": str(ROOT).replace("\\", "/"),
                "NIMBUSWARE_SKIP_PREFLIGHT": "1",
            },
        )
    last_size = -1
    stall = 0.0
    t0 = time.monotonic()
    while proc.poll() is None:
        time.sleep(15)
        size = LOG.stat().st_size if LOG.is_file() else 0
        if size == last_size:
            stall += 15
        else:
            stall = 0
            last_size = size
        elapsed = int(time.monotonic() - t0)
        tail = ""
        if LOG.is_file():
            lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = lines[-1] if lines else ""
        print(f"t={elapsed}s size={size} stall={int(stall)}s last={tail[:120]}", flush=True)
        if stall >= STALL_S:
            print("HANG detected — killing", flush=True)
            proc.kill()
            proc.wait(timeout=10)
            print(LOG.read_text(encoding="utf-8", errors="replace")[-2000:])
            print("--- stderr ---")
            print(ERR.read_text(encoding="utf-8", errors="replace")[-4000:])
            return 124
    code = proc.returncode or 0
    print(f"exit={code}", flush=True)
    print(LOG.read_text(encoding="utf-8", errors="replace")[-2500:])
    err_txt = ERR.read_text(encoding="utf-8", errors="replace")
    if err_txt.strip():
        print("--- stderr ---")
        print(err_txt[-2000:])
    return code


if __name__ == "__main__":
    raise SystemExit(main())

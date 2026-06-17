#!/usr/bin/env python3
"""Fleet SSH hardware probe for scheduled CI (see docs/deploy/ssh-hardware-probe.md)."""

from __future__ import annotations

import json

from nimbusware_hw.fleet_hardware import run_probe_matrix


def main() -> int:
    summary = run_probe_matrix()
    print(json.dumps(summary, sort_keys=True))
    if summary.get("skipped"):
        print("Skip: no NIMBUSWARE_HW_FLEET_HOSTS or NIMBUSWARE_HW_SSH_HOST configured")
        return 0
    return 1 if int(summary.get("failed") or 0) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

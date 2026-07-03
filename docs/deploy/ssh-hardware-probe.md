# SSH hardware probe (Enterprise fleet)

Live tier checks for remote GPU/CPU workers over SSH. Code lives in `packages/hw/` (`probe.py`, `ssh_probe.py`, `fleet_hardware.py`).

## GitHub Actions

Workflow: [`.github/workflows/ssh_hardware_probe.yml`](../../.github/workflows/ssh_hardware_probe.yml)

| Trigger | Behavior |
|---------|----------|
| **Weekly schedule** (Sunday 04:30 UTC) | Fails the job on probe regression; opens a GitHub issue labelled `ssh-probe-failure`. |
| **workflow_dispatch** | Same probe matrix; job uses `continue-on-error` so manual runs do not block the repo. |

Entrypoint: `poetry run python scripts/ci/run_ssh_hardware_probe_ci.py` — prints one JSON summary line and exits non-zero when any host fails.

## Secrets and variables

| Name | Required | Notes |
|------|----------|--------|
| `NIMBUSWARE_HW_FLEET_HOSTS` | Preferred | Comma-separated hostnames probed in parallel order (same env as the Admin hardware dashboard). |
| `NIMBUSWARE_HW_SSH_HOST` | Legacy | Single host when `NIMBUSWARE_HW_FLEET_HOSTS` is unset. |
| `NIMBUSWARE_HW_SSH_IDENTITY` | Yes (live SSH) | PEM private key material for `ssh -i`. Rotate on the same cadence as other deploy keys. |
| `NIMBUSWARE_HW_EXPECT_MIN_TIER` | Optional (repo **variable**) | `weak`, `medium`, or `strong` — scheduled runs fail when a host classifies below this tier even if SSH succeeds. |

When neither fleet nor single-host secret is set, the workflow skips with exit code 0.

## Local / operator run

```bash
export NIMBUSWARE_EDITION=enterprise
export NIMBUSWARE_HW_FLEET_HOSTS=gpu-a.example,gpu-b.example
export NIMBUSWARE_HW_SSH_IDENTITY=/path/to/deploy_key
# optional regression guard:
export NIMBUSWARE_HW_EXPECT_MIN_TIER=medium

poetry run python scripts/ci/run_ssh_hardware_probe_ci.py
```

PR CI sets `NIMBUSWARE_HW_SSH_MOCK=1` so unit tests never open real SSH sessions.

## Tier assertions

Each host is classified `weak`, `medium`, or `strong` from remote `/proc/meminfo` and CPU count (see `classify_tier` in `probe.py`). A host **fails** when:

1. The SSH probe returns errors (unreachable host, parse failure, missing enterprise edition), or
2. `NIMBUSWARE_HW_EXPECT_MIN_TIER` is set and the classified tier ranks lower than the expectation.

Set the repo variable to the minimum tier your fleet should sustain (for example `medium` for 16 GB / 4 CPU workers).

## Rotation checklist

1. Generate a new deploy key on the target hosts (`authorized_keys`).
2. Update the `NIMBUSWARE_HW_SSH_IDENTITY` secret in GitHub.
3. Run **workflow_dispatch** once and confirm the JSON summary shows `"failed": 0`.
4. Revoke the previous key on all fleet hosts.

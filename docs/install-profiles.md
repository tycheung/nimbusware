# Install profiles and setup bundles

Nimbusware v1.2+ installer supports two **orthogonal** dimensions:

| Dimension | Values | Controls |
|-----------|--------|----------|
| **Setup bundle** | `default` \| `enterprise` | Edition, autopilot/enforcement defaults, slice budget, collab, audit retention |
| **Install profile** | `recommended` \| `barebones` | Ollama + model download size (ADR 024) |

## Setup bundles

| Bundle | CLI | Edition | Use case |
|--------|-----|---------|----------|
| **default** | `--setup-bundle default` (default) | Individual | Solo builders; Safe Coding or Engineer sub-choice on first Maker launch |
| **enterprise** | `--setup-bundle enterprise` | Enterprise | Governed teams — tiny slices, auto-commit, fleet enforcement seeds |

Persisted as `NIMBUSWARE_SETUP_BUNDLE` in `.env`. SSOT: `configs/install/bundles/*.yaml`.

### Default bundle env (summary)

- `NIMBUSWARE_DEFAULT_AUTOPILOT_PROFILE=guided`
- `NIMBUSWARE_DEFAULT_ENFORCEMENT_PROFILE=balanced`
- `NIMBUSWARE_SLICE_AUTO_ADVANCE=0`, `NIMBUSWARE_SLICE_AUTO_COMMIT=0`
- `NIMBUSWARE_COLLAB_ENABLED=0` (Engineer sub-choice enables collab in Maker)

### Enterprise bundle env (summary)

- `NIMBUSWARE_DEFAULT_ENFORCEMENT_PROFILE=platform_grade`
- `NIMBUSWARE_SLICE_BUDGET_PRESET=tiny`, `NIMBUSWARE_SLICE_AUTO_COMMIT=1`
- `NIMBUSWARE_AUDIT_RETENTION_DAYS=90`, `NIMBUSWARE_COLLAB_ENABLED=1`
- Auto `--seed-config` on recommended profile; fleet enforcement default tenant min **8**

## Install profiles (ADR 024)

| Profile | CLI | Behavior |
|---------|-----|----------|
| **recommended** (default) | `--install-profile recommended` | Ollama bootstrap + pull default models; `NIMBUSWARE_USE_LLM=1` when ready |
| **barebones** | `--install-profile barebones` or `--skip-ollama` | Skip Ollama; use Model Hub or `nimbusware-run --quick` |

Profile is persisted as `NIMBUSWARE_INSTALL_PROFILE` in `.env`.

## Interactive install order

1. Setup bundle (default vs enterprise)
2. Install profile (recommended vs barebones)
3. First Maker launch (default bundle only): Safe Coding vs Engineer workspace

## Launcher (desktop)

| Button | Setup bundle | Install profile |
|--------|--------------|-----------------|
| Quick setup | default | barebones |
| Full setup | default | recommended |
| Enterprise setup | enterprise | recommended |

## Examples

```bash
# Individual full local dev
python scripts/install/install_nimbusware.py --setup-bundle default --install-profile recommended

# Enterprise governed install
python scripts/install/install_nimbusware.py --setup-bundle enterprise --install-profile recommended --non-interactive

# Fast CI / cloud-only Individual
python scripts/install/install_nimbusware.py --setup-bundle default --install-profile barebones --skip-postgres
```

## References

- ADR: [`docs/adr/024-install-profiles.md`](adr/024-install-profiles.md), [`docs/adr/027-install-setup-bundles.md`](adr/027-install-setup-bundles.md)
- Timing: [`docs/deploy/first-install-timing.md`](deploy/first-install-timing.md)
- Installer: `scripts/install/install_nimbusware.py`

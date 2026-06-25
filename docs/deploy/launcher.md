# Desktop launcher

Nimbusware ships a small **desktop launcher** (Tkinter) that downloads or clones the repo, runs the universal installer, and starts `run.py` (API + Maker/Admin pywebview shell).

There is **no single binary for all operating systems**. Release builds are per platform; users pick the matching artifact from [GitHub Releases](https://github.com/tycheung/nimbusware/releases) (tag prefix `launcher-v*`).

## End-user flow

```text
Download launcher for your OS
        ↓
Quick setup  →  Poetry deps, barebones profile, default setup bundle (no Postgres/Ollama)
   or
Full setup   →  Poetry + Docker Postgres (when available) + Ollama recommended profile (default bundle)
   or
Enterprise setup  →  Full setup + enterprise edition strict env + fleet seeds
        ↓
Run Nimbusware  →  .venv python run.py  →  API + Maker window
```

**Requirements:** Python 3.10+ on PATH for install; Git *or* automatic GitHub zip fallback; Full setup additionally benefits from Docker and disk space for Ollama models.

## Release artifacts

| OS | CI runner | Binary | Packaged formats |
|----|-----------|--------|------------------|
| Windows x64 | `windows-latest` | `NimbuswareLauncher-windows-x64.exe` | `.zip` |
| macOS arm64/x64 | `macos-14` | `NimbuswareLauncher-macos-*` | `.zip`, `.dmg` |
| Linux x86_64 | `ubuntu-22.04` | `NimbuswareLauncher-linux-x86_64` | `.zip`, `.tar.gz` |

Filenames come from `scripts/publish/launcher_artifact_name.py`.

## Build locally

```bash
# Windows
.\scripts\publish\build_launcher.ps1

# macOS / Linux
./scripts/publish/build_launcher.sh
```

Outputs land in `dist/` with a platform-specific name. Optional packaging:

```bash
poetry run python scripts/publish/package_launcher_release.py   # zip + INSTALL.txt
```

## CI

- **PR gate:** `scripts/ci/run_publish_launcher_ci_gate.py` (main `ci.yml` unit job)
- **Release matrix:** `.github/workflows/publish_launcher.yml` on `workflow_dispatch` or tag `launcher-v*`

## Alternative entry points

| Path | When |
|------|------|
| `poetry run nimbusware-launcher` | Developers with a checkout |
| `pip install nimbusware-bootstrap` + `nimbusware-bootstrap --print-only` | Clean VM; prints launcher URL + curl installer |
| `nimbusware-bootstrap --install` | Remote curl install without GUI |
| `curl …/install_nimbusware.py \| python - …` | Script-only bootstrap |

## Operator notes

- The PyInstaller binary bundles `install_nimbusware.py` only; the full repo is fetched on first setup.
- Linux desktop runs still need GTK/WebKit packages for pywebview (`linux_desktop_deps`).
- Windows runs need WebView2 (Edge Chromium backend).
- Signing/notarization for wide distribution is not automated in CI yet.

See also [getting-started.md](../getting-started.md) and [install-profiles.md](../install-profiles.md).

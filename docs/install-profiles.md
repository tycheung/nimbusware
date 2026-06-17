# Install profiles (recommended vs barebones)

Nimbusware v1.2 universal installer supports two **install profiles**. Edition (Individual vs Enterprise) only changes Postgres/Redis/seed defaults — not the profile names.

## Profiles

| Profile | CLI | Behavior |
|---------|-----|----------|
| **recommended** (default) | `--install-profile recommended` | Ollama bootstrap + pull `llama3.1:8b` and `qwen2.5-coder:14b`; sets `NIMBUSWARE_USE_LLM=1` when bootstrap succeeds |
| **barebones** | `--install-profile barebones` or `--skip-ollama` | Skips Ollama and model pulls; use `nimbusware-run --quick` or [Model Hub](model-hub.md) later |

Profile is persisted as `NIMBUSWARE_INSTALL_PROFILE` in `.env`.

## Edition matrix

| Edition | recommended | barebones |
|---------|-------------|-----------|
| Individual | Default curl one-liner | `--install-profile barebones` |
| Enterprise recommended | Auto `--seed-config` after schema | — |
| Enterprise barebones (non-interactive) | — | Defaults Postgres to Docker when not skipped |

## After install

- **recommended** — Home readiness expects Ollama; preflight can pass when models are loaded.
- **barebones** — Home shows install profile and **Set up local or API LLM** CTA → Model Hub (`#/models`).

## References

- ADR: [`docs/adr/024-install-profiles.md`](adr/024-install-profiles.md)
- Timing budgets: [`docs/deploy/first-install-timing.md`](deploy/first-install-timing.md)
- Installer: `scripts/install/install_nimbusware.py`

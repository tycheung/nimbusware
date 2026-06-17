# ADR 024: Install profiles (recommended vs barebones)

## Status

Accepted (v1.2 Track C1).

## Context

The universal installer historically ran Ollama bootstrap unless `--skip-ollama`, with non-interactive mode auto-installing via winget/brew/script. CI, cloud-only, and quick-stub operators need a **fast minimal path** without multi-gigabyte model downloads, while first-time local dev still expects an out-of-the-box LLM stack.

## Decision

1. **`--install-profile`** — `recommended` (default) or `barebones`; persisted as `NIMBUSWARE_INSTALL_PROFILE` in `.env`.
2. **Recommended** — Ollama bootstrap + pull `llama3.1:8b` and `qwen2.5-coder:14b` (from `configs/model-routing.yaml` via `models_from_repo`); set `NIMBUSWARE_USE_LLM=1` when bootstrap succeeds; warn-and-continue on pull failure.
3. **Barebones** — skip Ollama and model pulls; operator uses `nimbusware-run --quick` or Model Hub later.
4. **`--skip-ollama`** implies barebones LLM posture (backward compatible).
5. **Edition matrix** — enterprise `recommended` auto-enables `--seed-config` after schema; enterprise `barebones` defaults Postgres to Docker in `--non-interactive` when not skipped.
6. **Interactive menu** — profile prompt before Ollama when stdin is a TTY and profile not explicit on CLI.

## Consequences

- Consumer curl lines and `nimbusware-bootstrap` document both profiles.
- `docs/deploy/first-install-timing.md` splits recommended vs barebones budgets.
- Model Hub (C3) is the post-install path for barebones operators adding local or API LLM.

# First install timing (Release v1)

Reference path for the **&lt; 15 min** onboarding metric (fo1300). Times are indicative on a mid-tier dev machine with Docker available.

## Recommended profile (default after v1.2 C1)

Full local LLM stack: Ollama install/start + default model pulls (`llama3.1:8b`, `qwen2.5-coder:14b`).

| Step | Typical duration | Command / surface |
|------|------------------|-------------------|
| Clone + Poetry install | 3–8 min | `python scripts/install_nimbusware.py --non-interactive` |
| Postgres up (Docker) | 1–2 min | Installer menu or `docker compose up -d postgres` |
| Schema apply | &lt; 30 s | Installer or `poetry run nimbusware-store apply-schema` |
| Ollama + model pull | 5–15 min | Installer recommended profile or `ollama pull llama3.1:8b` + `qwen2.5-coder:14b` |
| Start API + Maker | &lt; 30 s | `poetry run nimbusware-run` or `--quick` for stub path |
| First gate pass (LLM) | 2–5 min | Maker Chat → patch intent on fixture with `NIMBUSWARE_USE_LLM=1` |

## Barebones profile (minimal / CI / cloud-only later)

No Ollama download during install. Use `--install-profile barebones` or `--skip-ollama`.

| Step | Typical duration | Command / surface |
|------|------------------|-------------------|
| Clone + Poetry install | 3–8 min | `python scripts/install_nimbusware.py --install-profile barebones --non-interactive` |
| Postgres (optional) | 0–2 min | `--skip-postgres` for fastest CI path |
| Start API + Maker | &lt; 30 s | `poetry run nimbusware-run --quick` |
| First gate pass (stub) | &lt; 3 min | Maker Chat → patch on fixture (stub critics) |

Add local LLM later via **Models** tab (`#/models`) or API connections (v1.2 Model Hub).

**Quick path (no Postgres):** `poetry run nimbusware-run --quick` — readiness green in **&lt; 5 min** after Poetry install; first stub gate pass in **&lt; 3 min**.

**Full path with Postgres (recommended):** target **&lt; 15 min** from clone to first documented gate pass on a reference fixture (excluding large model download variance).

Record intent→patch timings in Admin **Metrics** via `benchmarks/latest_intent_to_patch.json`. The harness uses stub implement on `tests/fixtures/repos/tiny_python_app` (not a live LLM path). Regenerate with:

```bash
poetry run python scripts/benchmarks/measure_intent_to_patch.py --json benchmarks/latest_intent_to_patch.json
```

The **&lt; 3 min** quick-path target applies to stub critics with `poetry run nimbusware-run --quick`, not to LLM-backed runs.

See [README.md](../../README.md) Maker onboarding and [operator-settings.md](../operator-settings.md).

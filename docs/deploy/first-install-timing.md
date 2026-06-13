# First install timing (Release v1)

Reference path for the **&lt; 15 min** onboarding metric (fo1300). Times are indicative on a mid-tier dev machine with Docker available.

| Step | Typical duration | Command / surface |
|------|------------------|-------------------|
| Clone + Poetry install | 3–8 min | `python scripts/install_nimbusware.py --non-interactive` |
| Postgres up (Docker) | 1–2 min | Installer menu or `docker compose up -d postgres` |
| Schema apply | &lt; 30 s | Installer or `poetry run nimbusware-store apply-schema` |
| Ollama + model pull | 2–5 min | Installer Ollama step or `ollama pull llama3.2` |
| Start API + Maker | &lt; 30 s | `poetry run nimbusware-run` or `--quick` for stub path |
| First gate pass (quick) | &lt; 2 min | Maker Chat → patch intent on fixture project |

**Quick path (no Postgres):** `poetry run nimbusware-run --quick` — readiness green in **&lt; 5 min** after Poetry install; first stub gate pass in **&lt; 3 min**.

**Full path with Postgres:** target **&lt; 15 min** from clone to first documented gate pass on a reference fixture.

Record actual timings in Admin **Metrics** via `benchmarks/latest_intent_to_patch.json` (regenerate with `scripts/measure_intent_to_patch.py --json benchmarks/latest_intent_to_patch.json`).

See [README.md](../../README.md) Maker onboarding and [operator-settings.md](../operator-settings.md).

# CLI tools

| Command | Purpose |
|---------|---------|
| `poetry run nimbusware-api` | Start FastAPI/uvicorn |
| `poetry run nimbusware-config` | Import/export/seed Postgres config |
| `poetry run nimbusware-preflight` | Ad-hoc Ollama preflight probe |
| `poetry run nimbusware-memory-index` | Build repo-scoped memory FAISS index |
| `poetry run nimbusware-memory-sync` | Enterprise fleet memory push/pull |
| `poetry run nimbusware-memory-replay` | Replay runs against memory fixtures |
| `poetry run nimbusware-role-telemetry` | Aggregate role telemetry from events |
| `poetry run nimbusware-routing-suggest` | Read-only routing suggestions |
| `poetry run nimbusware-run-worker` | Redis/in-memory run-dispatch worker |
| `poetry run nimbusware-fleet-ollama-sli` | Enterprise sustained Ollama p95 export |
| `poetry run nimbusware-run` | Desktop API + Maker window |
| `poetry run nimbusware-admin` | Desktop API + Admin Console |
| `poetry run nimbusware-maker` | API + Maker web UI (`--quick` for solo dev) |
| `poetry run nimbusware-git-pr` | Open GitHub PR for a run branch |
| `poetry run nimbusware-mcp` | Stdio MCP server for IDE integration |
| `poetry run nimbusware-launcher` | Install/update/run launcher UI (Quick or Full setup) |
| `poetry run nimbusware-compute-worker` | Compute mesh worker |

## Scripts

- FAISS: `scripts/faiss/build_bundle_faiss_index.py`, `build_memory_faiss_index.py`
- Ops: `scripts/ops/run_dispatch_worker.py`, `prune_scraper_artifacts.py`, `e2e_smoke.py`
- Benchmarks: `scripts/benchmarks/swe_bench_harness.py`, `launch_eval.py`, `measure_intent_to_patch.py`

## Runbooks

See [`scripts/runbooks/`](../scripts/runbooks/) — fleet dispatch, Ollama SLI, stack soak, Redis fleet soak.

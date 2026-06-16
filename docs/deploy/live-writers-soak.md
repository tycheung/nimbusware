# Live writers soak (production profile)

Validates that **`nimbusware_production`** enables live writer stages (`stub_only: false`) and records a pipeline smoke reference.

## Quick gate (CI / local)

```bash
poetry run python scripts/run_live_writers_soak.py
```

Writes `benchmarks/latest_live_writers_soak.json` with:

- `integration_adapter_writer_stub_only: false`
- `refactor_stub_only: false`
- Optional in-memory micro_slice smoke (`run_id`, `pass_rate`)

Included in `scripts/run_v11_ship_gates.py`.

## Full Ollama soak (operator, optional)

Not required for v1.1 finish line. When validating live LLM writers:

1. Start Ollama: `ollama serve` and pull a model from `configs/model-routing.yaml`.
2. Set env: `NIMBUSWARE_USE_LLM=1`, `NIMBUSWARE_OLLAMA_BASE_URL=http://127.0.0.1:11434`.
3. Run a **production-profile** micro_slice on an attached workspace (not stub implement).
4. Confirm theater shows non-stub writer stages and file edits in workspace.
5. Attach summary (model id, gate outcome, duration) to release notes — not full prompts.

Production profile keeps **critique panels** on stub scan mode by default (`security_critique.stub: true`); live writers refer to **integration_adapter_writer** and **refactor** blocks in `configs/workflows/nimbusware_production.yaml`.

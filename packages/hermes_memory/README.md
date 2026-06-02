# hermes_memory

Repo-scoped retrieval index for Hermes agent runs (local FAISS + metadata sidecars). Enterprise editions may share fleet-scoped indexes; Individual edition keeps indexes under the Nimbusware repo root.

## Layout

| Module | Role |
|--------|------|
| `store.py` | Index build, query, and persistence helpers |
| `faiss_index.py` | FAISS wrapper and dimension checks |

## Related scripts

- `scripts/build_memory_faiss_index.py` — rebuild memory index from repo artifacts
- Console memory panels — `nimbusware_console.memory_display`

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).

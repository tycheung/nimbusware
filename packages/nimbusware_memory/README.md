# nimbusware_memory

Repo-scoped retrieval index for Nimbusware agent runs (local FAISS + metadata sidecars). Enterprise editions may share fleet-scoped indexes; Individual edition keeps indexes under the Nimbusware repo root.

## Layout

| Module | Role |
|--------|------|
| `store.py` | Index build, query, and persistence helpers |
| `faiss_index.py` | FAISS wrapper and dimension checks |

## Related scripts

- `scripts/faiss/build_memory_faiss_index.py` — rebuild memory index from repo artifacts
- Console memory panels — `nimbusware_console.memory_display`

Normative Nimbusware contract: gitignored `nimbusware-orchestrator-local-plan.md` at repo root.

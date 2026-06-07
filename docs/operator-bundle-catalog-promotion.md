# Bundle catalog promotion (Code Researcher → Integrator)

When research stages index a pattern, Nimbusware writes a **catalog candidate** under the repo workspace for operator review before merging into `configs/bundles/catalog.yaml`.

## Flow

1. **Code Researcher** completes `research.pattern.indexed` and calls `write_catalog_candidate()` (see `packages/nimbusware_research/stages.py`).
2. **Stitcher** on successful `stitch.applied` writes a catalog candidate via `write_stitch_catalog_candidate()` (see `packages/nimbusware_research/stages_stitch.py`).
3. Candidate files land at `.nimbusware/research/catalog_candidates/{run_id}/{pattern_id}.json` with `status: pending_integrator_review`.
4. **Admin Console** — use bundle catalog search and integrator preview/apply to validate compatibility; promote rows into the YAML catalog via `POST /v1/bundles/catalog-candidates/{run_id}/{candidate_id}/promote`, `PUT /v1/bundles/catalog`, or the catalog editor panel.
5. **Integrator / Stitcher** stages consume the promoted catalog metadata on subsequent runs.

## API

| Method | Path | Access |
|--------|------|--------|
| `GET` | `/v1/bundles/catalog-candidates?limit=100` | Admin (`X-Nimbusware-Admin-Token`) |
| `POST` | `/v1/bundles/catalog-candidates/promote-stitch-pending?expected_version=N` | Admin — batch-promote pending stitch candidates |
| `POST` | `/v1/bundles/catalog-candidates/{run_id}/{candidate_id}/promote?expected_version=N` | Admin — merge candidate into `catalog.yaml` |

Response shape: `{ "candidates": [ { "run_id", "candidate_id", "status", "repo_url", ... } ] }`.

## Operator checklist

- Confirm license and `domain_tag` on each candidate JSON before catalog merge.
- Rebuild the bundle FAISS index after catalog changes (`scripts/build_bundle_faiss_index.py` or Admin bundle panel).
- Enterprise tenants: fleet memory sync is independent; catalog authority remains repo-scoped YAML + Postgres materializer.

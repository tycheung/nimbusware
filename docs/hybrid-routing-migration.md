# Hybrid routing migration (fo1471)

Legacy [`configs/model-routing.yaml`](../configs/model-routing.yaml) `stage_providers` and `cloud_runtime` remain supported via a shim in `ModelBindingResolver`. When a role has no user defaults or workflow binding, the resolver maps:

| Agent role | Stage key |
|------------|-----------|
| planner | plan |
| backend_writer, frontend_writer | implement |
| security_critic | critique |

If the stage is set to `cloud` and `cloud_runtime.enabled` is true, the resolver returns a cloud binding with `binding_source: hybrid_routing.stage_providers` (legacy label; implementation is `stage_provider_routing`).

**Migration path:** apply a routing preset (`POST /v1/platform/routing-presets/apply`) or configure per-role bindings in Settings **Agent & Models**. Hybrid shim is a fallback only — not the long-term source of truth.

**Enterprise policy:** the `model_policy` section in [`configs/model-routing.yaml`](../configs/model-routing.yaml) (and `GET/PUT /v1/enterprise/model-policy`) gates allowed cloud providers and blocked model ids for admin audit. Saving via the enterprise API may also write `configs/model_policy.yaml` as a tenant override file.

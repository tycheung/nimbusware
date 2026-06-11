# Headless patch from CI

Run a **patch** workflow from GitHub Actions (or any HTTP client) without opening Maker. Uses the same `POST /v1/runs` + lifecycle APIs as the MCP `nimbusware_patch` tool.

## Prerequisites

- Nimbusware API reachable from the runner (`NIMBUSWARE_API_BASE`)
- Enterprise: `X-Nimbusware-Api-Key` with `maker_user` scope
- Individual localhost: open user routes (no key on loopback)
- Project registered with `workspace_path` pointing at the PR checkout
- Optional: external CI bridge env vars so `slice.gate` posts a GitHub Check ([external-ci-bridge.md](external-ci-bridge.md))

## Minimal flow

1. `POST /v1/runs` with `workflow_profile=patch`, `work_type=patch`, `work_type_source=ci`
2. `POST /v1/runs/{run_id}/lifecycle/start`
3. `POST /v1/runs/{run_id}/lifecycle/slice?mode=auto`
4. Poll `GET /v1/runs/{run_id}/maker-progress` until terminal or blocked

### Example create body

```json
{
  "project_id": "<project-uuid>",
  "workflow_profile": "patch",
  "work_type": "patch",
  "work_type_source": "ci",
  "requirements": {
    "business_prompt": "Fix failing unit test on this PR"
  },
  "patch_context": {
    "failing_test": "tests/test_auth.py::test_login",
    "target_paths": ["src/auth.py", "tests/test_auth.py"]
  }
}
```

## Sample GitHub Action

See [`.github/workflows/nimbusware_patch_sample.yml`](../../.github/workflows/nimbusware_patch_sample.yml) (dry-run friendly; set secrets to enable).

## Related

- [ide-bridge.md](../ide-bridge.md) — MCP equivalent
- [external-ci-bridge.md](external-ci-bridge.md) — gate status on `slice.gate`

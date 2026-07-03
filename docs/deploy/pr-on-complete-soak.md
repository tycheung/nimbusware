# PR-on-complete soak (fo1320)

Verify **git workspace → gate PASS → Review Open PR** without Admin.

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Git workspace | Project `workspace_path` is a git repo (`git init` or clone) |
| `gh` CLI | [GitHub CLI](https://cli.github.com/) on PATH, authenticated (`gh auth login`) |
| Slice auto-commit | `NIMBUSWARE_SLICE_AUTO_COMMIT=1` or workflow enables native git outputs |
| Campaign/factory or flag | `open_pr_on_complete` on `run.created` metadata, or `NIMBUSWARE_GIT_PR_ON_COMPLETE=1` |

Patch/micro-slice runs do **not** set `open_pr_on_complete` by default. For soak, use **campaign** or **factory** on a git workspace, or enable the global env flag.

## Green path (Maker)

1. Attach a git-backed project (Home → create project with clone path).
2. Start a **slice** or **campaign** run from Chat (`#/chat`) on that project.
3. Complete at least one slice through **gate PASS** (stub path OK for CI: `NIMBUSWARE_SLICE_IMPLEMENT=stub`).
4. Open **Review** (`#/review?run_id=…`).
5. **Git & pull request** panel shows branch name (default `nimbusware/run-{run_id}`).
6. Click **Open pull request** → `POST /v1/runs/{id}/maker/open-pr`.
7. Expect `pr_url` in response when `gh` succeeds; panel updates with PR link.

## API smoke

```bash
# After a run exists with workspace metadata:
curl -sS "$API/v1/runs/$RUN_ID/maker/git-status" -H "Authorization: Bearer $TOKEN"
curl -sS -X POST "$API/v1/runs/$RUN_ID/maker/open-pr" -H "Authorization: Bearer $TOKEN"
```

Without `gh`: endpoint returns **422** with `gh_not_found` or skip reason — expected on headless CI.

## Automated coverage

- Unit: `tests/unit/test_git_outputs.py` (`maybe_open_gh_pr`, branch naming)
- API: `tests/api_http/test_maker_open_pr.py` (mocked `gh` success path)
- Settings: [operator-settings.md](../operator-settings.md) (`git.open_pr_on_complete`)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No branch in git-status | Enable `NIMBUSWARE_SLICE_AUTO_COMMIT`; apply a slice that passes gate |
| **Open PR** button missing | Run terminal or enable `NIMBUSWARE_GIT_PR_ON_COMPLETE`; need branch without existing `pr_url` |
| 422 `gh_not_found` | Install/auth `gh`, or use copy-branch + manual PR |
| 422 workspace | Run must have `project.workspace_path` resolving to a directory |

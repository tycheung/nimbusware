# Nimbusware peel scripts

Automation for Phase 9 Nimbusware → SwissArmyNoife peel. Operational docs live in
`../../docs/peel-runbook.md`. Day-0 abbreviated protocol: `../../docs/peel-soak-day0.md`.

| Script | Slice | Purpose |
|--------|-------|---------|
| `peel_checklist.py` | sak415-b/c/e | Flags, bridges, stage_bind, default-on gate doc, forbidden edges |
| `ci_peel_import_graph.py` | sak414-a/b/c | CI import-graph gate (strict by default) |
| `ci_peel_delete_guard.py` | sak414-d | Inventory path guard (warn pre-delete; `--post-delete` fail) |
| `peel_soak_prereq.py` | sak415-i | Soak prerequisite bundle (checklist + import graph + docs) |
| `peel_soak_smoke.py` | sak415-j/k/l | In-process soak smoke (flags=1; domain asserts; optional live ping) |
| `peel_soak_lib.py` | refactor:peel-soak-smoke-domain-sections | Domain helpers (`assert_domain_llm` … `assert_domain_compute`) |
| `peel_delete_dry_run.py` | sak411-b, sak412-a, sak413-a, sak411-d | List delete/thin candidates (`--domain llm\|sandbox\|tools\|memory\|all`); **no deletes** |
| `audit_reverse_imports.py` | sak408 | Reverse-import audit helper |
| `peel_common.py` | refactor | Shared paths + inventory candidates |

## Quick run

```powershell
cd Nimbusware
$env:PYTHONPATH = "packages;tests"

python scripts/peel_checklist.py --strict
python scripts/ci_peel_import_graph.py
python scripts/ci_peel_delete_guard.py
python scripts/peel_soak_prereq.py
python scripts/peel_soak_smoke.py
python scripts/peel_delete_dry_run.py --domain llm
python scripts/peel_delete_dry_run.py --domain sandbox
python scripts/peel_delete_dry_run.py --domain memory          # sak413 — memory package
python scripts/peel_delete_dry_run.py --domain memory --strict # sak413-c CI pre-delete gate
python scripts/peel_delete_dry_run.py --domain all --strict   # sak411-d aggregator
```

CI pre-delete inventory gate (`sak412-b` / `sak413-b`): add `--strict` so the script exits **1**
when any inventory path is missing on disk (see `../../docs/peel-delete-inventory.md` and
`../../docs/ci-matrix.md`).

Delete inventory: `../../docs/peel-delete-inventory.md`. Soak log: `../../docs/peel-soak-log.md`.

### Reverse imports (`sak408-f`)

Product `agent_tools` / `research` → `orchestrator` reverse imports were cleared via facades
(**sak408** / **sak409**). Keep them green:

```powershell
python scripts/audit_reverse_imports.py
python scripts/ci_peel_import_graph.py
```

`ci_peel_import_graph.py` is strict by default and is what hosted peel CI runs. Facades under
`agent_tools/facades/` are intentional seams — see `../../docs/peel-import-audit.md`.

## CI

Peel gates run from `Nimbusware/` (see `../../docs/ci-matrix.md` and
`../../docs/hosted-ci-followup.md`).

| Script | Mode | Exit behavior |
|--------|------|---------------|
| `ci_peel_import_graph.py` | default strict | Fail on forbidden import hits (`sak414-a/b/c`) |
| `ci_peel_delete_guard.py` | default (pre-delete) | **Warn** when inventory paths still exist; exit 0 |
| `ci_peel_delete_guard.py --post-delete` | post-delete | **Fail** if any inventory path still exists (`sak414-d` / `sak414-e`) |
| `peel_delete_dry_run.py --domain * --strict` | pre-delete inventory | Fail when listed paths are **missing** on disk |

### `ci_peel_delete_guard.py`

Inventory path guard for sak411+ delete slices. Scans unique rows from
`peel_common.DOMAIN_CANDIDATES` (llm, sandbox, memory, …).

**Pre-delete (default)** — run on PR/main before deletes land:

```powershell
python scripts/ci_peel_delete_guard.py
# optional: --root D:\path\to\Nimbusware  (tests / alternate checkout)
```

Expected: inventory paths **present** → warns, exits 0. Use alongside
`peel_delete_dry_run.py --domain {llm,sandbox,memory} --strict`.

### Memory domain (`sak413-c`)

`--domain memory` lists `packages/memory/{index,store,fleet,…}` delete/thin candidates from
[peel-delete-inventory.md](../../docs/peel-delete-inventory.md). Use `--strict` on CI/main while
inventory is still expected on disk; switch to `ci_peel_delete_guard.py --post-delete` only after
soak-gated deletes land.

**Post-delete (`--post-delete`)** — run after sak411+ file deletes:

```powershell
python scripts/ci_peel_delete_guard.py --post-delete
```

Expected: inventory paths **gone** → ok. Any path still on disk → exit 1 with stderr list.

Unit tests: `Nimbusware/tests/unit/test_peel_import_audit.py` (`test_ci_peel_delete_guard_*`).

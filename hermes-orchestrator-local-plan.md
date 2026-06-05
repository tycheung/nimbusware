# Nimbusware — Hermes agent integration plan (local-first)

> **Nomenclature:** **Nimbusware** = this repository and product (API, Maker, Admin Console, config, IAM). **Hermes** = the online agentic system (adversarial pipeline, critics, gates, verifiers). See [ARCHITECTURE.md](ARCHITECTURE.md#nomenclature).

## Goal

Build **Nimbusware** as the local-first platform integrating the **Hermes** online agentic
orchestration layer (Option A) for a local-first, adversarial
agentic programming workflow using:

- **Primary LLM**: GLM 4.7 Flash (local runtime)
- **Runtime recommendation**: `Ollama` local server (low-overhead default for initial setup)
- **Backend**: FastAPI (Python)
- **Package management**: Poetry
- **Operator UI**: web-only — Maker at `/v1/maker/app/`, Admin at `/v1/admin/app/` (Enterprise Fleet at `/v1/admin/app/fleet`); Streamlit **retired**

The system should support writer/planner agents, adversarial critique agents across multiple
domains, deterministic verifiers, and unanimous gate policies before progression.

**Product north star (Lane M):** turn a **business prompt** into working software on **fully local
hardware** through **many small, careful iterations** — not whole-repo rewrites. Hermes enforces
the loop; Nimbusware **Maker** provides project-scoped UX, slice approval/revert, plain-language
progress, and honest local-resource guidance.

### Top priority (configuration authority)

**Move operator-mutable configuration from repo YAML files to PostgreSQL as the single source of
truth**, with a thin **materialization** layer that builds the in-memory / on-run structures
Hermes already consumes (persona shelves, role registry, workflow profiles, policy merge defaults,
escalation thresholds, integrator thresholds, critique pairings, self-refinement policy, and
related knobs).

- **Authoritative:** API and Admin web edits persist to Postgres (versioned rows, optimistic
  concurrency, audit via existing append-only events such as `persona.shelf.updated` and new
  `config.*.updated` types where needed).
- **Materialized:** orchestrator, ingress, and policy merge read through a `ConfigCatalog` (or
  domain-specific loaders) backed by a **refreshable cache** populated from Postgres—not by
  rereading `configs/**/*.yaml` on every request.
- **Gitops (optional, not authoritative):** `nimbusware-config export` / `nimbusware-config import` (or
  migration seed on empty DB) so teams can still review diffs in git; **never** dual-write YAML and
  Postgres without a declared winner.
- **Frozen at run start:** merged `policy_snapshot` on `run.created` (§6.3A) must snapshot
  **materialized** config as of that moment, not live files that change mid-run.

Normative detail: **§19.5**. Implementation tracking: [plan_gap.md](plan_gap.md) (**shipped** — close-out ledger only).

### Top priority (v2 product — May 2026)

**Nimbusware** is the operator product; **Hermes** remains the orchestration agent. **fo150–fo155**,
**PZ-1–PZ-10**, **Phase 4 (fo160–fo191)**, and **Lane D (fo200–fo207)** shipped at core (May 2026).
**Status (Jun 2026):** Ranked backlog **#1–21** and close-out **A1–A3** shipped. **Individual v1 contract (§14, Phases 1–3, P, 4, §19.5): ~99%.** **Lane M (fo300–fo308): ~98%.** **Enterprise core (Lane D): ~97%** (ops polish optional). **Overall Individual coding-factory product: ~97%.**
**Status and backlog:** [plan_gap.md](plan_gap.md) (close-out items **A4+** only). This document remains the **normative contract**.

| Epic | Normative outcome |
|------|-------------------|
| **fo150** | **Admin web operator chat** (Cursor-like) to configure runs and steer Hermes |
| **fo151** | **Custom agents** with dedicated **system prompts**; editor in Admin web |
| **fo152** | **Micro-slice** workflow: bounded files/LOC per slice; `slice.plan` artifacts |
| **fo153** | **Per-slice** verify → critique → scoped test → unanimous gate before next slice |
| **fo154** | **SliceContextPacket** handoffs between roles (capped context for modest hardware) |
| **fo155** | **Diff-aware replan** — measure slice diff vs `max_files`/`max_loc`; `slice.replan` to subdivide |
| **fo160–fo164** | **Failure/fix retrieval memory** (repo-scoped index, default-on retrieval, per-run opt-out) — **Phase 4 track 1** |
| **fo170–fo172** | **Bundle usage memory** — historical integrator outcomes bias search/ranking |
| **fo180–fo181** | **Replay / failure-pattern regression** harness |
| **fo190–fo191** | **Model params & budgets** optimization from run telemetry |

**Design contract:** adversarial roles pass **small packets** (diff excerpt, test log, verdicts)—not
whole-repo prompts—so each slice is safer, testable, and runnable on weaker machines.

**Normative workflow profile:** `configs/workflows/micro_slice.yaml` (see **§12 Phase P**).

### Top priority (v3 maker product — shipped Jun 2026)

**Lane M** is **shipped (core, ~98%)**: Alpine Maker web at `/v1/maker/app/` on top of
existing Hermes runs (micro-slice + gates), aimed at **business → software** on local hardware.

| Pillar | Normative outcome |
|--------|-------------------|
| **Project-scoped maker UX** | Bind runs to a **project workspace** (not the Nimbusware install root); intent → plan → slices with traceability |
| **Approval + revert at slice boundaries** | Human approve plan / preview diff / apply or **revert** last slice; workspace snapshots before `apply_slice_file_edits` |
| **Plain-language progress** | Maker UI shows status in sentences (“Slice 2 passed tests”), not operator telemetry (fo133, CSV exports) |
| **Local resource honesty** | Readiness dashboard: Ollama up, model loaded, RAM headroom, slice budgets; hardware tier + governor (**§20.8**; replaces static-only presets) |

**Execution substrate (Lane M — ties to Hermes):**

| Component | Normative outcome |
|-----------|-------------------|
| **Agent tool runtime** | Read file, grep, edit file, run shell/pytest (local allowlist); orchestrator invokes tools instead of Ollama-only slice patches |
| **Workspace snapshots** | Git worktree, stash, or copy-on-write snapshot per run/slice **before** mutating files |
| **Revert API** | `POST /v1/runs/{id}/workspace/revert` (and maker UI button) restore last approved snapshot |
| **Orchestrator wiring** | `slice.implement` calls agent runtime when configured; critics/gates unchanged |

Sprint board, epic queue, and **recommended build path:** [plan_gap.md](plan_gap.md) (Maker / web UI items).

---

## 1) Scope and Non-Goals

In this document, headings like **`## 14)`** or **`### 6.3A`** match cross-references written as
**?14** or **?6.3A**.

### In Scope

- Multi-agent orchestration with role-specific responsibilities
- Adversarial critiques for every critical stage
- Unanimous gate pass requirements (with anti-deadlock escalation)
- Local-first execution and storage
- Internet-scale scraping and retrieval **only** for **roles explicitly allowlisted** in workflow /
  policy (`network_egress.scraper_role_allowlist` as **Role Registry** UUIDs, ?3 and ?19.1), with
  **domain allowlists** (hostnames, punycode, or **IP literals** per ?6.3A), **per-run budgets**, and
  **Windows executor egress gates** (?9, ?9.1);
  deny-by-default for all other roles
- FastAPI APIs for orchestration and run lifecycle
- Web operator consoles (Maker + Admin)
- Failure trace routing to correct writer/owner role (**persisted `owner_role`** is a **Role
  Registry UUID**; ?3, ?5)
- **PostgreSQL-backed configuration store** with materialization (?19.5)?replacing direct
  `configs/**/*.yaml` as runtime source of truth for operator-mutable data
- **v2 (Phase P):** operator chat UI, custom agent registry, micro-slice orchestration with
  per-slice gates and context packets (fo150–fo154)
- **v3 (Lane M):** maker app shell, project workspaces, slice approval/revert, plain-language
  progress, local readiness UX, agent tool runtime + workspace snapshots (fo300–fo308)
- **Phase 4:** repo-scoped retrieval memory (`hermes_memory`), bundle usage memory, replay harness,
  model-budget optimization (fo160–fo191); see §12 Phase 4

### Out of Scope (for v1 Individual install)

- Enterprise multi-tenant IAM (**shipped** under `NIMBUSWARE_EDITION=enterprise` — Lane D fo201)
- Production cloud deployment (compose + runbooks only; K8s charts = ops polish)
- **Fleet-wide memory index** on Individual (**shipped** on Enterprise — Lane D fo202; Phase 4 Individual stays **repo-scoped**)

---

## 2) System Architecture

### 2.1 Control Plane (Nimbusware API + Hermes runtime)

Implemented as the Nimbusware FastAPI service (`nimbusware_api`) hosting Hermes orchestration.

Responsibilities:

- Workflow definition and execution (state machine / DAG)
- Agent role registry and model routing
- Policy and gate enforcement
- Task dispatching to workers
- Run state persistence and audit trail
- Retry, timeout, escalation, and cancellation handling

### 2.2 Data Plane

Responsibilities:

- LLM inference requests (GLM 4.7 Flash)
- Tool execution (tests, linting, scans, perf, network checks)
- Artifact generation and storage
- Observability events and metrics

### 2.3 Suggested Local Infrastructure

- **PostgreSQL**: runs, tasks, outputs, findings, decisions
- **Redis**: queues, pub/sub, ephemeral coordination
- **Local FS** (or MinIO later): artifacts and reports
- **Optional vector store**: Qdrant/FAISS for retrieval memory

### 2.4 Runtime and Compatibility Strategy (Windows-First)

- Primary local runtime: `Ollama`
- Primary target model: `glm-4.7-flash` (when available and validated)
- Deployment priority: Windows-first compatibility, Linux parity later
- OS-specific behavior must be isolated behind adapters; avoid cross-OS conditionals in core logic
- Keep Windows-only runtime/model/process handling in dedicated compatibility modules
- Add Linux compatibility modules as separate implementations when parity work begins

---

## 3) Agent Role Taxonomy

All roles must use strict contracts and structured JSON output.

**Role identifiers (normative):** names in ?3.1���3.3 are **human-facing** labels. Persisted policy,
`network_egress.scraper_role_allowlist`, and similar allowlists use **`role_id` UUIDs** from a
**Role Registry** (one row per orchestratable role; ?3 taxonomy entries map to registry records).
The registry is the single authority for stable ids across snapshots, events, and APIs.
**`owner_role` on findings and related persisted events** uses the same **`role_id` UUID** after
ingress normalization (not taxonomy strings), so routing, allowlists, and audit payloads stay
aligned.

### 3.1 Producer Roles

- Planner/Architect
- Agent Evaluator (assesses persona coverage and creates new personas for new domains when needed)
- Frontend Writer
- Backend Writer (FastAPI-oriented)
- Test Writer
- Refactorer
- Security Writer (hardening and remediation patches)
- Module Integrator (assembles from tested bundle modules with minimal deltas)
- Integration Adapter Writer (creates thin compatibility shims for target codebases)
- **Domain Researcher** (**§20.7**, shipped) — external product/domain discovery; `research.brief.emitted`; Maker/Admin approve/reject
- **Code Researcher** (**§20.7**, shipped) — external codebase/pattern discovery; indexes comparable OSS for Planner and Stitcher
- **Stitcher** (**§20.7**, shipped) — minimally invasive transplant of vetted external or catalog modules; hands off to Refactorer for standards alignment

### 3.2 Critique Roles (Adversarial)

- Product Reference Critic
- Domain Critic (e.g., specific game / domain reality checks)
- Spec Compliance Critic
- Code Quality Critic (including N+1 and complexity risks)
- Security Critic
- Performance Critic
- Network/Resilience Critic
- Test Adequacy Critic
- Refactor Critic
- Bundle Fit Critic (checks whether selected module bundle matches requirements)
- Integration Safety Critic (ensures minimal-risk adaptation boundaries)
- Persona Coverage Critic (validates that selected personas match domain and technical risk)
- Agent Evaluator Critic (reviews evaluator decisions, persona-creation triggers, and coverage scores)
- Self-Refinement Critic (checks agent self-review quality before persona promotion)

### 3.3 Verifier / Runner Roles

- Unit/integration test runner
- Static analysis runner
- Dependency and secret scan runner
- API contract validator
- Performance benchmark runner
- Failure Traceback Router
- Bundle Regression Runner (ensures imported bundles remain stable post-integration)

---

## 3A) Bundle Modules + RAG Retrieval Strategy

You maintain tested, popular module bundles (for example auth RBAC, Stripe, AWS SES, AWS RDS
connection managers). Hermes should prefer these reusable assets before full rewrites.

### 3A.1 Bundle Catalog Targets

- Auth/RBAC bundle: admin-configurable role creation and role permissions for frontend routes/pages
  and backend endpoints
- Billing bundle: standardized Stripe integration
- Messaging bundle: AWS SES provider setup
- Data bundle: AWS RDS connection/session manager patterns for FastAPI
- Additional internal golden-path modules as they are validated

### 3A.2 Retrieval Architecture

- Build embeddings over bundle docs, API contracts, migration notes, tests, and reference adapters
- Index using FAISS for local low-latency retrieval
- Add metadata filters: framework, language version, dependency constraints, security posture,
  and compatibility score
- Return top-k bundle candidates and rank by fit before generation

### 3A.3 Agent Split: Integrate vs Rewrite

- **Bundle-first path**: Module Integrator + Integration Adapter Writer perform configurable/simple
  tweaks to fit tested modules into the target codebase
- **Rewrite path**: Frontend/Backend Writers handle large structural rewrites when fit score is low
  or constraints are incompatible

Routing policy:

- If bundle compatibility score >= threshold, default to bundle-first path
- If score below threshold or hard conflicts detected, escalate to rewrite path
- Critic panel can force rewrite when integration risk is high

### 3A.4 Bundle Integration Gates

- Bundle Fit Critic must PASS
- Integration Safety Critic must PASS
- Regression runner must PASS on imported bundle tests and target project smoke tests
- Security/performance critics must PASS after adaptation

---

## 3B) Persona Shelving Model (Business Areas vs Development Roles)

All agents/personas should be indexed on two independent skill axes to avoid role confusion:

- **Business Area expertise** (what domain/regulatory/product context they understand)
- **Development Role expertise** (what technical implementation function they perform)

### 3B.1 Business Area Persona Shelf

Examples:

- Legal/Compliance Expert (privacy, policy, contractual constraints)
- Finance/Billing Expert (invoicing, payments, tax-related flows)
- Healthcare Expert (regulated workflows and terminology where applicable)
- E-commerce Expert (catalog, checkout, fulfillment)
- Gaming/Product Domain Expert (domain language, user expectations, ecosystem conventions)
- Cybersecurity Domain Expert (threat modeling and risk posture context)

### 3B.2 Development Role Persona Shelf

Examples:

- Planner/Architect
- Frontend Engineer
- Backend Engineer
- Test Engineer
- Security Engineer
- Performance Engineer
- Network/Resilience Engineer
- Data/DB Engineer
- Refactor Engineer
- Module Integrator

### 3B.3 Persona Assignment Rule

At runtime, assign a composite persona:

- one primary Business Area persona
- one primary Development Role persona
- optional secondary personas for edge constraints

This creates combinations like:

- `Legal Compliance Expert` + `Backend Engineer`
- `Gaming Domain Expert` + `Frontend Engineer`
- `Finance Expert` + `Security Engineer`

### 3B.4 Agent Evaluator Responsibilities

The Agent Evaluator runs before planning and at major gate failures to determine whether
current persona coverage is sufficient.

Responsibilities:

- Score current persona fit against project/domain requirements
- Identify missing business-area expertise vs missing development-role expertise
- Propose creation of new personas when coverage is insufficient
- Version and register approved new personas in the persona catalog
- Trigger Persona Coverage Critic review before new personas enter mandatory gates

Creation policy:

- New persona creation requires explicit evidence of repeated mismatch/failure
- New persona must define scope boundaries, allowed tools, output schema, and success metrics
- New persona enters probation mode until it meets reliability thresholds

### 3B.5 Universal Critique Modules (Applies to Every Role)

Every producer/evaluator/integrator role must have a paired critique module.

Required pairings:

- Planner -> Plan Quality Critic
- Agent Evaluator -> Agent Evaluator Critic
- Frontend Writer -> Frontend Quality Critic
- Backend Writer -> Backend Quality Critic
- Test Writer -> Test Adequacy Critic
- Refactorer -> Refactor Critic
- Security Writer -> Security Critic
- Module Integrator -> Bundle Fit Critic + Integration Safety Critic

Policy:

- No role output can advance directly to gate without its paired critique module
- Critique modules are mandatory, not optional advisory checks
- Any missing critique pairing is treated as configuration error and blocks run start
- Default operating model is **single producer/writer + multiple critics**, not multiple competing
  writers for the same task
- Advancement requires unanimous PASS from all mandatory critics for that producer output

### 3B.6 New Persona Self-Review and Self-Refinement Loop

After a new business-area persona is created, it must run a self-refinement loop before
joining mandatory production gates.

Self-refinement steps:

1. Persona produces **`capability_profile`**, **`boundary_statement`**, **`scope_in`**, and
   **`scope_out`** (§3E.3)—narrow enough that it cannot subsume another shelf role
2. Persona adds **`terminology_disambiguation`** for overloaded terms in its domain (§3E.4)
3. Persona lists **`defers_to`** for every adjacent role it must not impersonate
4. Persona performs self-critique **only** against `scope_in` tasks (failure cases inside boundary)
5. Self-Refinement Critic checks for **scope creep** (attempts to own `scope_out` items), vague boundaries,
   and missing deferrals—not just depth of prose
6. Agent Evaluator Critic verifies persona-creation rationale, overlap with existing personas, and risk class
7. Persona is revised and re-tested until probation threshold is met

Promotion rule:

- New persona remains in probation until it passes self-refinement checks, **scope field** validation,
  and paired critic gates
- Personas with overlapping `scope_in` vs an existing **promoted** persona require explicit
  `primary_for` / `secondary_for` tags or redesign
- If repeated failures persist, persona is shelved for manual redesign rather than forced into runtime

---

## 3C) Role-to-Critic Mapping Matrix (Operational)

Use this matrix as the source-of-truth config for mandatory critique coverage and unanimous gating.

| Producer / Evaluator Role | Mandatory Critique Modules | Gate Rule |
| --- | --- | --- |
| Planner/Architect | Product Reference Critic, Domain Critic, Spec Compliance Critic, Plan Quality Critic | Unanimous PASS required |
| Agent Evaluator | Persona Coverage Critic, Agent Evaluator Critic | Unanimous PASS required |
| Frontend Writer | Frontend Quality Critic, Security Critic, Performance Critic | Unanimous PASS required |
| Backend Writer | Backend Quality Critic, Security Critic, Performance Critic, Network/Resilience Critic | Unanimous PASS required |
| Test Writer | Test Adequacy Critic, Spec Compliance Critic | Unanimous PASS required |
| Security Writer | Security Critic, Spec Compliance Critic | Unanimous PASS required |
| Refactorer | Refactor Critic, Code Quality Critic, Test Adequacy Critic | Unanimous PASS required |
| Module Integrator | Bundle Fit Critic, Integration Safety Critic, Security Critic, Performance Critic | Unanimous PASS required |
| Integration Adapter Writer | Integration Safety Critic, Code Quality Critic, Network/Resilience Critic | Unanimous PASS required |
| New Domain Persona (probation) | Self-Refinement Critic, Agent Evaluator Critic, Persona Coverage Critic | Unanimous PASS required before promotion |
| Domain Researcher (§20.7) | Persona Coverage Critic, Domain Critic, Spec Compliance Critic | Unanimous PASS required |
| Code Researcher (§20.7) | Integration Safety Critic, Security Critic, Spec Compliance Critic | Unanimous PASS required |
| Stitcher (§20.7) | Integration Safety Critic, Security Critic, Refactor Critic (post-Refactorer), Bundle Fit Critic when `bundle_id` set | Unanimous PASS required |

Operational notes:

- Add/remove critics only through policy version updates (no ad-hoc runtime edits)
- Optional advisory critics may run, but do not override mandatory unanimous gate policies
- Deterministic verifier failures still block advancement even when critic matrix returns PASS
- Critic domain scope is enforced; out-of-domain findings are marked advisory and cannot block gates

---

## 3D) Critic Domain Isolation and Non-Crossing Rules

Critique agents must evaluate only within their explicitly assigned domain boundaries.

### 3D.1 Domain-Bound Critique Contracts

Each critic contract must define:

- `allowed_domains`: exact domains the critic can evaluate
- `forbidden_domains`: domains the critic must not evaluate
- `blocking_authority`: finding categories that can block progression
- `advisory_only_categories`: categories that may be suggested but cannot block

### 3D.2 Enforcement Rules

- A critic may emit `BLOCKER` findings only for categories in its `blocking_authority`
- Any out-of-domain finding is auto-reclassified as `ADVISORY`
- Repeated out-of-domain blocking attempts lower critic reliability score and can trigger quarantine
- Gate evaluation must ignore out-of-domain blocker claims

### 3D.3 Domain Ownership Examples

- Legal/Compliance Critic: privacy, policy, contractual/legal constraints only
- Security Critic: auth, secrets, vulnerability posture, exploitability
- Performance Critic: latency, throughput, resource utilization, query efficiency
- Network/Resilience Critic: retries, timeouts, backoff, network fault handling
- Domain Critic (business area): market/domain realism and requirement alignment

### 3D.4 Escalation for Cross-Domain Findings

If a critic discovers a likely issue outside its domain:

1. Mark as advisory with evidence
2. Route to the owning domain critic/role
3. Do not block the stage unless the owning domain critic confirms it

### 3D.5 Audit and Reporting

- Track per-critic out-of-domain finding rate
- Track false-block attempts by domain
- Include domain-compliance metrics in critic health dashboards

---

## 3E) Narrow scope, single-job discipline (all agents & personas)

**Principle:** Every agent does **one job expertly** and **refuses to half-do others’ jobs**.
Overlapping vague mandates cause duplicate work, contradictory findings, wasted tokens, and
confusing **Run theater** threads (§20.9). Scope discipline is as important as unanimous gates.

### 3E.1 Producer / writer rules (normative)

| Rule | Requirement |
|------|-------------|
| **Single primary output** | One artifact type per stage (plan, patch, test file, research brief)—no “while I’m here” refactors in writer stages |
| **Explicit deferral** | If work belongs to another role, emit **`defer_to_role`** (registry UUID + one-line reason) in metadata—do not implement |
| **No critic cosplay** | Writers must not emit blocking security/perf verdicts; they may flag “suggest Security Critic review” as **non-blocking** note only |
| **Terminology** | Use role-local definitions for ambiguous terms (see §3E.4); if unsure, name the owning role instead of guessing |

### 3E.2 Critic rules (extends §3D)

- Critics **only** judge inside `allowed_domains`; everything else is **ADVISORY** + `defer_to_role`.
- Critics must **not** propose full implementations outside their domain—only `RequiredFixArtifact` patches
  for categories in `blocking_authority`, or a deferral to the owning writer.
- **No pile-on:** if another critic already BLOCKED the same category, later critics add **evidence only**
  unless they own a distinct blocking category.

### 3E.3 Persona shelf fields (normative catalog shape)

Each persona entry (business area **and** development role) should carry **machine-readable scope**,
not only prose in `instructions`:

| Field | Purpose |
|-------|---------|
| `capability_profile` | What this persona **is** expert at (required for promotion, §3B.6) |
| `boundary_statement` | What this persona **will not** do (required for promotion) |
| `scope_in` | Non-empty list: topics, layers, artifacts this persona owns |
| `scope_out` | Non-empty list: explicit non-goals (other roles’ jobs) |
| `defers_to` | List of role/persona ids to hand off to (e.g. `security_engineer`, `refactorer`) |
| `terminology_disambiguation` | List of `{term, meaning_in_role}` for overloaded words |

**Self-refinement promotion (§3B.6):** probation → promoted only when `scope_in`, `scope_out`,
`capability_profile`, and `boundary_statement` are all present and pass Self-Refinement Critic review.
Optional: at least one `terminology_disambiguation` entry when the domain uses overloaded terms.

**Implementation:** validated in `hermes_extensions.personas`; promotion gaps in
`SelfRefinementEvaluator`.

### 3E.4 Terminology disambiguation (examples)

Same English word, different expert meanings—agents must use **their** definition or defer:

| Term | Data engineer | ML practitioner | Refactor engineer |
|------|---------------|-----------------|-------------------|
| **normalization** | Schema/DB normal forms, deduped keys | Feature scaling, train/val distributions | Code style / API shape consistency |
| **validation** | Constraints, migrations, data quality checks | Holdout metrics, cross-validation | Input/schema validation in app code |
| **pipeline** | ETL / batch jobs | Training/inference graph | CI stage graph / Hermes run stages |
| **model** | DDL / ER diagram | ML weights | Pydantic schema / domain object |

Domain researchers (§20.7) document domain glossary; **development-role personas** document
engineering glossaries. Planner merges glossaries into plan context—writers must not redefine terms.

### 3E.5 Efficient inter-agent “conversation”

Handoffs are **structured**, not free-form debate:

1. **Deferral message** — `defer_to_role`, `reason_code`, `evidence_refs` (Run theater displays this clearly).
2. **No duplicate producers** — one writer per concern; parallel writers only when concerns are orthogonal (frontend vs backend).
3. **Packet discipline (fo154)** — `SliceContextPacket` / research briefs carry **scoped excerpts**, not whole-repo dumps.
4. **Agent Evaluator** — rejects persona sets where `scope_in` overlaps heavily between assigned roles without explicit primary/secondary ranking.

### 3E.6 Prompt template requirement (see §8.1)

Every role system prompt must include a **Scope** section citing `scope_in`, `scope_out`, and
`defers_to` from the assigned persona(s), plus: *“If the task is outside scope_in, defer; do not partially implement.”*

---

## 4) Workflow and Gates

### 4.1 Canonical Pipeline

1. Agent Evaluator checks persona coverage and composes required persona set
2. If new persona is created, run self-refinement loop + evaluator critiques
3. Planner drafts implementation plan + acceptance criteria
4. Plan critics review (reference/domain/spec/persona coverage)
5. Gate: unanimous PASS required for plan advancement
6. Bundle retrieval ranks reusable modules (RAG/FAISS)
7. Gate decides bundle-first integration path or rewrite path
8. Writers implement in parallel (module integrator/frontend/backend/test as applicable)
9. Role-specific critique modules review each output
10. Verifiers run tests/scans/benchmarks
11. Traceback router assigns failures to owning writer
12. Writers patch only assigned findings
13. Refactorer proposes maintainability improvements
14. Refactor critics validate no regressions
15. Agent Evaluator re-checks if repeated failures indicate missing persona coverage
16. Final mandatory gates pass -> run completed

### 4.2 Gate Policy Contract

**Two layers:** (A) **Critic agent output** ��� the full structured contract below, used for gate
logic and persistence of authoritative critic JSON (artifact or embedded blob). (B) **Audit /
event projection** ��� e.g. `critic.verdict.emitted` append-only events may carry a **subset** of
fields optimized for replay, dashboards, and correlation; they are not a second source of truth
for the full contract unless explicitly versioned to include it.

**Critic agent output** (every critic must return):

Raw agent JSON may still use **taxonomy labels** where convenient, but **persistence and events**
carry **Role Registry UUIDs** after **?5** ingress normalization (especially **`owner_role`**).

- `verdict`: `PASS | FAIL | NEEDS_INFO`
- `severity`: `LOW | MEDIUM | HIGH | BLOCKER`
- `evidence`: concrete references
- `required_fixes`: structured, minimal, actionable
- `owner_role`: role responsible for remediation (**Role Registry `role_id` UUID** on every
  persisted path; raw agent JSON may use a taxonomy label only if ingress resolves it ��� see ?5)
- `domain_scope`: declared critic domain for this verdict (see ?3D domain boundaries)
- `is_in_domain`: boolean enforcement flag used by gate logic

`required_fixes` is mandatory and must be deterministic:

- `format`: `json_patch` or `unified_diff`
- `target_files`: explicit file paths
- `patch_artifact`: machine-applyable patch payload
- `validation_steps`: exact checks to rerun (tests/lints/scans)
- `acceptance_criteria`: objective pass signal for closure
- Free-form prose-only fix instructions are invalid for blocking findings

**Typed contract (track in code):** define a single Pydantic model (e.g. `RequiredFixArtifact`) that
contains exactly the fields above (`format`, `target_files`, `patch_artifact`,
`validation_steps`, `acceptance_criteria`). Critic verdicts, findings, and gate-related events that
reference fixes must embed this model (or a list of them for multi-file fixes), not a loose dict.

### 4.2A Finding fix strictness (two sliders)

`finding.created` payloads use **config-driven** rules for when `required_fixes` is mandatory, so
operators can tune strictness without code changes.

**Primary slider ��� `minimum_severity_requiring_fixes`**

- Ordered ladder: `LOW` < `MEDIUM` < `HIGH` < `BLOCKER`.
- All severities **at or above** this floor **must** include at least one deterministic
  `RequiredFixArtifact` on `finding.created`.
- Examples:
  - `BLOCKER` ��� only blocker findings require fixes.
  - `HIGH` ��� `HIGH` and `BLOCKER` require fixes; `LOW`/`MEDIUM` do not (unless secondary slider).
  - `MEDIUM` ��� `MEDIUM`, `HIGH`, and `BLOCKER` require fixes (default in code).
  - `LOW` ��� every severity requires fixes (maximum primary strictness).

**Secondary slider ��� `also_require_fixes_for_low_severity`**

- Boolean. When **true**, **LOW** findings **also** require `required_fixes`, even if the primary
  floor is above `LOW` (e.g. primary floor `MEDIUM` still mandates fixes for **LOW** in addition to
  `MEDIUM`+).
- When the primary floor is already `LOW`, this flag is redundant (all severities already covered).

**Implementation contract**

- Persist the effective `FindingFixStrictnessSettings` in the **run policy snapshot** (or workflow
  profile) at run start; orchestration passes the same object as Pydantic validation **context** under
  key `finding_fix_strictness` when validating `finding.created` events and any API that accepts
  finding payloads.
- Default if omitted: `minimum_severity_requiring_fixes = MEDIUM`,
  `also_require_fixes_for_low_severity = false`.

**Edge case (documented):** if the primary floor is `HIGH`, `MEDIUM` findings do **not** require
fixes; turning on the LOW-only secondary does **not** add `MEDIUM`. Tighten the primary floor if
`MEDIUM` must always carry fixes in that configuration.

### 4.2B Plan ��� code mapping (v1 event projection)

| ?4.2 critic agent field | v1 `critic.verdict.emitted` payload / note |
| --- | --- |
| `evidence` | `evidence_refs` (list of stable refs: paths, test ids, artifact ids) |
| `domain_scope` | Not on v1 event payload; must appear on full critic agent output (artifact or future payload revision) |
| `required_fixes` | `required_fixes` as `RequiredFixArtifact[]` (JSON wire key per artifact remains `format`) |
| `verdict`, `severity`, `owner_role`, `is_in_domain` | Same semantics on the event payload; **`owner_role` must be a Role Registry UUID** on persisted `critic.verdict.emitted` / `finding.created` / `finding.routed` / `finding.closed` payloads (see ?3, ?5) |

**Additional event types:** any future append-only payloads that include **`owner_role`** must use the
same **Role Registry UUID** rule; extend **?19.2** `CHECK` / ENUM and application unions **in
lockstep** when adding types (**?14**, ?6.6).

**Forward compatibility:** a later revision may embed the full ?4.2 shape on the event, or require
an `artifact_id` pointer to immutable stored critic JSON and keep the event minimal.

### 4.3 Unanimous Pass Rules

**Severity semantics:** on `critic.verdict.emitted`, `severity` encodes the **risk / urgency of the
verdict** for routing and dashboards. **Finding fix strictness** (?4.2A) governs **when**
`finding.created` payloads must include `RequiredFixArtifact` lists; **agent vs event field
mapping** is ?4.2B. Gates combine verdicts,
severities, findings, and policy tables; the two dimensions are intentional and must not be
conflated in orchestration code.

- Stage advances only when all mandatory critics return `PASS`
- Any `BLOCKER` immediately routes remediation to the **owner** identified by persisted
  **`owner_role`** (**Role Registry UUID** after ?5 ingress; not a free-text label)
- `NEEDS_INFO` routes to Planner for clarification (not direct rewrite)
- If repeated loop count exceeds threshold, escalate to Arbiter/Human checkpoint
- Default pattern is one producer output reviewed by multiple adversarial critics; avoid parallel
  competing writers unless explicitly configured for experimentation

### 4.4 Model Preflight and Fallback Gate (Mandatory)

Before run creation, execute a model preflight stage:

- Verify `Ollama` reachability and runtime health
- Verify configured primary model is locally available
- Verify minimum capabilities used by this system (structured JSON reliability, context budget,
  response latency envelope)

Fallback policy:

- If primary `glm-4.7-flash` is unavailable or fails capability checks, route to approved fallback model
- Fallback selection must use ordered allowlist from config (no ad-hoc runtime choice)
- Persist selected model, reason code, and preflight evidence into run metadata
- If no approved model passes preflight, run fails fast at initialization

---

## 5) Failure Attribution and Routing

Create a deterministic mapping from finding category to owner role.

Examples:

- UI logic/regression -> Frontend Writer
- API schema mismatch -> Backend Writer
- Flaky/misaligned tests -> Test Writer
- SQL/query count/N+1 issues -> Backend Writer + Perf Critic
- Auth/secret/input sanitization issues -> Security Writer

The examples above use **taxonomy** for human readability; **persisted `owner_role`** is always a
**registry UUID** after normalization (?3, **Ingress normalization** below).

Each finding should include:

- `finding_id`
- `category`
- `owner_role` ��� **Role Registry `role_id` UUID** (see ?3); not a free-text persona name on append
- `source_artifact`
- `repro_steps`
- `severity`
- `required_fixes`: list of deterministic remediation artifacts when policy requires them (see
  ?4.2 for contract / `RequiredFixArtifact` shape; ?4.2A for when fixes are mandatory)

**Ingress normalization:** before append, map critic or router output that names a role by **taxonomy
label** to a **registry UUID** via the Role Registry; **reject** unknown labels at validation time.

**Fix shape (`expected_fix_type` vs artifacts):** the **canonical** fix discriminator is
`required_fixes[].format` (`json_patch` | `unified_diff`), matching `RequiredFixArtifact` in code
(Python field `patch_format`, JSON alias `format`). An optional **`expected_fix_type`** in APIs or
legacy docs, if present, **must equal** the primary artifact���s `format` (denormalized convenience
only); v1 may **omit** `expected_fix_type` entirely wherever `required_fixes` is authoritative.

---

## 6) FastAPI Service Design

### 6.1 Core Modules

- `orchestrator`: workflow execution and stage transitions
- `agents`: role definitions, prompts, model config
- `policies`: gate and escalation logic
- `tasks`: queue dispatch and worker contracts
- `artifacts`: report and patch persistence
- `telemetry`: logs, traces, metrics

### 6.2 API Endpoints (v1)

Paths below are **logical resource names**. Mount the HTTP API under **`/v1/...`** (e.g.
`POST /v1/runs`, `GET /v1/runs/{run_id}`) or use an equivalent **version header** strategy per
?6.6; do not ship unversioned public routes in production.

Unless stated otherwise, each line is **`METHOD` + a path segment** (e.g. `POST /runs` uses segment
`/runs`; `GET /runs/{run_id}` uses `/runs/{run_id}`). The **mounted** URL path is **`/v1`** plus
that segment (e.g. `POST ���/v1/runs`, `GET ���/v1/runs/{run_id}`). Do not concatenate the method name
onto `/v1`; only the path segment is prefixed. With a **version-header** strategy instead of a URL
prefix, treat the same segments as the versioned resource paths under the contract.

- `POST /runs` create run with workflow profile
- `GET /runs/{run_id}` get run status and summary
- `GET /runs/{run_id}/timeline` stage and event timeline
- `GET /runs/{run_id}/findings` aggregated findings and ownership
- `POST /runs/{run_id}/actions/retry` retry failed stage
- `POST /runs/{run_id}/actions/escalate` trigger arbiter checkpoint
- `POST /roles/{role_id}/execute` manual role execution (debug/admin use)

### 6.3 Data Models (Pydantic)

**Aggregate domain types** (`Run`, `Stage`, `Task`, `AgentOutput`, `CriticVerdict`, `Finding`,
`GateDecision`) are **projection / read models**: derived from the append-only event stream (and
optional artifact pointers), **not** a second source of truth beside the database event store.
Strict schema validation applies to all agent outputs at ingress and to events at append time.

**Implemented today (v0):** event envelope and per-`event_type` payload models live under
`packages/agent_core` (e.g. discriminated unions for `critic.verdict.emitted`,
`finding.created`). Aggregate `Run` / `Stage` / `Task` types are **targets** for Phase 1+ once
replay and APIs land. Replay ordering for projections: **?19.3** (`ORDER BY store_seq`).

### 6.3A Run policy snapshot layout

At run start, persist an immutable **policy snapshot** (referenced by `run.created` fields such as
`policy_version` and `config_snapshot_id`). Stable keys for operator-tunable rules:

- `policy_snapshot.finding_fix_strictness.minimum_severity_requiring_fixes` ��� `LOW` | `MEDIUM` |
  `HIGH` | `BLOCKER` (see ?4.2A).
- `policy_snapshot.finding_fix_strictness.also_require_fixes_for_low_severity` ��� boolean.

- `policy_snapshot.network_egress.scraper_role_allowlist` ��� **merged** list of **Role Registry**
  `role_id` UUIDs allowed to scrape (see ?3, ?9.1). A **merged empty** list means **no** roles may
  scrape.
- `policy_snapshot.network_egress.domain_allowlist` ��� v1 entries are **hostnames**, **punycode**
  hostnames, **IPv4 dotted-quad**, or **IPv6** literals (no scheme, no port in the string). **ASCII
  hostname** or **punycode** (`xn--���`) may use **suffix** form with a **leading dot** (e.g.
  `.pypi.org` matches `files.pypi.org`); **suffix / leading-dot rules do not apply to IP literals**
  (**exact match only** for IPs). **IDN** in hostnames must be normalized to **punycode** at
  merge/freeze (reject invalid labels). **Normalize IPv6** literals to a **single canonical
  compressed** text form at merge/freeze, and **reject** any literal that contains **`%`** (zone /
  scope-id suffixes are unsupported in v1). **IPv4** literals: **parse and re-serialize** to **canonical
  dotted-quad** at merge/freeze (**reject** invalid IPv4). **Lowercase** hostname/punycode entries at
  merge/freeze (IP literals unchanged except the IPv4/IPv6 normalizations above).
- `policy_snapshot.network_egress.budget_bytes_per_run` ��� **merged** effective byte cap: see merge
  rules below (**non-negative integer** after merge, **`0`** = zero-byte cap; **`null`** = no cap /
  unlimited).

**`network_egress` merge stack (normative):** layers from **base ��� highest**: (1) `configs/` defaults
(?19.1), (2) **workflow profile** for the run, (3) **run-scoped overrides** (API / operator). **Freeze**
the merged result into `policy_snapshot` at run start.

**List fields (`scraper_role_allowlist`, `domain_allowlist`) ��� merge:** Walk layers **low ��� high**
(configs ��� workflow ��� run). Initialize **accumulator** to **`[]`**. At each layer: if the field is
**omitted** or **`null`**, skip the layer (**accumulator** unchanged); if **`[]`**, set
**accumulator** to **`[]`**; if a **non-empty list**, **accumulator := dedupe(accumulator ��� list)**.
Higher layers **widen** the
allowlist; **`[]`** **clears** contributions from lower layers so far, then higher layers may widen
again. **Security:** to **hard-deny** for that field, set **`[]` on the highest layer** that should
take effect. If every layer **omits** the field or sets **`null`**, **accumulator** stays **`[]`**
(deny-by-default).

**`budget_bytes_per_run`:** collect **finite non-negative integers** from every layer that **sets**
the field (after treating omit/`null` as ���not set��� for that layer); **reject** negative values at
merge/freeze. **`0`** is valid: it caps egress at **zero bytes** and is included in the **min()** like
any other supplied integer. If **none** set, effective value is **`null`** (no cap). If **one or more**
set, effective value is the **minimum** (smallest integer wins)���**intentionally different** from list
union (narrowing vs widening). Per-layer **`null`** /
omit means ���do not set a cap at this layer.��� **Higher-layer omit/`null` does not remove a finite cap**
already set by a **lower** layer: there is **no** v1 ���relax to unlimited��� override except when **no**
layer ever supplied an integer (merged snapshot **`null`**).

Orchestration **must** load these values and pass them as Pydantic validation **context** under key
`finding_fix_strictness` when validating `finding.created` events and any HTTP body that accepts
finding payloads (same key as ?4.2A).

### 6.4 Event Store and Immutable Audit Logging

- Use PostgreSQL as the immutable event store of record for run/stage/task/critic events
- Event writes are append-only; corrections are represented by new compensating events
- Every gate decision, model selection (including fallback), and finding lifecycle update must emit events
- API read models may denormalize from events, but source-of-truth remains append-only DB event stream
- Columns and payload fields that identify an orchestrated role (**`actor_role`** on `event_store`,
  **`owner_role`** inside JSON payloads, etc.) use **Role Registry `role_id` UUID** strings when set
  (see ?3, ?19.2).

### 6.5 Event Store and Event Envelope Hardening (Required)

Track these during implementation; they prevent silent corruption and nondeterministic replay.

1. **`event_type` ��� `payload` coupling (application layer)**  
   The persisted `event_type` must always match the payload shape. Enforce with discriminated unions
   in Pydantic (or equivalent), a single factory that validates the pair before INSERT, and tests
   that reject mismatches. Do not allow a generic envelope where any payload can accompany any type.

2. **Deterministic replay ordering (database + application)**  
   Add a monotonic ordering key assigned at insert time (e.g. global `store_seq BIGSERIAL`, or a
   per-run strictly increasing sequence). **Replay projections with `ORDER BY store_seq`**
   (never rely on `occurred_at` alone for tie-breaking; `event_id` UUID order is not chronological).

3. **`event_type` constraint at the database boundary**  
   Restrict `event_type` to the approved set (PostgreSQL `ENUM` synced with the app, or a `CHECK`
   constraint listing allowed values). Reject unknown types at the DB so drift is caught early.

4. **Typed `RequiredFixArtifact` everywhere fixes are mandatory**  
   Blockers and routable findings must carry the full artifact (contract / `RequiredFixArtifact`
   shape ��� ?4.2; **when** fixes are mandatory ��� ?4.2A), not only `format` or prose.

**Implementation note (typing vs runtime):** static `JsonValue`-style aliases may permit values
that runtime envelope validation rejects (e.g. non-finite floats in `metadata`). Treat the
**implementation module** as authoritative for strict JSON rules on persisted `metadata`.

### 6.6 Operational API and lifecycle (normative bullets)

These items govern production hygiene; implement incrementally but do not leave ambiguous:

- **Idempotency:** require client-supplied `Idempotency-Key` and/or envelope `correlation_id` for
  **`POST /v1/runs`** (the **mounted** URL for the ?6.2 **`POST /runs`** create-run route) and other
  mutating routes (path segments listed in ?6.2); define deduplication window and collision behavior.
- **API versioning:** use URL prefix (e.g. `/v1/`) or version header; document deprecation policy
  for breaking contract changes.
- **Human override / escalation events:** target v1 append-only type names such as
  `run.escalated`, `gate.overridden` (carrying actor id, reason code, link to policy snapshot, and
  optional compensating payload). They are **not** in the ?19.2 draft `CHECK` list until shipped;
  add them to PostgreSQL **`CHECK` / ENUM** and the app discriminated union **in the same release**
  (?14 checklist item 8, ?19.2, ?19.4).
- **Retention / PII:** TTL vs legal hold for `event_store` rows and blob artifacts; redaction
  rules for `metadata` and `payload`; constraints on export and log shipping.
- **Replay / projections:** name an owning component (orchestrator worker or batch job), rebuild
  triggers after schema changes, and failure modes; align with ?19.3.
- **Streamlit / debug auth:** local-only shared secret or OS user binding; disable remote exposure
  by default; tighten scope for **`POST /v1/roles/{role_id}/execute`** (suffix `POST /roles/{role_id}/execute`
  in ?6.2) where `{role_id}` is a **Role Registry** UUID (?6.2, ?3).
- **Cross-event invariants (optional v1):** e.g. forbid `finding.created` before `run.started`;
  choose soft log warnings vs hard reject at append time.

---

## 7) Web operator console

Primary operator surfaces are **FastAPI-served web apps** (not Streamlit):

| Surface | URL | Notes |
|---------|-----|-------|
| **Maker** | `/v1/maker/app/` | Alpine.js product shell (intent → review → progress) |
| **Admin** | `/v1/admin/app/` | Preact power-user console (runs, config, metrics) |
| **Fleet** (enterprise) | `/v1/admin/app/fleet` | Hardware / SSH probe BFF |

Streamlit operator UI is **retired**; all new work lands in web UIs (`nimbusware_maker_web`, `nimbusware_admin_ui`).

### 7.1 v2 operator workspace (fo150–fo151)

- **Operator chat** (fo150): threaded messages, compose box, actions to start runs and inspect
  timeline/gate failures (`packages/nimbusware_console/operator_chat.py`).
- **Custom agents** (fo151): list/select agents; **pencil** icon opens system-prompt editor;
  persisted under `configs/custom_agents/registry.yaml` or Postgres `agents/registry` when DB mode
  is on (`packages/nimbusware_console/custom_agents_ui.py`, `GET/POST/PATCH /v1/custom-agents`).

### 7.2 Operations views (shipped v1)

- Run list with status filters
- Per-run timeline and stage transitions
- Critic matrix (role x verdict x severity)
- Findings board with ownership routing
- Artifact viewer (plans, patches, logs, reports)
- Retry/escalation controls
- Token/time/cost proxy metrics per role

### 7.3 Maker app shell (Lane M — fo300+)

**Goal:** A **slimmer product surface** for “describe what you want → review small changes → keep
or revert” — without exposing the full operator console (config explainers, fo133, fleet panels).

**Normative UX (Simple mode default):**

| Screen | Behavior |
|--------|----------|
| **Home / project** | Pick or create project folder; greenfield template vs attach repo; readiness strip (Ollama, model, disk) |
| **Intent** | Business prompt + clarifying questions → frozen **requirements artifact** linked to `run.created` |
| **Plan review** | Plain-language plan + slice list; **Approve plan** before first slice |
| **Slice loop** | Diff preview → **Apply** or **Skip**; test summary in plain English; **Revert slice** |
| **Progress** | “Slice 2 of 5 — tests passed — ready for next slice”; hide gate matrix CSV unless Advanced |

**Advanced toggle:** links to Admin web console (timeline, critic matrix, config tooling).

**Deliverables (epics fo300–fo308):** see [plan_gap.md](plan_gap.md) Maker / web migration rows.

**Out of scope for Lane M v1:** multi-user SaaS; cloud model routing; full IDE replacement.

---

## 8) Prompting and Contracts

### 8.1 Role Prompt Template

Each role prompt must specify:

- Mission and constraints
- **Scope (mandatory — §3E):** bullet `scope_in` / `scope_out` from assigned persona(s); “defer, don’t dabble”
- **Terminology (when assigned):** embed `terminology_disambiguation` for that role; link domain glossary from research brief if present
- Allowed tools and forbidden actions
- Input schema
- Output schema
- Stop conditions
- Quality rubric
- **Deferral contract:** how to emit `defer_to_role` instead of out-of-scope work

### 8.2 Critic Reliability Requirements

- Evidence-backed claims only
- Must cite artifacts/tests/files involved
- No style-only blockers unless explicitly policy-defined
- Unsupported claims auto-marked invalid and retried once
- **Stay in lane (§3E.2):** out-of-domain issues → ADVISORY + defer; never ship a full alternate design for another role’s layer
- **One blocking owner per category:** do not duplicate another critic’s BLOCKER finding

---

## 9) Security and Execution Safety

Local-first still needs strict guardrails:

- Sandboxed command/tool execution
- Allowed command lists and path boundaries
- Secret scanning before persistence
- Dependency vulnerability checks
- Controlled network egress policies per role
- Immutable run logs for audits ��� **authoritative audit trail** is the **PostgreSQL append-only
  event store** (?6.4���6.5). Artifact files (plans, patches, stdout captures) are **supporting**
  evidence and must not replace missing or invalid events.

### 9.1 Network retrieval and scraping (role-gated)

- **Default:** deny-by-default outbound HTTP(S) and scraping from orchestrated tools unless the
  active role���s **`role_id` UUID** appears on `network_egress.scraper_role_allowlist` in merged
  policy (?19.1, ?6.3A); an **empty** list means **no** roles may scrape.
- **Non-binding examples** of roles that *might* be allowlisted in later phases when product needs
  it: research-oriented producers or integrators that fetch public docs or package metadata ��� **do
  not** grant blanket scraping to all critics or verifiers by default.
- **Enforcement:** combine `domain_allowlist` (hostnames, punycode, **IP literals** ��� matching rules
  ?6.3A), `budget_bytes_per_run` (or equivalent), per-role egress checks in the Windows executor
  adapter, and operator-visible run config in the Streamlit console (?7).

Windows-first execution hardening requirements:

- Implement command execution via explicit adapter boundary: `windows_executor` now, `linux_executor`
  later
- Restrict execution to allowlisted commands and workspace-bounded paths
- Enforce per-role execution identity/scope and timeout budgets
- Store OS-specific command templates and process controls in separate compatibility files
- Gate all outbound network calls through policy checks with per-role allowlists

---

## 10) Project Structure (Poetry + Monorepo)

Suggested layout:

- `apps/orchestrator` (FastAPI app)
- `apps/dashboard` (Streamlit app)
- `packages/agent_core` (shared contracts/schemas/base role logic)
- `packages/roles` (planner/writers/critics)
- `packages/tools` (runner adapters)
- `packages/policies` (gate/escalation logic)
- `configs` (workflows/prompts/model routing)
- `runs` (local artifacts)
- `tests` (unit/integration/system)

Use Poetry for dependency groups:

- `main`: runtime deps
- `dev`: lint/test/type-check tools
- `security`: scanners

**Distribution vs import package:** the Poetry project / wheel name may be `hermes` (or similar)
while the installable Python package is `agent_core` under `packages/agent_core`. After
`pip install -e .` or `poetry install`, use `import agent_core` from application code.

**Repository maturity (non-normative):** the working tree may temporarily omit directories from the
suggested layout (?10) or dev/security tool dependencies from ?11 until Phase 1 scaffolding lands.
The **normative** target remains the listed monorepo structure and tool stack; drift is expected
only during early bootstrap.

---

## 11) Quality and Verification Stack

Initial recommended tools:

- Python quality: Ruff + mypy + pytest
- Security: bandit + pip-audit + semgrep
- API checks: schema/contract validation tests
- Performance: pytest-benchmark (and optional load harness later)
- N+1 detection: query count assertions + SQL logging checks

Rule: deterministic verifier failures override LLM critic PASS results.

---

## 12) Phased Delivery Plan

**Ordering note (Jun 2026):** Phase **1.5 (§19.5) configuration authority** is **shipped**. **Implementation status** lives in [plan_gap.md](plan_gap.md) (close-out ledger). This document is the **normative product contract**. **v1 sign-off:** §14 checklist **21/21 Done**; Phases **1 / 1.5 / C / 2 / P / 3 / 4** met for **Individual** (~**99%**); **Lane D (fo200–fo207)** met for **Enterprise** core (~**97%**).

### Phase 1.5 ? Configuration store (PostgreSQL authority + materialization)

**Goal:** operator-mutable config lives in Postgres; runtime reads materialized views only.

**Scope (migrate to Postgres, in order):**

1. **Personas** ? `configs/personas/shelves.yaml` ? `hermes_config_personas` (or JSONB document per
   shelf); keep Pydantic validation in `hermes_extensions.personas`; API/Streamlit write Postgres;
   emit `persona.shelf.updated` (unchanged audit story).
2. **Role registry** ? extend today?s optional `hermes_roles_registry` to full registry metadata;
   retire `configs/roles.yaml` for runtime when `NIMBUSWARE_CONFIG_FROM_DB=1` (or make DB default).
3. **Workflow profiles** ? `configs/workflows/{profile}.yaml` ? versioned rows keyed by profile stem;
   merge preview / apply paths read/write Postgres; retain export for git review.
4. **Policy merge defaults** ? `configs/model-routing.yaml` slices that feed `policy_snapshot`
   (`finding_fix_strictness`, `network_egress` defaults, preflight knobs) ? Postgres; materialize
   into merge layer (?6.3A).
5. **Satellite policies** ? `configs/escalation/policy.yaml`, `configs/integrator/thresholds.yaml`,
   `configs/self_refinement/policy.yaml`, `configs/personas/critique_pairings.yaml` ? Postgres
   documents with the same validation as today?s loaders.

**Stay on disk (derived or binary, not authoritative):**

- FAISS index files under `configs/bundles/index/` (build artifacts).
- Scraper response artifacts under `.cache/hermes_scraper` (?10).
- Optional **export** copies of Postgres config under `configs/` for gitops—**read-only** from
  Nimbusware's perspective unless explicit `import` is run.

**Bundle catalog (`configs/bundles/catalog.yaml`):** migrate **metadata** to Postgres in a
follow-on slice if operator edit volume warrants it; until then, treat catalog as **seed/import**
only while personas/workflows move first.

**Exit criteria:**

- Empty DB can bootstrap from `nimbusware-config seed-from-repo` (or one-shot migration).
- All `/v1/personas` and workflow write paths persist Postgres only (no atomic YAML write).
- Orchestrator `create_run` / policy merge / persona resolution use **materialized** config;
  `run.created` carries immutable `policy_snapshot` from materialized state.
- Tests: integration tests against Postgres config tables; unit tests for materializer invalidation.

### Phase 1 - Minimal Viable Orchestrator

- FastAPI run lifecycle endpoints
- Planner + 2 plan critics (reference/domain)
- Unanimous plan gate
- Backend writer + test writer loop
- Basic pytest/ruff/mypy runners

Exit criteria:

- End-to-end run can pass/fail with clear gate outputs
- Findings are routed to correct owner role

### Phase 2 - Parallel Writers and Dashboard

**Prerequisite:** Phase **1.5** configuration store materially complete for personas, roles, and
workflows (satellite policies may lag one slice behind).

- Add frontend writer and critic
- Add module catalog + FAISS retrieval + compatibility scoring
- Add Module Integrator and Integration Adapter Writer roles
- Add persona catalog with business-area and development-role shelves (**backed by Postgres**;
  assignment rules use materialized shelves)
- Add Agent Evaluator and Persona Coverage Critic
- Add Streamlit run timeline and critic matrix
- Add retry/escalation operations
- Strengthen failure traceback routing

Exit criteria:

- Multi-writer parallel flow stable with ownership routing

### Phase 3 - Security/Performance Deepening

- Security and performance critics/verifiers
- Network/resilience checks
- N+1 and query hotspot detection
- Refactorer + refactor critic stage

Exit criteria:

- Security/perf blockers reliably prevent progression

### Phase P — Product UX + micro-slice orchestration (v2 — shipped)

**Goal:** full operator product (chat + custom agents) and Hermes runs that advance **one small
code slice at a time** with critique and tests on every slice.

**Prerequisite:** v1 sign-off (§14 **21/21**); Phase **1.5** config store for agent registry when
using Postgres authority.

**Scope (epics fo150–fo154):**

1. **fo150 — Operator chat:** Streamlit chat panel; session thread; launch `POST /v1/runs`; show
   assistant summaries from timeline/gate read-models.
2. **fo151 — Custom agents:** registry (`id`, `display_name`, `system_prompt`, optional
   `bound_role_id`); API CRUD; pencil prompt editor; `custom_agent_id` on `run.created` metadata.
3. **fo152 — Micro-slice model:** workflow block `slice: { enabled, max_files, max_loc }`; planner
   emits `slice.plan`; deterministic diff-budget check before accepting implementation output.
4. **fo153 — Per-slice gates:** stage chain `slice.implement` → `slice.verify` → `slice.critique`
   → `slice.test` → `slice.gate`; unanimous gate blocks next slice until PASS.
5. **fo154 — Context packets:** `SliceContextPacket` (capped paths, diff, test output, prior
   verdicts); LLM prompts assemble from packet when `HERMES_USE_LLM=1`.
6. **fo155 — Diff-aware replan:** after implement, collect git/plan diff stats; on budget fail,
   emit `slice.replan` and narrow `target_paths` (deterministic subdivide + optional LLM replan);
   env `HERMES_SLICE_REPLAN_MAX`.
7. **Scoped slice.implement:** default `HERMES_SLICE_IMPLEMENT=scoped` runs ruff format + `--fix` on
   plan paths before diff budget; `stub` for no-op.

**Exit criteria:**

- Operator can chat to select/create an agent, start a `micro_slice` run, and see **≥2 slices**
  with per-slice gate outcomes in chat + timeline (`HERMES_MICRO_SLICE_COUNT`, default `2`).
- `POST /v1/runs/{id}/lifecycle/verify` and `POST .../lifecycle/slice` run the automatic
  slice chain (`slice.plan` → `slice.gate`); LLM slice plans when `HERMES_USE_LLM=1`.
- Custom agents persist via Postgres config namespace `custom_agents/registry` when DB mode is on.
- Context packets stay under configured character caps on reference fixtures.
- Phase **3** critic **stages:** **fo143–fo146 shipped** (security, performance, network/resilience, refactor panels).

### Phase 4 - Memory and Optimization

**Status (May 2026):** **Shipped (Individual scope)** — **fo160–fo191** in repo; Enterprise fleet/org
memory is Lane **D** **fo202** (not enabled on Individual default install). See [plan_gap.md](plan_gap.md).

**Prerequisites:** Phases **1–3** and **P** shipped; append-only `event_store`; `SliceContextPacket`
(fo154); bundle FAISS pattern (§3A, §14 #12); Postgres config store (§19.5).

#### Normative capabilities

1. **Retrieval memory for prior failures and fixes** — index `finding.created`, gate FAILs, and
   `required_fixes` excerpts; retrieve at planner / micro-slice stages (advisory only).
2. **Bundle usage memory** — record integrator/gate outcomes per `bundle_id` and project tags; bias
   `search_bundles` and integrator ranking from historical success.
3. **Replay framework** — deterministic re-projection of event streams; golden failure fixtures for
   regression (read models and, optionally, verifier re-run).
4. **Role-level model params and budgets** — aggregate per-role token/latency from events; suggest
   adjustments to `model-routing` slices (operator-approved via config store).

**Exit criteria:**

- Measurable reduction in repeat failures (same category / path) across runs on a fixed repo.
- Lower average loop count per stage and improved first-pass slice gate pass rate.
- Memory retrieval is **audited** (`memory.retrieval.emitted` or equivalent) and **bounded** (caps
  on excerpt size and top-k).

#### Index scope (v1)

- **Repo/workspace only:** all memory keys are scoped to `NIMBUSWARE_REPO_ROOT` (or materialized repo
  id). No fleet-wide or multi-tenant index in Phase 4.
- **Collaboration (v1):** individuals may **share vector stores** by exchanging index manifests and
  FAISS blobs (sync protocol below)—not live multi-writer fleet index.
- **Lane D (defer):** enterprise-wide memory, IAM-scoped retention, centralized vector service, and
  cross-org analytics — same defer bucket as fleet SLI and NOTIFY.

#### Package and storage architecture

| Layer | Responsibility |
|-------|----------------|
| **`packages/hermes_memory/`** | Hermes agent subsystem: chunking, embed, index build/search, sync protocol, retrieval API |
| **Postgres** | Metadata rows derived from `event_store` (chunk ids, `run_id`, `finding_id`, `embedding_model_id`, index generation, opt-out flags) |
| **On-disk index (default)** | Under repo root, e.g. `configs/memory/index/` or `.hermes/memory/index/`: `faiss.index`, `memory_order.json`, `manifest.json` (mirrors bundle catalog layout) |
| **Pluggable backend** | Interface supports **local FAISS** (default) and **remote canonical store** (HTTP/file manifest); local install **downloads** snapshot for offline use — **no Qdrant dependency** in v1 |

**Default storage posture:** **Postgres metadata + local FAISS** (same operational model as bundle
search): local-first, Windows-friendly, optional `poetry install --with faiss`.

#### Design principles (normative)

1. **Event-first** — New durable facts enter via append-only events (e.g. `memory.indexed`,
   `memory.retrieval.emitted`) and/or documented derived tables **rebuildable** from `event_store`.
2. **Pinned at run start** — `run.created` freezes `memory_index_version` and retrieval settings
   (like `policy_snapshot`) so mid-run index updates do not change behavior.
3. **Retrieval is advisory** — Memory augments `SliceContextPacket` / prompts; **verifiers and
   unanimous gates take precedence**; no auto-apply of patches from memory without `RequiredFixArtifact`.
4. **Caps** — Reuse fo154 packet limits; add `memory_excerpt` with `HERMES_MEMORY_RETRIEVAL_K` and
   `HERMES_MEMORY_EXCERPT_MAX_CHARS` (names TBD in implementation).
5. **Hermes vs Nimbusware** — Logic in `hermes_memory` + `hermes_orchestrator`; operator toggles and
   read APIs in `nimbusware_console` / `nimbusware_api`.
6. **Privacy** — Repo-relative paths only in index; redact secrets; never index scraper bodies beyond
   existing egress policy.

#### Embeddings and sync

| Mode | When |
|------|------|
| **`deterministic`** | Default for CI and air-gapped runs (hash-based vectors, same family as bundle pseudo-embeddings) |
| **`ollama`** | When `HERMES_USE_LLM=1` and workflow `memory.embedding_mode: ollama` with configured embedding model |
| **`sync`** | CLI (e.g. `hermes-memory-sync` or `nimbusware-config memory sync`) pulls/pushes **manifest + blobs** so a remote canonical store can hydrate **local FAISS** for full offline runs |

Workflow YAML block (normative shape):

```yaml
memory:
  enabled: true
  retrieval_enabled: true          # default-on for production / micro_slice
  index_contribution_default: true # runs contribute unless opted out
  embedding_mode: deterministic    # deterministic | ollama
  sync_url: null                   # optional remote manifest base
  retrieval_k: 5
  excerpt_max_chars: 4000
```

#### Per-run operator controls (default-on with opt-out)

Frozen on `run.created` metadata (API + Streamlit):

| Flag | Effect |
|------|--------|
| `memory.retrieval_enabled` | When `false`, **no reads** from memory for this run (default `true` on `nimbusware_production` / `micro_slice`) |
| `memory.index_contribution` | When `false`, **exclude** this run's findings from future index builds (“do not pollute memory”) |

Console: checkboxes on run create / run detail; timeline shows last retrieval summary.

#### Phase 4 epic map (implementation)

| Track | Epics | Outcome |
|-------|-------|---------|
| **1 — Failure memory** (first) | **fo160–fo164** | Schema, indexer, FAISS, slice/plan retrieval, workflow + console flags |
| **2 — Bundle memory** | **fo170–fo172** | Outcome events, ranking memory, console analytics |
| **3 — Replay** | **fo180–fo181** | Replay harness, golden failure fixtures |
| **4 — Model tuning** | **fo190–fo191** | Telemetry aggregation, routing profile suggestions |

Detail: [plan_gap.md](plan_gap.md) (Phase 4 memory — shipped).

### Lane M — Maker product (fo300–fo308)

**Status (Jun 2026):** **Shipped (core, ~98%)**. Web Maker at `/v1/maker/app/` (`nimbusware_maker_web`); parity matrix all `web: true`. Residual polish: [plan_gap.md](plan_gap.md) **A4+**.

**Goal:** Software from a **business prompt** via **many small careful iterations** on **fully local
hardware**, with a **slimmer maker shell** instead of the operator console as the default surface.

#### Design pillars (normative)

| Pillar | Requirement |
|--------|-------------|
| **Project-scoped maker UX** | `Project` entity: workspace path, template, default workflow profile, requirements artifact; runs scoped to project |
| **Approval + revert** | Explicit HITL: approve plan, preview diff, apply slice, **revert** to last snapshot; events `slice.approved`, `workspace.reverted` |
| **Plain-language progress** | Maker read-models: human sentences + diff summary; operator CSV/metrics hidden in Simple mode; deep dive = **Run theater / group chat** (§20.9) |
| **Local resource honesty** | Readiness API + UI: Ollama health, model id, RAM/disk guidance, slice/token budgets, “degraded/stub” labels; **§20.8** hardware tier + resource governor (Maker + Admin sliders) |

#### Execution substrate

| Item | Requirement |
|------|-------------|
| **Agent tool runtime** | Allowlisted tools: read, grep, write (within slice plan), shell (pytest/ruff only by default) |
| **Workspace snapshots** | Snapshot before each slice apply; store ref on run metadata |
| **Revert API** | `POST /v1/projects/{id}/workspace/revert` or run-scoped revert restoring snapshot |
| **Orchestrator wiring** | `HERMES_SLICE_IMPLEMENT=agent` path calling tool runtime; gates unchanged |

#### Epic map (fo300–fo308)

| Epic | Outcome |
|------|---------|
| **fo300** | **Maker app shell** — `poetry run nimbusware-maker` / `nimbusware-run`; UI at `/v1/maker/app/` (Alpine) |
| **fo301** | **Project model** — CRUD, workspace binding, greenfield/brownfield bootstrap, `NIMBUSWARE_PROJECT_ROOT` per run |
| **fo302** | **Intent intake** — business prompt → clarifications → requirements artifact on `run.created` |
| **fo303** | **Plain-language progress** — maker projections over timeline; test summary card; hide operator telemetry in Simple mode; feeds **§20.9** theater headlines |
| **fo304** | **Slice approval UX** — plan approve, diff preview, apply/skip/revert buttons; pending state blocks auto-advance |
| **fo305** | **Workspace snapshots + revert API** — snapshot before `apply_slice_file_edits`; revert endpoint + events |
| **fo306** | **Agent tool runtime** — package + allowlist; wire `slice.implement` when `HERMES_SLICE_IMPLEMENT=agent` |
| **fo307** | **Local readiness** — `/v1/platform/readiness` + maker home strip; model presets (fast/careful) |
| **fo308** | **First-run wizard** — desktop shell flow: pick folder, smoke test, start first maker run |

**Exit criteria (Lane M):**

- Non-operator user can describe an app, approve a plan, complete **≥2 slices** with diff preview,
  plain test summary, and **revert** one slice — all on local Ollama without opening config tooling.
- Project workspace is isolated from Nimbusware install root.
- Readiness UI explains when hardware/model is insufficient (no silent stub failure).

Sprint board and **recommended build path:** [plan_gap.md](plan_gap.md).

### Lane D — Enterprise edition (fo200–fo207)

**Status (May 2026):** **Core shipped** when `NIMBUSWARE_EDITION=enterprise` (install
`--edition enterprise`). Individual installs remain default and must not require enterprise deps.

| Epic | Normative outcome |
|------|-------------------|
| **fo200** | Edition gate, `GET /v1/platform/edition`, compose profile split |
| **fo201** | Multi-tenant IAM, API keys, `tenant_id` on store |
| **fo202** | Fleet/org-scoped memory index + sync |
| **fo203** | Postgres NOTIFY + `config.document.updated` |
| **fo204** | Object-store primary for scraper artifacts |
| **fo205** | Redis fleet worker profile + health/back-pressure |
| **fo206** | Sustained Ollama p95 SLI + benchmark harness |
| **fo207** | Enterprise console (tenant switcher, fleet dashboards) |

Sprint board detail: [plan_gap.md](plan_gap.md) (enterprise rows). **Ops polish**
(OIDC, K8s charts, external SLI cron) is optional and tracked there—not normative blockers.

---

## 13) Operational Policies

- Hard per-role timeout budgets
- Max retry counts per stage
- Cost/token budget ceilings per run
- Automatic quarantine of noisy critics
- Human override path with full audit trail
- Preserve default preference: multiple critics per producer output with unanimous advancement gates

Operational hardening additions:

- Version and snapshot policy/config/model-routing at run start for deterministic replay
- Enforce model preflight evidence requirements before run transitions from `CREATED` to `RUNNING`
- Track SLO alerts for: stage timeout rate, retry exhaustion rate, false-block rate, and critic
  out-of-domain rate
- Reject blocking findings that lack deterministic `required_fixes` artifacts
- Event store: enforce `event_type`/`payload` pairing in application code; constrain `event_type` in
  PostgreSQL; persist `store_seq` (or equivalent) for deterministic replay
- Agent outputs and event payloads: ship a versioned Pydantic `RequiredFixArtifact` and reference it
  from critic/finding/gate schemas
- Persist `FindingFixStrictnessSettings` in the run policy snapshot and pass it as validation
  context for `finding.created` (see ?4.2A and ?6.3A for snapshot key paths)

---

## 14) Initial Implementation Checklist

1. Stand up local `Ollama` runtime, validate health endpoint, and implement model preflight with ordered fallback policy
2. Initialize Poetry monorepo and package boundaries
3. Build FastAPI scaffolding under **`/v1/`** (e.g. `/v1/runs`, `/v1/runs/{id}/timeline`, `/v1/runs/{id}/findings`; ?6.2)
4. Implement Planner + two critics + unanimous gate engine with deterministic `required_fixes` schema enforcement and finding fix strictness context (?4.2A)
5. Add Backend/Test writer loop with deterministic verifiers
6. Add Traceback Router and owner-role mapping (taxonomy label ��� **Role Registry UUID** for persisted
   `owner_role`; ?3, ?5)
7. Implement append-only PostgreSQL event store with: `store_seq` ordering, DB-level `event_type`
   allowlist, append-only triggers; application-layer validation of `event_type` ��� payload
8. When implementing ?6.6 operational events (e.g. `run.escalated`, `gate.overridden`), add
   append-only event types, extend the ?19.2 PostgreSQL `CHECK` allowlist, and migrate the database
   and application `EventType` / discriminated union in the **same release**
9. Add Pydantic `RequiredFixArtifact` and wire critic/finding/gate events to enforce full deterministic
   fixes (not format-only)
10. Create Windows-specific execution adapter and isolate OS-specific runtime/process handling in compatibility modules
11. Build Streamlit visibility pages for one full run
12. Build bundle catalog and FAISS index from tested modules
13. Add Module Integrator path and compatibility gate thresholds
14. Build persona catalog (business area vs development role) and assignment rules
15. Add Agent Evaluator lifecycle and Persona Coverage Critic gates
16. Add universal critique pairings for every producer/evaluator role
17. Add new-persona self-refinement loop and probation promotion checks
18. Add security and quality scanners to gate chain
19. Define escalation and anti-deadlock policy thresholds
20. Run pilot scenario and tune prompts/contracts
21. **Configuration store (?19.5):** Postgres authority + materialization for personas, role
    registry, workflows, and policy-merge defaults; optional git export/import; freeze
    `policy_snapshot` from materialized config at `run.created`

---

## 15) Pilot Scenario (Your Example Pattern)

Scenario: create a high-quality plan for a domain-specific content/product artifact.

Required panel:

- 1 Planner
- 1 Product Reference Critic
- 1 Domain Critic

Policy:

- All three produce structured outputs
- Both critics must return PASS before implementation planning proceeds
- Failures route back to Planner with explicit required fixes

This scenario becomes your baseline template for broader software flows.

---

## 15A) Pilot Scenario (Bundle-First Software Build)

Scenario: integrate standardized modules into a new or existing codebase with minimal custom code.

Example track:

- Select auth RBAC bundle with admin-configurable role creation and route/page access control
- Select Stripe billing bundle
- Select AWS SES bundle
- Select AWS RDS connection manager bundle (FastAPI)

Required panel:

- Planner
- Bundle Fit Critic
- Integration Safety Critic
- Security Critic
- Performance Critic

Policy:

- Retrieval ranks candidate bundles; planner chooses top fit with justification
- Integration path proceeds only after unanimous mandatory critic PASS
- Failures route to Module Integrator first; rewrite agents engaged only when required

---

## 16) Success Metrics

- Stage pass rate without human intervention
- Average loop count per stage
- Mean time to resolve blocker findings
- False-positive critic rate
- Defect escape rate after final gate
- Security/performance blocker detection precision

---

## 17) Risks and Mitigations

- **Critic hallucination risk** -> enforce evidence schema + verifier precedence
- **Infinite loop risk** -> max retries + escalation arbiter
- **Tool execution risk** -> strict sandbox and command allowlists
- **Prompt drift risk** -> versioned prompts and replay tests
- **Single-model bias risk** -> parameter diversity + deterministic checks

---

## 18) Maintenance and backlog (May 2026)

**Status (Jun 2026):** Core orchestrator, §14 checklist (**21/21**), Phase 4, Lane M web Maker, Lane D enterprise core, §20.6 metrics, ranked backlog **#1–21**, and close-out **A1–A3** are **shipped** (~**97%** overall Individual product per [plan_gap.md](plan_gap.md)). **No v1 blockers.** Further work is optional close-out (**A4+**) or maintenance.

**Operators should use:** [plan_gap.md](plan_gap.md) for close-out items and CI evidence. This file stays the **normative contract**; do not duplicate the sprint board here.

Do not reopen YAML dual-write paths; Postgres materialization remains authoritative when
`NIMBUSWARE_DATABASE_URL` is set.

---

## 19) Implementation Drafts (Config + Event Store)

Use these as starting contracts for code generation and migrations.

### 19.1 `configs/model-routing.yaml` (Draft)

```yaml
version: 1
platform:
  primary_os: windows
  supported_os:
    - windows
    - linux
  compatibility_adapters:
    windows:
      executor: packages/tools/executors/windows_executor.py
      model_runtime: packages/tools/runtime/windows_ollama_runtime.py
    linux:
      executor: packages/tools/executors/linux_executor.py
      model_runtime: packages/tools/runtime/linux_ollama_runtime.py

runtime:
  provider: ollama
  base_url: http://localhost:11434
  health_endpoint: /api/tags
  request_timeout_seconds: 60

preflight:
  required: true
  min_context_tokens: 8192
  max_p95_latency_ms: 8000
  require_structured_json_response: true
  checks:
    - runtime_reachable
    - model_available
    - structured_json_capable
    - context_budget_ok
    - latency_envelope_ok

models:
  primary:
    id: glm-4.7-flash
    temperature: 0.2
    top_p: 0.9
    max_output_tokens: 4096
  fallbacks:
    - id: qwen2.5-coder:14b
      reason_code: primary_unavailable_or_failed_preflight
    - id: llama3.1:8b
      reason_code: secondary_fallback

selection_policy:
  mode: ordered_allowlist
  fail_fast_if_none_pass: true
  persist_selection_event: true
  persist_preflight_evidence: true

finding_fix_strictness:
  minimum_severity_requiring_fixes: MEDIUM   # LOW | MEDIUM | HIGH | BLOCKER
  also_require_fixes_for_low_severity: false

network_egress:
  scraper_role_allowlist: []   # Role Registry role_id UUIDs; [] = explicit empty at this file layer; merged snapshot ?6.3A
  domain_allowlist: []         # [] = explicit empty at this file layer; IPv4/IPv6 normalized ?6.3A; merged ?6.3A
  budget_bytes_per_run: null   # null/omit = no cap at this layer; merged: min(non-neg ints), 0 ok; or null (?6.3A)

contracts:
  required_fixes:
    enforce_deterministic_format: true
    allowed_formats:
      - json_patch
      - unified_diff
    # Mirror in Pydantic as RequiredFixArtifact; embed in critic/finding/gate payloads
    artifact_schema_version: 1
    fields:
      format: required  # json_patch | unified_diff
      target_files: required  # list of repo-relative paths
      patch_artifact: required  # string or structured patch body per format
      validation_steps: required  # e.g. command ids or named checks
      acceptance_criteria: required  # objective pass condition
```

Notes:

- Keep runtime/model adapter code isolated per OS.
- Do not select ad-hoc models outside allowlist.
- Persist model selection and preflight evidence in event store.
- `finding_fix_strictness` mirrors ?4.2A and must be copied into `policy_snapshot` at run start
  (?6.3A); orchestration passes it as Pydantic context key `finding_fix_strictness`.
- `network_egress` governs role-gated scraping (?9.1); keep empty until roles are explicitly
  approved. Snapshot keys: **?6.3A** (`policy_snapshot.network_egress.*`). Merge order,
  **low���high list merge (`[]` wipe, union, dedupe)**, **`[]` vs omit**, and **`budget_bytes_per_run`
  minimum-cap** rules: **?6.3A**.

### 19.2 PostgreSQL Event Store (Append-Only Draft)

Hardening applied in this draft: `store_seq` for replay order, `event_type` allowlist via `CHECK`
(optional: replace with a PostgreSQL `ENUM` maintained in lockstep with the application). When
introducing new append-only event types (e.g. from ?6.6 human override / escalation), **extend** the
`CHECK` constraint list and migrate **in lockstep** with the application `EventType` enum or
discriminated union ��� drift between DB and code is a production incident.

```sql
-- Source of truth: immutable append-only event stream
CREATE TABLE IF NOT EXISTS event_store (
  store_seq BIGSERIAL NOT NULL,
  event_id UUID PRIMARY KEY,
  run_id UUID NOT NULL,
  stage_id UUID NULL,
  task_id UUID NULL,
  event_type TEXT NOT NULL,
  event_version INT NOT NULL DEFAULT 1,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_role TEXT NULL,  -- Role Registry role_id UUID when set; NULL for system/human/non-role actors
  model_id TEXT NULL,
  correlation_id UUID NULL,
  causation_id UUID NULL,
  payload JSONB NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  CHECK (jsonb_typeof(payload) = 'object'),
  CONSTRAINT event_store_type_allowed CHECK (event_type IN (
    'run.created', 'run.started', 'run.failed', 'run.completed',
    'model.preflight.started', 'model.preflight.passed', 'model.preflight.failed',
    'model.selected.primary', 'model.selected.fallback',
    'stage.started', 'stage.blocked', 'stage.passed', 'stage.failed',
    'critic.verdict.emitted',
    'finding.created', 'finding.routed', 'finding.closed',
    'gate.decision.emitted'
  ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_store_store_seq ON event_store(store_seq);
CREATE INDEX IF NOT EXISTS idx_event_store_run_seq ON event_store(run_id, store_seq);

-- Enforce append-only semantics
CREATE OR REPLACE FUNCTION prevent_event_store_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'event_store is append-only; updates/deletes are not allowed';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_event_store_no_update ON event_store;
CREATE TRIGGER trg_event_store_no_update
BEFORE UPDATE ON event_store
FOR EACH ROW EXECUTE FUNCTION prevent_event_store_mutation();
-- Note: EXECUTE FUNCTION requires PostgreSQL 14 or newer. On older versions use EXECUTE PROCEDURE
-- with the same function. Normative local target for Nimbusware: PostgreSQL 14+.

DROP TRIGGER IF EXISTS trg_event_store_no_delete ON event_store;
CREATE TRIGGER trg_event_store_no_delete
BEFORE DELETE ON event_store
FOR EACH ROW EXECUTE FUNCTION prevent_event_store_mutation();

-- Common read/query indexes (occurred_at for display; store_seq for authoritative replay)
CREATE INDEX IF NOT EXISTS idx_event_store_run_time
  ON event_store(run_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_event_store_stage_time
  ON event_store(stage_id, occurred_at)
  WHERE stage_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_event_store_type_time
  ON event_store(event_type, occurred_at);

CREATE INDEX IF NOT EXISTS idx_event_store_payload_gin
  ON event_store USING GIN(payload);

-- Optional idempotency protection for producer retries
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_store_correlation_unique
  ON event_store(correlation_id, event_type)
  WHERE correlation_id IS NOT NULL;
```

Required event types (minimum):

- `run.created`, `run.started`, `run.failed`, `run.completed`
- `model.preflight.started`, `model.preflight.passed`, `model.preflight.failed`
- `model.selected.primary`, `model.selected.fallback`
- `stage.started`, `stage.blocked`, `stage.passed`, `stage.failed`
- `critic.verdict.emitted`
- `finding.created`, `finding.routed`, `finding.closed`
- `gate.decision.emitted`

### 19.3 Read Model Guidance (Non-Authoritative)

- Build `runs_current_status` and `run_timeline_view` as projection tables/views from `event_store`.
- Treat projections as rebuildable caches; never as source-of-truth.
- Rebuild projections by replaying events in **`store_seq` order** (global monotonic insert order).
  Use `occurred_at` only for human-readable timestamps, not for replay determinism.
- Application must validate each row���s `event_type` against the expected payload schema before
  projecting; reject or quarantine invalid rows during replay.
- When re-materializing `metadata` JSONB into typed models, apply the same strict JSON rules as the
  append path (?6.5 implementation note: finite floats, no datetime objects, etc.).

### 19.5 Configuration store (PostgreSQL authority + materialization)

**Problem:** today many subsystems read and write `configs/**/*.yaml` directly (persona CRUD,
workflow apply, role registry fallback, escalation/integrator/self-refinement loaders). That is
fine for solo dev bootstrap but breaks multi-operator edits, optimistic concurrency, and
deterministic `policy_snapshot` freeze (?6.3A).

**Principle:** **Postgres is source of truth; YAML is optional mirror.**

| Layer | Responsibility |
|-------|----------------|
| **Store** | Versioned rows in PostgreSQL (per domain table or `config_key` + `version` + `content` JSONB validated by existing Pydantic modules). |
| **Materializer** | On startup and on change: load store ? validate ? build in-memory `ConfigSnapshot` (persona shelves, role map, workflow dicts, policy defaults, pairings). |
| **Consumers** | `RunOrchestrator`, ingress, API routes, Streamlit?read **only** through materializer interfaces (`PersonaCatalog`, `WorkflowProfileStore`, `RoleRegistry`, etc.). |
| **Audit** | Continue append-only events (`persona.shelf.updated`; add `config.document.updated` if a generic envelope is cleaner). |
| **Gitops** | CLI `export` / `import` / `seed-from-repo`; CI may diff exports without being runtime authority. |

**Migration tiers (do not big-bang in one PR):**

| Tier | Paths | Notes |
|------|--------|------|
| **T1 (first)** | `personas/shelves.yaml`, `roles.yaml`, `workflows/*.yaml` | Highest churn; API already mutates personas/workflows. |
| **T2** | `model-routing.yaml` (policy slices), `escalation/policy.yaml`, `integrator/thresholds.yaml`, `self_refinement/policy.yaml`, `personas/critique_pairings.yaml` | Feeds merge + explainers; read-heavy. |
| **T3 (optional)** | `bundles/catalog.yaml` | Large; may stay file-seeded longer; FAISS remains derived artifacts. |

**Anti-patterns (reject in review):**

- Dual-write: updating both YAML and Postgres without a single winner.
- Per-request file read in hot paths after migration (use materialized cache).
- Ad-hoc ?processor language? for config?reuse Pydantic models from `hermes_extensions` / workflow parsers.

**Run boundary:** at `run.created`, deep-copy the **effective materialized merge** into
`policy_snapshot` (and workflow profile reference by id/version), so replay and audit do not depend
on later operator edits.

**Environment:** prefer `NIMBUSWARE_DATABASE_URL` set ? config from DB; unset ? optional
`import-from-repo` bootstrap or read-only dev fallback (documented, time-limited).

### 19.4 Event / Fix Hardening Checklist (Quick Reference)

- [ ] Pydantic: discriminated union or equivalent so `event_type` always matches payload
- [ ] DB: `store_seq` (or per-run sequence) assigned on insert; projections `ORDER BY store_seq`
- [ ] DB: `event_type` constrained to approved set (CHECK or ENUM)
- [ ] Pydantic: `RequiredFixArtifact` v1; embedded in critic/finding/gate paths for blockers
- [ ] Tests: reject mismatched type/payload; reject unknown `event_type` at insert
- [ ] When adding operational event types (?6.6): migrate PostgreSQL `CHECK` allowlist and app
  `EventType` / union in the same release

---

## 20) Growth roadmap — coding platform competitiveness (May 2026)

**Purpose:** Normative backlog for making Nimbusware stronger as a **governed coding
factory** (not a general chat workspace), with Hermes providing the adversarial agent runtime.
Items deepen existing moats (**§4**, **§12 Phase P**,
**Lane M**, **Lane D**) or close gaps versus IDE agents (Cursor, Continue, Cline), CLI pair
programmers (Aider), and autonomous repo agents (OpenHands, SWE-agent).

**Tracking:** Implementation status and sprint order live in [plan_gap.md](plan_gap.md); this
section is the **product intent**. Proposed epic ids use **fo400+** to avoid colliding with
shipped **fo150–fo308** / **fo200–fo207**.

### 20.1 Strategic positioning (normative)

| Hermes wins when… | Hermes loses when… |
|-------------------|-------------------|
| Teams need **audited, policy-bound** multi-stage code change | User wants **sub-second** inline edit in the IDE |
| **Slice + gate** discipline beats one-shot large diffs | User wants **zero setup** (`pip install` + one command) |
| **Event timeline** is the system of record | User only needs a **single agent** with shell access |
| **Bundle integrator + personas** encode org golden paths | User wants **best chat UX** or email/calendar workspace |

**North star (coding):** *An AI pipeline that behaves like audited CI with specialized reviewers —
not a faster terminal agent.*

### 20.2 Deepen strengths (double down)

These extend capabilities Hermes already has; they are **higher priority** than feature parity
with chat UIs.

#### Governance and audit trail

| Item | Epic | Normative outcome |
|------|------|-------------------|
| **Gate → external CI bridge** | **fo400** | Map `slice.gate` / `gate.decision.emitted` to GitHub Checks / GitLab pipeline status; PR comment with timeline link |
| **Policy diff on replay** | **fo401** | CLI/API: compare `policy_snapshot` on run A vs B; explain why gate behavior differed |
| **Exportable audit bundle** | **fo402** | Nimbusware API audit export for run `{id}` → signed tarball (events JSONL + artifacts + policy snapshot) for compliance |
| **Human override events** | **fo403** | Ship `gate.overridden`, `run.escalated` on event store + Admin UI (?6.6); same-release DB `CHECK` migration |

#### Micro-slice and bounded change

| Item | Epic | Normative outcome |
|------|------|-------------------|
| **Per-slice git commit** | **fo410** | Optional auto-commit per passed slice with message from `slice.plan`; branch per run |
| **Slice budget presets** | **fo411** | Maker presets: `tiny` / `standard` / `careful` mapping to `max_files`, `max_loc`, replan max |
| **E2E slice stage** | **fo412** | Workflow profile flag `slice.e2e`: Playwright (or configured runner) after `slice.test` for web apps |
| **Diff review API** | **fo413** | `GET /v1/runs/{id}/slices/{n}/diff` unified diff + file list for Maker/PR bots without Streamlit |

#### Adversarial critics and personas

| Item | Epic | Normative outcome |
|------|------|-------------------|
| **Critic reliability dashboard** | **fo420** | Aggregate out-of-domain rate, false-block rate, quarantine (?3D, ?13) in Admin Console |
| **Custom critic packs** | **fo421** | Postgres-documented critic profiles (domain + blocking_authority) installable per workflow |
| **Persona probation automation** | **fo422** | Auto-shelve personas below reliability threshold; notify operator before promotion (?3B.6) |
| **Integrator live path** | **fo423** | Harden integration adapter writer beyond scaffold: manifest validation, target-state apply with rollback |

#### Bundle-first engineering

| Item | Epic | Normative outcome |
|------|------|-------------------|
| **Bundle outcome analytics** | **fo430** | Console panel: fit score vs gate pass rate per `bundle_id` (extends fo170–fo172) |
| **Compatibility preflight** | **fo431** | Before integrator stage: dependency/version conflict report against target `pyproject` |
| **Catalog operator CRUD** | **fo432** | Postgres bundle catalog (§19.5 T3) + Admin Config Bundles editor with candidate promotion |

#### Platform and enterprise

| Item | Epic | Normative outcome |
|------|------|-------------------|
| **Fleet run comparison** | **fo440** | Enterprise: compare Ollama SLI + gate pass rates across tenants (read-only analytics) |
| **Config change blast radius** | **fo441** | Preview which active runs would see different gates if workflow edited (materializer dry-run) |
| **SOC2-oriented audit export** | **fo442** | Enterprise: IAM action log + event export API with retention policy hooks |

#### Engineering quality (moat maintenance)

| Item | Epic | Normative outcome |
|------|------|-------------------|
| **Pipeline mixin typing** | **fo450** | Remove `_pipeline.*` mypy `ignore_errors`; type MRO incrementally (?ARCHITECTURE) |
| **E2E on every PR** | **fo451** | Promote `tests/e2e/` from weekly to required CI subset when Postgres service available |
| **SWE-bench harness** | **fo452** | Optional benchmark job: Hermes `micro_slice` profile on public fixture repos (marketing + regression) |

### 20.3 Close gaps (learn from competitors)

These address **weaknesses** versus coding-focused alternatives; many complement **Lane M**
(fo300–fo308) without replacing orchestration core.

#### Developer experience and speed

| Gap vs peers | Learn from | Item | Epic | Normative outcome |
|--------------|------------|------|------|-------------------|
| No IDE integration | Cursor, Continue, Cline | **IDE bridge** | **fo460** | MCP or LSP server: stream run status, open slice diff, approve gate from editor |
| High setup friction | Aider | **Quick local mode** | **fo461** | `nimbusware-maker --quick`: in-memory store + stub critics + single-package slice for solo dev |
| Git not first-class | Aider | **Git-native outputs** | **fo462** | Branch naming, commit messages, `gh pr create` helper after final gate PASS |
| Slow feedback loop | Cursor | **Hot slice path** | **fo463** | Skip full critic matrix for `severity < HIGH` when workflow `fast_slice: true` (explicit opt-in) |

#### Maker / product UX

| Gap vs peers | Learn from | Item | Epic | Normative outcome |
|--------------|------------|------|------|-------------------|
| Streamlit credibility | Odysseus, Open WebUI | **Maker web v2** | **fo470** | Lightweight SPA (or embedded component) for slice loop; Streamlit remains Admin |
| Plain-language only partial | Lane M fo303 | **Progress streaming** | **fo471** | SSE/WebSocket: live slice status + **§20.9** theater messages to Maker without polling |
| Model onboarding friction | Odysseus Cookbook | **Model wizard** | **fo472** | Subsumed by **fo532–fo534** (§20.8): fit-ranked models + readiness; keep fo472 as Maker UX alias |
| No mobile | Odysseus PWA | **Read-only PWA** | **fo473** | Approve/reject slice + progress view on phone (defer full implement on mobile) |

#### Execution safety and verification

| Gap vs peers | Learn from | Item | Epic | Normative outcome |
|--------------|------------|------|------|-------------------|
| No full sandbox | OpenHands, E2B | **Sandbox backend** | **fo480** | Optional per-run container/VM for `hermes_agent_tools` shell (policy-pluggable) |
| Unit tests only | Playwright, Devin | **Browser verify stage** | **fo412** | (see §20.2) |
| Tool power without isolation | Odysseus threat model | **Filesystem jail** | **fo481** | Workspace-root bind + deny paths outside project; align with ?9 Windows executor |

#### Context and code intelligence

| Gap vs peers | Learn from | Item | Epic | Normative outcome |
|--------------|------------|------|------|-------------------|
| Path-list slice plans | Cursor repo map | **Repo map injection** | **fo490** | Build tree + import graph excerpt into `SliceContextPacket` (cap bytes like fo154) |
| Weak symbol awareness | LSP | **LSP-assisted plan** | **fo491** | Optional: resolve symbols for `target_paths` before `slice.implement` |
| Memory vs chat history | Aider | **Session memory UI** | **fo492** | Maker: show which memory chunks influenced this slice (`memory.retrieval.emitted`) |

#### Enterprise and deploy

| Gap vs peers | Learn from | Item | Epic | Normative outcome |
|--------------|------------|------|------|-------------------|
| OIDC design-only | LibreChat | **OIDC / SSO** | **fo500** | Enterprise: OIDC for Admin + Maker; API keys remain for automation |
| Partial k8s | Helm charts | **Full reference stack** | **fo501** | `docs/deploy/k8s`: postgres, redis worker, maker console, migration job |
| No public benchmark | SWE-agent | **fo452** | (see §20.2) |

#### Lane M completion (existing normative — prioritize)

These are **already specified** in **§7.3** and **Lane M (fo300–fo308)**; treat as **P0 gap
closure** for coding product credibility:

| Epic | Status intent |
|------|----------------|
| **fo305–fo306** | Workspace snapshots + agent tool runtime wired to `slice.implement` |
| **fo304** | Slice approval UX blocking auto-advance |
| **fo301–fo302** | Project workspace isolated from Nimbusware install root |
| **fo307–fo308** | Readiness + first-run wizard |

### 20.7 Researcher & Stitcher roles (external discovery + transplant)

**Implementation status (Jun 2026):** **Shipped (core ~92%)** in `packages/hermes_research/` — Maker Review + Admin run detail research/stitch panels; bundle catalog CRUD close-out in **A3**.

**Goal:** Before (and during) planning, Hermes **researches** comparable products and OSS
patterns, then **transplants** vetted modules with minimal rewrites—instead of regenerating auth,
IAM, billing, etc. from scratch. Research output is **structured, auditable, and retrieval-ready**;
Stitch output is **bounded, gated, and Refactor-cleaned**.

**Relationship to existing roles:**

| Existing | Researcher / Stitcher |
|----------|------------------------|
| **Module Integrator** | Internal **bundle catalog** (FAISS over `configs/bundles/`) |
| **Code Researcher** | External **OSS / docs** discovery → pattern index for Planner |
| **Stitcher** | External or catalog **file-tree transplant** + wiring deltas |
| **Integration Adapter Writer** | Thin shims **after** Stitcher when API surface mismatches |
| **Refactorer** | **Mandatory** post-stitch normalization (lint, style, module layout) |
| **Scraper stage** | Low-level HTTP fetch; Researchers **consume** artifacts via policy |

#### 20.7.1 Researcher taxonomy (normative)

Two producer sub-roles under a shared **Research** workflow stage (both Role Registry UUIDs;
composite persona = Business Area shelf + Research development role where applicable).

| Sub-role | Shelf axis | Mission | Primary outputs |
|----------|------------|---------|-----------------|
| **Domain Researcher** | Business Area (e.g. Golf Scheduling Expert) | Find how the **product/domain** works in the real world: user journeys, regulations, terminology, competitor features | `ResearchBrief` (domain), `domain.critic.proposed` payloads, glossary + constraint list |
| **Code Researcher** | Development Role (Research Engineer) | Find **similar codebases**, libraries, and architectural patterns (GitHub, docs, benchmarks) | `ResearchBrief` (code), `research.pattern.indexed` chunks, license/spi notes, candidate `transplant_source` refs |

**Example (golf scheduling app):**

1. Intent: “app for golf tee-time scheduling.”
2. **Domain Researcher** (golf / sports-ops shelf): collects calendar rules, pace-of-play norms, handicap policies → proposes **Domain Critic** definitions (or extends Persona Coverage Critic inputs).
3. **Code Researcher**: finds OSS schedulers, booking APIs, FastAPI auth samples → indexes patterns.
4. **Planner** reads both briefs + bundle RAG + failure memory.
5. Need auth/IAM → **Code Researcher** ranks candidates → **Stitcher** transplants → **Refactorer** aligns style.

**Default policy:** Research runs **after** Agent Evaluator / persona assignment and **before**
Planner draft (?4.1 step 3 insert). Optional **re-research** on plan gate FAIL when
`failure_category=missing_context|domain_gap|no_suitable_module`.

#### 20.7.2 Stitcher role (normative)

**Mission:** Given an approved `transplant_candidate` (from Code Researcher, bundle catalog, or
operator pin), copy the **minimal file set** into the project workspace, adjust **imports,
config hooks, and dependency declarations** only—no broad API redesign.

**Hard constraints:**

- Transplant budget: `max_files`, `max_loc`, `max_new_dependencies` (workflow block, like micro-slice).
- **License allowlist** in `policy_snapshot` (e.g. MIT, Apache-2.0 only unless operator override).
- **No** transplant without prior `research.brief.emitted` or `bundle_id` with integrator PASS path.
- **Refactorer stage is mandatory** after `stitch.applied` before slice gate PASS on stitch stages.

**Handoff chain:**

```text
Code Researcher ──► transplant_candidate (manifest)
        │
        ▼
   Stitcher ──► stitch.plan ──► stitch.apply (workspace snapshot before apply)
        │
        ▼
   Refactorer ──► refactor (standards) ──► existing critic matrix + verifiers
        │
        ▼
   Micro-slice / writers for gaps only
```

#### 20.7.3 Pipeline placement (?4.1 extension)

Insert into canonical pipeline (**§4.1**) after persona evaluation, before planning:

| Step | Stage | Roles |
|------|-------|-------|
| 2a | `research.domain` | Domain Researcher → domain brief + critic proposals |
| 2b | `research.code` | Code Researcher → code brief + pattern index update |
| 3 | Planner | Consumes `ResearchBrief[]`, bundle RAG, memory excerpts |
| 7b | `stitch.plan` / `stitch.apply` | Stitcher (when plan selects `path=transplant`) |
| 7c | `refactor.post_stitch` | Refactorer (mandatory) |
| 8+ | (unchanged) | Writers, critics, verifiers, micro-slice |

**Routing policy (normative):**

- `implementation_strategy: transplant` → Stitcher path when Code Researcher confidence ≥
  threshold **or** bundle integrator score ≥ threshold.
- `implementation_strategy: rewrite` → skip Stitcher; Frontend/Backend Writers (existing).
- Domain Researcher **always** runs when `workflow.research.domain_enabled` and intent tags include
  a new `domain_tag` not present on persona shelves.

#### 20.7.4 Integration hooks (connections to existing subsystems)

| Hook | Package / surface | Connection |
|------|-------------------|------------|
| **Role Registry** | `configs/roles` → Postgres | Register `domain_researcher`, `code_researcher`, `stitcher` UUIDs; critique pairings (?3C) |
| **Persona shelves** | `hermes_extensions.personas` | Business-area researchers on **3B.1** shelf; Code Researcher on **3B.2**; Agent Evaluator may **spawn** domain shelf entries (?3B.4) |
| **Network egress** | `policy_snapshot.network_egress` (?6.3A, ?9.1) | Add researcher role UUIDs to `scraper_role_allowlist`; separate **research domain allowlist** (github.com, readthedocs, vendor docs); byte budget per run |
| **Scraper stage** | `hermes_orchestrator` scraper mixin | Researchers request fetches via scraper; bodies land in `.cache/hermes_scraper/` or object store (fo204); **prompt_security** wrapper for untrusted HTML (? Odysseus-style policy in plan spirit) |
| **Executor** | `hermes_executor` | Role-gated egress only; researchers never bypass allowlist |
| **Event store** | `agent_core` + `hermes_store` | New append-only types (§20.7.5); extend PostgreSQL `CHECK` in same release |
| **Research pattern index** | `hermes_memory` (new namespace) | **Separate** from failure-memory FAISS: `configs/research/index/` or `hermes_research_chunk` table; embed `ResearchPattern` excerpts for Planner retrieval |
| **Failure memory** | Phase 4 `hermes_memory` | Unchanged; stitch failures also emit `finding.created` → future failure memory |
| **Bundle catalog** | `hermes_extensions.catalog` | Code Researcher may **promote** external repo into catalog candidate; Stitcher may consume **either** external manifest or `bundle_id` |
| **Bundle memory** | `hermes_bundle_outcome` | Stitcher transplants from bundles record outcomes same as integrator gate |
| **Planner** | `_pipeline` plan stage | `plan.context` includes merged `ResearchBrief` + top-k `research.pattern` hits (capped, fo154-style) |
| **SliceContextPacket** | `slice_context_packet.py` | Optional `research_excerpt` field for implement stages |
| **Stitcher workspace** | Lane M fo305 | **Snapshot before `stitch.apply`**; revert API restores pre-transplant tree |
| **Agent tools** | `hermes_agent_tools` | Stitcher uses allowlisted read/write/copy; not unrestricted shell |
| **Config store** | `nimbusware_config` | Workflow blocks: `research:`, `stitch:`; domain→critic templates in Postgres |
| **API / Maker** | `nimbusware_api`, `nimbusware_maker` | Approve research brief; preview transplant diff; plain-language “found 3 OSS auth libs” |
| **Admin Console** | `nimbusware_console` | Research timeline panel, pattern index status, license warnings |
| **Materializer** | `nimbusware_config` | Freeze `research_policy` + `stitch_policy` in `policy_snapshot` at `run.created` |

#### 20.7.5 Events, artifacts, and contracts

**New event types (minimum — migrate ?19.2 `CHECK` + `EventType` in one release):**

| Event type | When | Payload highlights |
|------------|------|-------------------|
| `research.brief.emitted` | Domain or Code Researcher completes | `brief_kind: domain\|code`, `domain_tag`, `sources[]` (url, license, trust_tier), `summary`, `artifact_id` |
| `research.pattern.indexed` | Code Researcher indexes OSS pattern | `pattern_id`, `repo_url`, `paths[]`, `embedding_ref`, `license` |
| `domain.critic.proposed` | Domain Researcher proposes new critic | `critic_template`, `allowed_domains`, `blocking_authority`, `evidence_refs` |
| `transplant.candidate.selected` | Planner or operator picks source | `candidate_id`, `source_kind: oss\|bundle`, `license`, `compatibility_score` |
| `stitch.plan.emitted` | Stitcher plans file set | `target_paths[]`, `source_manifest`, `wiring_delta_summary` |
| `stitch.applied` | Files written | `snapshot_ref`, `files_added[]`, `deps_added[]` |
| `stitch.failed` | Transplant aborted | `reason_code`, `rollback_snapshot_ref` |

**Artifacts (immutable FS or object store, pointer on event):**

- `ResearchBrief` — JSON schema (Pydantic): domain glossary, competitor table, code pattern summaries.
- `TransplantManifest` — source tree hash, file list, license file paths, required env vars.
- `StitchWiringDelta` — unified diff of import/config changes only (not full module bodies in event).

**Critique pairings (?3C extension):**

| Producer | Mandatory critics |
|----------|-------------------|
| Domain Researcher | Persona Coverage Critic, Domain Critic (existing or proposed), Spec Compliance Critic |
| Code Researcher | Integration Safety Critic (license/SPI), Security Critic (supply chain), Spec Compliance Critic |
| Stitcher | Integration Safety Critic, Bundle Fit Critic (if from catalog), Security Critic, Refactor Critic (after Refactorer output) |

**Domain critic provisioning:** Domain Researcher does **not** auto-enable critics in production.
It emits `domain.critic.proposed` → operator or Agent Evaluator **promotes** via config store
(same probation story as **§3B.6**).

#### 20.7.6 Workflow configuration (normative YAML shape)

```yaml
research:
  enabled: true
  domain_enabled: true
  code_enabled: true
  max_brief_sources: 20
  pattern_index_contribution: true   # feed research.pattern index
  egress:
    extra_domain_allowlist: []       # merged into policy_snapshot.network_egress
  domain_tags_from_intent: true      # derive golf, fintech, etc. from requirements artifact

stitch:
  enabled: true
  max_files: 40
  max_loc: 2500
  max_new_dependencies: 10
  license_allowlist: [MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause]
  require_refactor_pass: true
  prefer_bundle_over_oss_when_score_within: 0.05
```

Frozen on `run.created` under `metadata.research` and `metadata.stitch` (mirror `metadata.memory`).

#### 20.7.7 Epic map (fo510–fo529)

| Epic | Outcome |
|------|---------|
| **fo510** | Role Registry + critique matrix rows for Domain Researcher, Code Researcher, Stitcher |
| **fo511** | `research.brief.emitted` + `ResearchBrief` Pydantic models + artifact store |
| **fo512** | Domain Researcher stage + `domain.critic.proposed` + shelf/persona hooks |
| **fo513** | Code Researcher stage + scraper/egress wiring (?9.1) |
| **fo514** | Research pattern index (`hermes_memory` namespace or `packages/hermes_research/`) + `research.pattern.indexed` |
| **fo515** | Planner read-model: merge domain + code briefs into plan stage context |
| **fo516** | API: `GET /v1/runs/{id}/research` + Maker approve/reject brief |
| **fo520** | Stitcher: `stitch.plan` / `stitch.apply` + `TransplantManifest` validation |
| **fo521** | Workspace snapshot + revert integration (Lane M fo305) for stitch |
| **fo522** | Mandatory `refactor.post_stitch` stage + gate chain |
| **fo523** | License scanner + dependency diff verifier on stitch |
| **fo524** | Console: research timeline + transplant preview panels |
| **fo525** | Bundle catalog promotion path: Code Researcher → catalog candidate → Integrator/Stitcher |
| **fo526** | Re-research on plan FAIL (`missing_context` routing) |
| **fo527** | Enterprise: tenant-scoped research index + egress audit export |
| **fo528** | Tests: golden golf-domain fixture + auth-transplant fixture (no live network in CI) |
| **fo529** | `prompt_security` wrapper for all researcher LLM prompts containing fetched content |

#### 20.7.8 Security and non-goals

- Researchers are **high egress** roles: admin-gated on Individual; explicit allowlist per deployment.
- Fetched content is **untrusted** until summarized into `ResearchBrief`; never execute fetched code.
- Stitcher **never** runs without license check event on the audit trail.
- **Non-goals:** fully autonomous “clone any repo”; live crawling on every PR; replacing human
  choice of transplant source without Maker/Admin approval on first use per `candidate_id`.

#### 20.7.9 Success metrics (Researcher / Stitcher)

| Metric | Target |
|--------|--------|
| Planner runs with research brief attached | ↑ vs baseline |
| Transplant path vs full rewrite ratio | Measurable; transplants should ↑ for commodity modules (auth, IAM) |
| Post-stitch Refactorer loop count | ≤ 2 median |
| Integrator/security gate pass rate after stitch | ≥ bundle-only integrator baseline |
| Repeat `missing_context` plan failures | ↓ after fo526 re-research |

### 20.8 Hardware awareness & resource governor (Odysseus-class, Nimbusware-native)

**Goal:** Nimbusware **detects local (or SSH-remote) hardware**, **recommends and auto-selects**
models/workflows within safe RAM/VRAM envelopes, and **limits parallel agent/LLM work** so runs
stay stable on weak boxes—without abandoning throughput on strong ones. Operator controls live in
**Maker** (simple presets + sliders) and **Admin Console** (full governor + fleet view).

**Today (baseline — do not duplicate blindly):**

| Surface | What exists |
|---------|-------------|
| `nimbusware_maker.readiness` | RAM avail (Windows/Linux), disk, Ollama reachability, static **fast/careful** presets |
| `hermes_orchestrator.preflight` | Model latency p95, context length, JSON probe (?4.4) |
| `GET /v1/platform/readiness` | Aggregates readiness for Maker strip |
| `parallel_writers.run_parallel_writer_group` | Unbounded `asyncio.gather` for writer stages |
| `fo206` fleet Ollama SLI | Sustained health p95 (Enterprise); feeds routing suggestions |

**Gap vs Odysseus Cookbook / `services/hwfit`:** GPU grouping (NVIDIA/AMD/Apple), VRAM-aware
model **fit scoring**, unified-memory handling, remote host probe, and **dynamic** parallel
serving limits tied to live memory pressure.

#### 20.8.0 Odysseus Cookbook — feature inventory (reference)

Odysseus **Cookbook** is a first-class UI module (`static/js/cookbook*.js`, `routes/cookbook_routes.py`)
built on **`services/hwfit/`** (hardware probe + VRAM fit math + serve profiles). It is **not** the
same as chat/agent memory; it answers: *“What can this machine run, and how do I get it running?”*

**A. Hardware scan (`hardware.py` → `detect_system`)**

| Capability | Behavior |
|------------|----------|
| **Probe targets** | Local host; optional **SSH remote** (`host`, `ssh_port`, `platform`: windows \| linux \| termux) |
| **Cache** | 30-minute TTL; **Rescan** forces `fresh=True` |
| **RAM** | Total + available GB; Windows uses PowerShell/WMI path when `/proc` is useless |
| **CPU** | Core count + model name |
| **NVIDIA** | `nvidia-smi` memory.total + name; SSH fallbacks for PATH; unified-memory devices when VRAM is `[N/A]` (Grace/GB10 class) |
| **AMD** | ROCm path; `classify_amd_gfx` → RDNA vs CDNA vs GCN (steers vLLM vs GGUF) |
| **Apple Silicon** | Metal backend; `unified_memory: true`; VRAM budget uses system RAM pool |
| **Multi-GPU** | Per-device list + **`gpu_groups`**: identical (name, rounded VRAM) pools with **device indices** for `CUDA_VISIBLE_DEVICES` / homogeneous serve |
| **Homogeneous flag** | Whether all GPUs can tensor-parallel / single-pool serve |
| **Errors** | Surfaces driver mismatch (`NVML` errors) instead of silent “No GPU” |

**B. Model catalog (`models.py` + `data/hf_models.json`)**

| Capability | Behavior |
|------------|----------|
| **Catalog** | ~270+ Hugging Face–style entries (params, MoE flag, active params, context length, architecture tags) |
| **Quant ladder** | GGUF quants `Q8_0` … `Q2_K`; separate **prequantized** paths (AWQ, GPTQ, FP8, MLX, NVFP4, …) |
| **VRAM estimate** | `estimate_memory_gb(model, quant, ctx)` = weights + KV cache (active params for MoE) + overhead |
| **Use-case inference** | `coding`, `chat`, `reasoning`, `multimodal`, `embedding`, `tts`, `stt`, `general` from name/tags |
| **Best quant for budget** | Walks quality ladder until fit in VRAM/RAM |

**C. Fit scoring (`fit.py` → `analyze_model` / `rank_models`)**

| Output field | Meaning |
|--------------|---------|
| **`fit_level`** | `perfect` \| `good` \| `marginal` \| `too_tight` (still listed so user can see what *would* fit on bigger HW) |
| **`run_mode`** | `gpu` \| `cpu_offload` \| `cpu_only` \| `no_fit` |
| **`required_gb`** | Estimated memory for chosen quant + context |
| **`speed_tps`** | Heuristic tok/s (GPU bandwidth table + offload fraction blend for CPU spill) |
| **`score`** | Weighted composite: quality, speed, fit, context — weights vary by **use_case** |
| **`scores.*`** | Sub-scores for UI columns / sorting |
| **`gpu_only` mode** | When user selects a GPU tier, **disable RAM offload** so rankings show what fits **on VRAM**, not 175B models that only “fit” via CPU spill |
| **Coding bias** | `USE_CASE_WEIGHTS["coding"]` emphasizes quality + speed for code models; coder-specialized models get +6 when filter=coding, −10 when browsing general |
| **Sort keys** | score, speed, vram, params, context, newest |

**Composite score (example weights for `coding`):** 50% quality, 20% speed, 15% fit, 15% context — differs per use case.

**D. Serve profiles (`profiles.py` → `compute_serve_profiles`)**

Deterministic **Quality / Balanced / Speed** presets for **llama.cpp** (download mode varies quant; serve mode fixes quant to on-disk GGUF):

| Profile | Typical quant | KV cache | Context | Notes |
|---------|---------------|----------|---------|-------|
| Quality | Q6_K (or largest that fits) | q8_0 | up to model max | MoE may set `n_cpu_moe` offload |
| Balanced | Q4_K_M | q4_0 | full cap | Speed/quality tradeoff |
| Speed | smallest full-GPU fit | q4_0 | 32k (halved until fits) | Trims context first |

Outputs: `n_gpu_layers`, `n_cpu_moe`, `cache_type`, `ctx`, `est_vram_gb`, `fits`, `offloads`, human `note`. Vision models reserve ~1 GB encoder headroom.

**E. Cookbook UI workflows (Odysseus — out of scope to copy verbatim)**

| Workflow | What it does |
|----------|----------------|
| **Hardware panel** | Shows scan, GPU toggles (multi-GPU), RAM vs GPU mode, remote server picker |
| **Model list** | Ranked table with fit badges, expand row for details / GGUF sources |
| **Download** | HF token, background download to `data/huggingface`, tmux jobs |
| **Serve** | vLLM, SGLang, llama.cpp, Ollama, diffusion — remote SSH; **Dependencies** installs pip/OS packages per server |
| **Presets** | Saved hardware + filter state (`cookbook_state.json`) |
| **Diagnosis** | Log pattern matching for serve failures |

**F. Known operational lessons (inform Nimbusware UX)**

- Docker without GPU passthrough → wrong GPU (iGPU) or 0 VRAM — need compose overlays / `check-docker-gpu.sh`.
- macOS: Cookbook serve via vLLM limited; **Ollama + Metal** is the supported local path (Nimbusware + Hermes already align here).
- Prequantized AWQ/GPTQ models must not be rated “GOOD” on backends that cannot serve them (backend-aware filtering).

#### 20.8.1 Transplant strategy (normative — not a monolith copy)

Odysseus ships **`services/hwfit/`** (`hardware.py`, `fit.py`, `models.py`, `profiles.py`) under
**MIT**. A wholesale copy into Nimbusware is **not** appropriate:

| Odysseus piece | Nimbusware action |
|----------------|---------------|
| `hardware.py` (~GPU/RAM/CPU probe, SSH remote, 30m cache) | **Port** into `packages/nimbusware_hw/probe.py`; strip `services.*` imports; Windows-first per ?2.4; preserve `gpu_groups`, `homogeneous`, `unified_memory` |
| `fit.py` + `models.py` (VRAM fit tables, quant heuristics, `rank_models`) | **Adapt** as `nimbusware_hw/fit.py`; filter catalog to **`model-routing.yaml` allowlist** + Ollama tag names; default **`use_case=coding`**; record MIT in `ACKNOWLEDGMENTS.md` |
| `profiles.py` (Quality/Balanced/Speed llama.cpp flags) | **Translate** to Ollama equivalents (`num_ctx`, `num_gpu`, quant tag) in `nimbusware_hw/ollama_presets.py` — not literal `-ngl` / KV cache strings |
| `data/hf_models.json` | **Optional sync** job → `configs/hardware/model_catalog.json` (subset); primary source remains routing allowlist + Ollama `show` sizes |
| `cookbook-hwfit.js` (scan, GPU toggles, ranked list, fit badges) | **Reimplement** as Maker **Model Manager** panel + shared React components (§20.8.10) |
| `cookbookDownload.js` / HF pull | **Out of scope** — Maker shows `ollama pull <tag>` with copy button; no in-app HF download |
| `cookbookServe.js` / vLLM / llama.cpp / tmux | **Out of scope** — runtime is Ollama only (?19.1) |
| `cookbook-diagnosis.js` | **Partial** — map common Ollama errors to readiness hints (not full log-regex serve doctor) |
| Dependencies panel (`/api/cookbook/packages`) | **Narrow** — check `ollama`, `docker` (if used), Python venv, optional `nvidia-smi`; no pip install from UI in Individual tier |

**Implementation rule:** one **hardware probe adapter** + one **resource governor** consumed by
orchestrator, API, and UIs—no Streamlit/Cookbook coupling.

#### 20.8.2 `nimbusware_hw` package (proposed)

| Module | Responsibility |
|--------|----------------|
| `probe.py` | `detect_hardware_profile(fresh=False, host=None)` → `HardwareProfile` (RAM total/avail, CPU, GPU groups, backend, unified_memory flag) |
| `fit.py` | Port `analyze_model` / `rank_models`: `fit_level`, `run_mode`, `score`, `scores.*`, `gpu_only` flag; default `use_case=coding` weights; allowlist = `model-routing.yaml` |
| `ollama_presets.py` | Map Odysseus `compute_serve_profiles` outputs → Ollama tag + `num_ctx` suggestions (§20.8.10 Screen C) |
| `pressure.py` | Sample current RAM/VRAM; compare to governor caps; return `ok \| warn \| throttle \| block` |
| `governor.py` | `ResourceGovernor.from_profile(profile, settings)` → limits document |

**`HardwareProfile` persisted** (not recomputed every slice):

- Postgres table `hermes_hardware_profile` **or** repo-local `.hermes/hardware/profile.json` (Individual default).
- Event: `hardware.profile.detected` on change (append-only).

#### 20.8.3 Resource governor settings (operator-facing)

Frozen subset on `run.created` as `policy_snapshot.resource_governor` (?6.3A extension).

| Setting | Default | Effect |
|---------|---------|--------|
| `auto_adjust` | `true` | Apply derived limits when run starts; else manual only |
| `max_system_ram_pct` | `75` | Cap estimated RAM for Nimbusware + Ollama + index builds combined |
| `max_vram_pct` | `85` | Cap GPU memory for loaded model(s); unified memory uses `max_system_ram_pct` instead |
| `reserve_ram_gb` | `2.0` | Headroom for OS / desktop shell |
| `reserve_vram_gb` | `0.5` | Headroom on discrete GPUs |
| `max_parallel_writer_stages` | derived | Upper bound for `run_parallel_writer_group` (1 on low RAM) |
| `max_concurrent_llm_calls` | derived | Semaphore across critic/writer LLM stages |
| `max_micro_slices_inflight` | `1` on weak / `2` on strong | Throttle slice chain when pressure = `throttle` |
| `context_budget_tokens` | derived from fit | Overrides per-role caps in materialized routing when auto |
| `degrade_to_stub` | `true` when pressure = `block` | Skip LLM; deterministic stub paths with Maker warning |

**Derived limits (normative algorithm sketch):**

1. Probe hardware → pick **tier**: `weak` (avail RAM &lt; 8 GB or no GPU and RAM &lt; 16 GB), `medium`, `strong`.
2. Map tier → default `max_parallel_writer_stages` (1 / 2 / 4) and `max_concurrent_llm_calls` (1 / 2 / 4).
3. Clamp by operator sliders (`max_system_ram_pct`, `max_vram_pct`).
4. If Ollama reports loaded model size + profile VRAM → reduce concurrent LLM to 1 before OOM.

#### 20.8.4 Integration hooks

| Consumer | Hook |
|----------|------|
| **Preflight** (?4.4) | Pass `HardwareProfile`; reorder fallback allowlist by fit score; fail fast if no model fits within VRAM cap |
| **`build_platform_readiness`** | Add `hardware` check: GPU name, VRAM, tier, recommended preset; replace static fast/careful hints with **fit-driven** labels |
| **`model-routing.yaml` materializer** | Optional `hardware_tier_overrides` slice merged at materialize time |
| **`RunOrchestrator.create_run`** | Snapshot `hardware_profile_id` + `resource_governor` on `run.created` metadata |
| **`parallel_writers`** | Accept `ResourceGovernor`; use semaphore / chunk stage list before `asyncio.gather` |
| **Micro-slice executor** | When `pressure == throttle`, serialize slice LLM calls; when `block`, surface Maker message |
| **FAISS / memory index** | `rebuild_memory_index` checks RAM; defer or lower `retrieval_k` under pressure |
| **Redis fleet worker** (fo205) | Worker concurrency = `min(queue_workers, governor.max_concurrent_llm_calls)` |
| **Maker Console** | Settings page: sliders + “Auto hardware” toggle; readiness strip shows tier + warnings |
| **Admin Console** | Hardware panel: rescan, SSH remote probe (Enterprise), governor defaults per tenant, fleet SLI overlay |
| **API** | `GET /v1/platform/hardware`, `PUT /v1/platform/resource-governor` (admin), `GET` includes effective limits for UI |

#### 20.8.5 Parallel agents policy (normative)

**Parallel only when safe:**

- Writers (frontend/backend) may run in parallel **iff** `resource_governor.max_parallel_writer_stages >= 2` **and** `pressure == ok`.
- Critics for a **single** producer output stay **sequential** by default (existing unanimous gate story); optional `parallel_critics: true` only when tier = `strong` and operator enables.
- **Never** parallelize stages that share one Ollama model context over VRAM cap—governor forces serialization.
- Emit `resource.governor.applied` on run start with effective limits JSON for audit.

#### 20.8.6 Events and config

| Event / config | Purpose |
|--------------|---------|
| `hardware.profile.detected` | New/changed profile snapshot |
| `resource.governor.applied` | Effective limits at `run.created` |
| `resource.pressure.warn` | Mid-run throttle (optional, rate-limited) |
| Postgres `hermes_config_document` namespace `resource_governor` | Operator defaults (T2, ?19.5) |
| Workflow YAML `resource:` block | Per-profile overrides (`micro_slice` stricter than dev) |

```yaml
resource:
  auto_adjust: true
  max_system_ram_pct: 75
  max_vram_pct: 85
  reserve_ram_gb: 2.0
  max_parallel_writer_stages: null   # null = derive from hardware tier
  allow_parallel_critics: false
```

#### 20.8.7 Epic map (fo530–fo549)

| Epic | Outcome |
|------|---------|
| **fo530** | `packages/nimbusware_hw/` — port `hardware.py` probe (local Windows + Linux); MIT attribution |
| **fo531** | `HardwareProfile` schema + `GET /v1/platform/hardware` + `hardware.profile.detected` |
| **fo532** | Fit ranking adapter (`fit.py` port or llmfit wrapper) tied to `model-routing` allowlist |
| **fo533** | `ResourceGovernor` + `policy_snapshot.resource_governor` freeze on `run.created` |
| **fo534** | Preflight + readiness integration (replace static presets with tier-based recommendations) |
| **fo535** | `parallel_writers` + orchestrator LLM semaphore respect governor |
| **fo536** | Maker settings UI: RAM/VRAM % sliders, auto-adjust toggle, plain-language tier |
| **fo537** | Admin hardware panel: rescan, effective limits, pressure history |
| **fo538** | Mid-run `pressure.py` sampling + throttle/stub degrade path |
| **fo539** | Memory index rebuild respects RAM cap (defer job when over budget) |
| **fo540** | Enterprise: remote SSH hardware probe + fleet aggregate tier dashboard (extends fo206) |
| **fo541** | Tests: fixture profiles (weak/medium/strong) without GPU in CI |
| **fo542** | Docs: contrast with Odysseus Cookbook; document optional llmfit dependency |
| **fo543** | **Model Manager** API: `GET /v1/platform/models/ranked?use_case=coding&gpu_only=false` |
| **fo544** | Maker Model Manager panel: hardware strip, rescan, fit badges, expand row |
| **fo545** | GPU tier toggles + `gpu_only` ranking mode (mirror Odysseus multi-GPU UX) |
| **fo546** | Ollama preset mapper (Quality/Balanced/Speed → `num_ctx` / model tag suggestions) |
| **fo547** | “Apply to routing” wizard: write materialized `model-routing` override from chosen preset |
| **fo548** | Dependencies/readiness strip (ollama, GPU passthrough warning for Docker) |
| **fo549** | Optional `model_catalog.json` sync from hf_models subset (offline-first default) |

#### 20.8.10 Nimbusware Model Manager (product specification)

**Name:** **Model Manager** (Maker sidebar; Admin has extended view). Parallels Odysseus Cookbook
**hardware + fit** surfaces only—not chat, not serve orchestration.

**Entry points:** Maker `rail-model-manager` equivalent; readiness banner “Open Model Manager” when
no model fits; Admin **Hardware** tab links here for fit tables.

**Screen A — Hardware (maps Odysseus `_hwfitRenderHw`)**

| UI element | Data source | Behavior |
|------------|-------------|----------|
| Tier badge | `HardwareProfile.tier` | `weak` / `medium` / `strong` with color + one-line explanation |
| RAM bar | `ram_total_gb`, `ram_available_gb` | % used; governor cap line at `max_system_ram_pct` |
| GPU list | `gpus[]` + `gpu_groups[]` | Name, VRAM, backend (cuda \| rocm \| metal); homogeneous badge |
| Unified memory | `unified_memory` | Single pool label (Apple); hide misleading “VRAM” split |
| Multi-GPU toggles | `gpu_groups` | Select pool for ranking (default: largest homogeneous pool) |
| Rescan | `POST /v1/platform/hardware/rescan` | `fresh=True`; spinner; emit `hardware.profile.detected` |
| Remote (Enterprise) | SSH probe | Host picker; same panel layout; `fo540` |
| Warnings | probe `errors[]` | NVML mismatch, Docker no GPU, iGPU-only |

**Screen B — Model list (maps `_hwfitRenderList` / `rank_models`)**

| UI element | Behavior |
|------------|----------|
| Filter: use case | Default **`coding`**; also `chat`, `reasoning`, `general` (admin) |
| Filter: GPU only | When on, rankings match Odysseus `gpu_only` (no CPU-spill “fits”) |
| Sort | score (default), speed, vram, context, params |
| Columns | Model name, fit badge, run mode, est GB, speed (tps est), context cap |
| Fit badges | `perfect` green, `good` blue, `marginal` amber, `too_tight` gray (still visible) |
| Expand row | `required_gb`, `run_mode`, sub-scores, recommended Ollama tag, preset trio |
| Allowlist | Only models present in `model-routing.yaml` **or** installed Ollama tags |

**Fit badge → operator copy (normative):**

| `fit_level` | Maker copy |
|-------------|------------|
| `perfect` | “Runs fully on GPU with headroom” |
| `good` | “Comfortable fit for this machine” |
| `marginal` | “May work; expect slower runs or tight memory” |
| `too_tight` | “Not recommended — upgrade RAM/VRAM or pick smaller model” |

**Screen C — Presets (maps `compute_serve_profiles`, Ollama translation)**

For each selected model, show three cards **Quality / Balanced / Speed**:

| Preset | Ollama mapping (normative) |
|--------|---------------------------|
| Quality | Largest quant tag that `fit_level` ≥ `good` on GPU; `num_ctx` = min(model max, profile cap) |
| Balanced | Default routing tag (e.g. `q4_K_M` class); `num_ctx` = workflow default |
| Speed | Smallest quant with `fit_level` ≥ `marginal` on GPU; `num_ctx` reduced until `required_gb` fits |

Each card: estimated GB, fits yes/no, **Copy `ollama pull`**, **Apply to run profile** (writes
config doc + suggests materialize). No auto-pull without confirm (?20.8.8).

**Screen D — Governor link (Nimbusware-specific, no Odysseus equivalent)**

Sidebar on Model Manager: live **resource governor** sliders (§20.8.3) with preview of
`max_parallel_writer_stages` and `max_concurrent_llm_calls` when preset changes.

**Screen E — Dependencies (narrow Model Manager deps)**

| Check | Pass criteria |
|-------|---------------|
| Ollama reachable | `GET /api/tags` or CLI |
| Model installed | Selected tag in `ollama list` |
| GPU visible to Ollama | Non-zero VRAM in probe when discrete GPU expected |
| Docker (optional) | Warning if compose API container has no GPU device |

No “install pip package” buttons in Individual; Enterprise may link to runbook.

**API contract (additive to §20.8.4):**

```yaml
GET /v1/platform/hardware:
  # HardwareProfile + last_detected_at + cache_ttl

POST /v1/platform/hardware/rescan:
  # fresh probe

GET /v1/platform/models/ranked:
  query: { use_case: coding, gpu_only: false, gpu_group_index: 0, limit: 50 }
  # { models: [{ id, fit_level, run_mode, score, scores, ollama_tag, presets }] }

POST /v1/platform/models/apply-preset:
  body: { model_id, preset: quality|balanced|speed, target: model-routing|run_defaults }
  # writes hermes_config_document; returns materialize hint
```

**Coding pipeline alignment:**

1. Preflight calls `rank_models_for_profile(..., use_case=coding)` before static fallback chain.
2. Materialized routing stores `hardware_tier` + `model_manager_preset_applied` in metadata for audit.
3. Run theater **System** actor posts: “Model Manager: using Balanced preset on RTX 4060 (8 GB)”.

**Catalog maintenance:**

- **Default:** static subset in `configs/hardware/model_catalog.json` shipped with Nimbusware.
- **Optional fo549:** import script from Odysseus `hf_models.json` fields (params, MoE, ctx)—MIT
  attribution; never required for offline Individual installs.

#### 20.8.8 Non-goals

- Bundled **model downloader** or vLLM/llama.cpp **serve manager** (Odysseus Cookbook scope).
- Auto-pull Ollama models without operator confirm on first install (Maker may **suggest** pull).
- Ignoring `policy_snapshot` mid-run to “learn” hardware—profile may refresh, but **run limits are frozen**.

#### 20.8.9 Success metrics

| Metric | Target |
|--------|--------|
| OOM / OS swap storms during multi-writer runs | ↓ after fo535 |
| Runs started on `weak` tier with auto stub degrade | 0 surprise LLM failures |
| Operator override rate of auto tier | Measurable; tune defaults |
| Time-to-ready on fresh install | Readiness shows tier + model suggestion &lt; 60s after probe |

### 20.9 Run theater (“group chat”) — roles thinking out loud

**Goal:** During a run, the user sees a **single threaded conversation** where Planner, writers,
critics, verifiers, and gates **explain what they are doing and why**—especially **why work was
sent back** for another round (FAIL verdict, blocker finding, slice gate blocked, escalation).
This is **observability narrative**, not a second control-plane chat (distinct from **fo150
operator chat**, which is user → Hermes steering).

**Product names (normative):**

| UI label | Meaning |
|----------|---------|
| **Run theater** | Internal/feature name; projection over the event store |
| **Group chat** (Maker) | User-facing label: “Team discussion for this run” |

**North star:** *Follow the run like overhearing a disciplined engineering stand-up—not reading raw JSON or CSV exports.*

#### 20.9.1 What appears in the thread (message kinds)

Each message is a **projection** from append-only events (or stage metadata)—**not** a new
source of truth. Default: **structured rationale** only; optional `verbose_rationale: true` in
workflow may include longer excerpts (operator-configured, capped).

| Actor (display) | Typical triggers | User-visible content |
|-----------------|------------------|----------------------|
| **Planner** | `stage.started` plan | “Proposed N slices because …”; acceptance criteria summary |
| **Frontend / Backend Writer** | writer stage complete | “Touched paths …”; one-line intent |
| **Domain / Security / Perf / … Critic** | `critic.verdict.emitted` | Verdict + **in-domain** reason; “Blocking because …” with evidence refs as links |
| **Verifier** | test/lint fail | “Tests failed: …” (tail-capped log excerpt) |
| **Gate** | `gate.decision.emitted` | “Stage blocked — waiting on Security Critic FAIL” or “All critics PASS” |
| **Router** | `finding.routed` | “Routing finding #… to Backend Writer — category schema_mismatch” |
| **Escalation** | `run.escalated` / anti-deadlock | “Retry budget exhausted — human checkpoint” (?6.6, fo403) |
| **Slice gate** | `slice.gate` metadata | “Slice 2 blocked: tests did not pass”; link to replan |
| **Researcher / Stitcher** (§20.7) | `research.brief.emitted`, `stitch.applied` | “Found 3 OSS auth patterns”; “Transplanted 12 files from …” |
| **System** | preflight, governor | “Using fallback model …”; “Throttling parallel writers (low RAM)” (§20.8) |
| **Deferral** | writer/critic metadata | “Deferring to Security Critic — out of my scope_in” (§3E.5) |

**Theater copy rule (§3E):** messages use the **actor’s** `terminology_disambiguation` when quoting
ambiguous terms; if two roles conflict, show both meanings and which role owns the decision.

**“Why another round?” template (normative):** When a stage fails or loops, emit one **summary
message** aggregating: failing critic(s) → finding categories → `owner_role` (display name) →
required fix format (`json_patch` / `unified_diff`) → next stage name. Plain-language in Maker;
full structured payload in Admin “expand” panel.

#### 20.9.2 Relationship to existing surfaces

| Surface | Role |
|---------|------|
| **Event timeline** (?6.2, Admin) | Authoritative ordered events; theater is a **derived, readable view** |
| **fo150 operator chat** | User messages + high-level assistant replies; may **link** to theater thread |
| **fo303 plain-language progress** | One-line status card; theater is the **deep dive** behind the card |
| **fo471 progress streaming** | Push new theater messages over SSE/WebSocket |
| **Critic matrix** (Console) | Tabular PASS/FAIL; theater explains **why** each cell is red |

**Simple mode (Maker):** show theater as default main panel during an active run; hide critic
matrix CSV exports. **Advanced:** split view timeline + theater + matrix.

#### 20.9.3 Architecture (projection, not parallel chat LLM)

```text
event_store (append-only)
        │
        ▼
nimbusware_projections.run_theater  ──► RunTheaterMessage[] (read model)
        │
        ├──► GET /v1/runs/{id}/theater?cursor=
        ├──► SSE /v1/runs/{id}/theater/stream  (fo471)
        └──► Maker UI “Group chat” + Admin “Run theater”
```

**Do not** run a separate multi-agent LLM “group chat” session—that would duplicate stages and
drift from gates. Theater messages are **deterministic templates** filled from validated event
payloads (`CriticVerdict`, `GateDecision`, `SliceContextPacket` summaries).

Optional **fo560**: LLM **one-sentence paraphrase** per stage for Maker only, with `theater.llm_summary: false` default (cost + hallucination risk).

#### 20.9.4 Integration hooks

| Hook | Connection |
|------|------------|
| **`agent_core` events** | Add optional `display_rationale: str` on payloads (max length); or derive from existing `message` / `reason_code` fields |
| **`nimbusware_projections`** | New builder `build_run_theater_messages(events, role_registry) → list[RunTheaterMessage]` |
| **`nimbusware_api`** | `GET /v1/runs/{run_id}/theater`; cursor pagination by `store_seq` |
| **`nimbusware_maker`** | `ui/run_theater.py` — group chat component; subscribes to stream during active run |
| **`nimbusware_console`** | Reuse or extend `operator_chat.py` sidebar: “Open full theater” |
| **`nimbusware_client`** | Typed client for theater endpoints (Maker `services/`) |
| **Workflow YAML** | `theater: { enabled, max_message_chars, show_evidence_links, llm_summary }` frozen in `metadata.theater` on `run.created` |
| **Research / Stitch / Memory** | Theater includes retrieval hits summary (“Recalled 2 prior gate failures”) when `memory.retrieval.emitted` |
| **IAM (Enterprise)** | Theater messages respect tenant scope; no cross-tenant leakage in fleet views |

#### 20.9.5 `RunTheaterMessage` contract (normative sketch)

```yaml
# Pydantic model (implementation)
run_id: uuid
store_seq: int          # anchor for ordering / SSE cursor
occurred_at: datetime
actor_display: str      # e.g. "Security Critic"
actor_role_id: uuid | null
message_kind: plan | critic_verdict | gate | finding_route | verifier | escalation | system | slice | research | stitch
severity: info | warn | block | pass
headline: str           # one line for Maker
body_md: str | null     # optional markdown; capped
refs:
  event_id: uuid
  finding_id: uuid | null
  stage_name: str | null
  slice_id: str | null
loop_round: int         # increment on stage retry / slice replan
```

#### 20.9.6 Epic map (fo550–fo565)

| Epic | Outcome |
|------|---------|
| **fo550** | `RunTheaterMessage` model + projection builder from event stream |
| **fo551** | `GET /v1/runs/{id}/theater` + pagination; OpenAPI tag `maker` |
| **fo552** | Maker **Group chat** panel (Simple mode default on active run) |
| **fo553** | “Why another round?” aggregator for gate FAIL + routed findings |
| **fo554** | Admin theater view: evidence expand, jump to timeline `store_seq` |
| **fo555** | SSE theater stream (merge with fo471 progress streaming) |
| **fo556** | Wire slice gate + micro-slice messages into theater |
| **fo557** | Researcher/Stitcher theater lines (§20.7) |
| **fo558** | Resource governor + preflight system lines (§20.8) |
| **fo559** | `theater` workflow block + `metadata.theater` on `run.created` |
| **fo560** | Optional LLM one-line paraphrase (off by default) |
| **fo561** | Tests: golden event fixture → stable theater message list hash |
| **fo562** | Export theater transcript (markdown) for audit bundle (fo402) |
| **fo563** | Theater + API: render `defer_to_role` and scope-creep warnings (§3E.5) |
| **fo564** | Agent Evaluator: detect overlapping `scope_in` across assigned personas |

#### 20.9.7 Non-goals

- Free-form **user ↔ multi-agent** chat replacing the pipeline (use fo150).
- Publishing **raw chain-of-thought** or full prompts in theater (security + noise).
- Theater messages that **contradict** gate outcomes—projection must reflect events only.
- Real-time theater for **completed** runs without replay from `event_store` (replay-only is fine).

#### 20.9.8 Success metrics

| Metric | Target |
|--------|--------|
| Maker users opening theater during active run | ↑ vs timeline-only |
| Support questions “why did it loop?” | ↓ after fo553 |
| Time to understand first gate FAIL | Self-reported / session analytics &lt; 30s |
| Theater / event timeline inconsistency bugs | 0 (fo561 golden tests) |

### 20.4 Prioritization matrix (recommended)

| Priority | Track | Epics | Rationale |
|----------|-------|-------|-----------|
| **P0** | Lane M substrate | fo300–fo308 (especially fo305, fo306, fo304) | Unblocks “business → code” story |
| **P1** | Research + Stitch (core) | fo510–fo515, fo520–fo523, fo528 | Domain/code discovery + transplant path; depends on scraper + fo305 snapshots |
| **P1** | Trust + integrator | fo400, fo403, fo410, fo413, fo423 | Strengthens unique governance story |
| **P1** | Dev friction | fo461, fo462, fo472 | Lowers adoption vs Aider |
| **P1** | Hardware + governor (core) | fo530–fo535, fo536, fo541 | Probe, fit, governor, parallel limits, Maker settings |
| **P2** | Hardware + governor (polish) | fo537–fo539, fo540, fo542 | Admin panel, mid-run pressure, fleet, docs |
| **P2** | Model Manager (Odysseus Cookbook parity UX) | fo543–fo549 | Ranked models, fit badges, GPU toggles, Ollama presets, apply-to-routing |
| **P2** | Research + Stitch (product) | fo516, fo524–fo526, fo529 | Maker approval UX, re-research, prompt hardening |
| **P2** | Research + Stitch (catalog) | fo525, fo527 | Bundle promotion + enterprise index |
| **P2** | Safety | fo480, fo481, fo412 | Matches OpenHands; reduces autonomous risk |
| **P2** | Ecosystem | fo460, fo470, fo471 | IDE + UX without rewriting orchestrator |
| **P2** | Run theater / group chat | fo550–fo556, fo559, fo561 | Follow-the-run UX; pairs with fo303 + fo471 |
| **P3** | Run theater (polish) | fo557, fo558, fo560, fo562, fo554 | Research/stitch/governor lines, Admin expand, export |
| **P3** | Enterprise polish | fo500, fo501, fo440–fo442 | Buyer checklist |
| **P3** | Marketing / quality | fo452, fo450, fo451 | Benchmark + maintainability |

### 20.5 Non-goals (coding growth lane)

Do **not** prioritize these in Nimbusware core (optional integrations only):

- General-purpose **chat workspace** (email, calendar, deep research UI) — use external tools; optional webhook only.
- ~~**Replacing Streamlit Admin Console** entirely~~ — **done** (Preact Admin at `/v1/admin/app/`); Streamlit **retired**.
- **Cloud-only model routing** as default — local-first remains Individual default.
- **Unbounded agent autonomy** without gates — conflicts with ?4.3 and product contract.

### 20.6 Success metrics (coding competitiveness)

Extend **§16** with coding-specific targets:

| Metric | Target direction |
|--------|------------------|
| First-pass **slice gate** pass rate | Increase release-over-release on fixed benchmark repo |
| Mean **slices per run** to completion | Stable or decreasing (less replan churn) |
| Time from **intent → first applied slice** | Decrease (Maker + fo461 quick mode) |
| **Repeat finding** rate (same category/path) | Decrease with Phase 4 memory (fo160–fo164) |
| **Setup time** (fresh install → green preflight) | &lt; 30 min documented path |
| **SWE-bench subset** pass rate | Publish when fo452 exists (optional) |
| **Transplant success rate** (stitch → refactor → gate PASS) | Track when fo520–fo522 ship (§20.7.9) |
| **Research brief utilization** | Planner stages citing `research.brief.emitted` (§20.7.9) |
| **OOM / swap during parallel writers** | ↓ with resource governor (§20.8.9) |
| **Auto tier match** (readiness tier vs actual hardware) | Correct on reference machines (fo541) |
| **Model Manager → routing apply** | Operator selects preset and materializes without manual YAML edit (fo547) |
| **Preflight model fit** | No run starts with `too_tight` default when auto-adjust on (fo532–fo534) |
| **“Why did it loop?”** support burden | ↓ when theater + fo553 ship (§20.9.8) |
| **Maker theater engagement** | Active-run users open group chat (§20.9.8) |

**Review cadence:** Revisit §20 priorities each sprint in [plan_gap.md](plan_gap.md); demote items
that duplicate shipped work or fail cost/benefit on Individual edition.

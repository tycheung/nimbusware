# Product overview

Nimbusware is a **local-first** platform for adversarial agentic software workflows: a FastAPI control plane, **Maker** and **Admin** web apps, and an event-sourced agent runtime with unanimous gates, verifiers, and optional Ollama-backed LLM stages.

Capability transport (LLM chat, sandbox, memory, …) is offloaded to **SwissArmyNoife** during peel — see Agentic [`docs/mcp-split.md`](../../../docs/mcp-split.md) and [`docs/dual-run-flags.md`](../../../docs/dual-run-flags.md).

## Individuals

Build and fix software on your machine with an agent that must pass tests and security gates, not just generate code.

- Greenfield **Build an app** flows run scope discovery in Maker Chat (with **Explain** hints), freeze a stack manifest from `configs/stacks/`, then deliver via `campaign_fullstack` (API + web surfaces, contract gate, launch test).
- Scope confirmation can auto-scaffold stack-catalog agents; the manifest preview shows per-surface model bindings before approval.
- Manifests with a **`deploy`** surface bind `infra_writer` for Terraform/CI slices; Progress includes a deploy cockpit; Chat supports `@discipline` mentions, solo hat chips, and surface steers.
- **Safe Coding** archetype adds extra approval gates and industry critics. **Engineer workspace** enables collaborative discipline rosters and agent overlays.
- Optional **VS Code / Cursor extension** (`extensions/nimbusware-status`) mirrors scope approval and deploy deep links alongside Maker MCP ([ide-bridge.md](../ide-bridge.md)).
- Tune **autonomy** and **enforcement depth** independently. Campaign workflows decompose a `business_prompt` into verified micro-slices.

**Manager PWA** (`?manager=1`) provides read-only Progress/Review plus Scope approval on phone. **Mobile native** is deferred — [mobile.md](mobile.md).

## Enterprise

Self-hosted control plane for governed agentic development:

- Audit every run (exports include scope and surface outcomes).
- Fleet compliance dashboard (gate pass rates, learnings search, archetype fit).
- Tenant audit policy with legal-hold; collab guest policy and regulated stack allowlist in Admin Fleet.
- Fleet governance summary in Maker Home; deploy credential scope audit; steer autonomy without a SaaS black box.

Buyer-oriented detail: [enterprise-buyer.md](../enterprise-buyer.md). Editions: [editions.md](editions.md).

## Personas

| Persona | First-run choice | Start here |
|---------|------------------|------------|
| **Safe Coding** | Safe Coding in Maker archetype picker | [safe-coding.md](safe-coding.md) · [journeys/safe-coding-first-app.md](journeys/safe-coding-first-app.md) |
| **Engineer workspace** | Engineer workspace (persists collab) | [maker.md](maker.md) · [collaborative-chat.md](../collaborative-chat.md) · [journeys/engineer-first-app.md](journeys/engineer-first-app.md) |
| **Enterprise AI** | Enterprise install bundle | [enterprise-buyer.md](../enterprise-buyer.md) · [journeys/enterprise-first-app.md](journeys/enterprise-first-app.md) |

Install bundles: [install-profiles.md](../install-profiles.md). Journeys index: [journeys/README.md](journeys/README.md).

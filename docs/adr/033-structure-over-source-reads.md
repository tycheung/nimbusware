# ADR 033: Structure-over-source agent reads

## Status

Accepted (2026-07)

## Context

The agent `read` tool defaults to full file source. Large files (especially out-of-slice
dependencies) dominate JIT context with low signal. Operators still need structure for
navigation and signatures before paying for full source on files actively being edited.

## Decision

`agent_core/read_outline.py` selects a read mode per file:

| Mode | When | Output |
|------|------|--------|
| **full** | Slice target files or small files | Raw source (capped by `NIMBUSWARE_READ_MAX_CHARS`) |
| **outline** | Python files above outline LOC threshold | AST class/function signatures |
| **digest** | Python files above digest threshold | Truncated outline (signatures only, ~80 lines) |

Thresholds are env-tunable; slice-target paths always receive `full` so implement stages
see complete source for files they may modify. `agent_core/read_staleness.py` tracks when
a digest/outline read should be refreshed after upstream edits.

Non-Python structure extraction uses regex signatures for `.ts`/`.tsx`/`.js`/`.jsx`/`.go` today. Optional tree-sitter parsers remain a future enhancement for richer outlines.

Related agent-side token tactics (no separate ADR): index-first memory injection
(`NIMBUSWARE_MEMORY_INDEX_FIRST`), lazy tool/MCP schema loading, and loop-history dedup
(`NIMBUSWARE_CONTEXT_DEDUP`) — documented in [context-efficiency.md](../reference/context-efficiency.md).

## Consequences

- Agents may need a second `read` call (or slice-target promotion) to see full implementation.
- Outline/digest output is lossy by design; verifiers and writers on target files bypass it.
- Staleness tracker prevents silent reuse of outdated structure summaries mid-campaign.

## Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Always full source | Token waste on large dependency files |
| RAG-only (never full read) | Implement stages need exact source for edits |
| Single global char cap only | No structure signal before truncation |

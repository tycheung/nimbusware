# agent_core

Shared event models and cross-package read helpers for Nimbusware.

## Modules

| Path | Role |
|------|------|
| `models/` | Pydantic event envelopes and payloads |
| `context_budget.py` | Shell output truncation for LLM history |
| `stage_graph.py` | Stage DAG parse, validate, timeline metadata |
| `slice_plan.py` | `SlicePlan` / `parse_slice_plan` |
| `prompt_tiers.py` | `assemble_prompt`, `stable_slice_agent_block` |
| `critique_stages.py` | Critique stage name constants + producer map |
| `timeline_metadata.py` | `run.created` metadata helpers |
| `read/campaign.py` | Campaign backlog row parsers |
| `read/critic_matrix.py` | Live critic matrix rows from gate events |
| `yaml_io.py` | YAML load/dump helpers |

`nimbusware_orchestrator` re-exports `stage_graph`, `prompt_tiers`, and `critic_matrix_live` for backward compatibility.

## Wire format

- Role identifiers on events are UUIDs (JSON strings on the wire).
- Event envelope is discriminated on `event_type`; use `validate_event_dict`.
- YAML helpers: `agent_core.yaml_io`.

Ships PEP 561 marker (`py.typed`).

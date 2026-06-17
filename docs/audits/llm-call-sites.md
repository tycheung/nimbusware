# LLM call-site audit (v1.2 fo1401)

Matrix of direct Ollama / cloud dispatch vs resolver target. **Exit criteria (A2):** all rows route through `ModelBindingResolver`.

| Module | Entry | Current dispatch | Resolver agent_role (target) |
|--------|-------|------------------|------------------------------|
| `llm_slice.py` | slice plan/implement/critique | `ollama_chat_json` direct | stage-mapped roles |
| `llm/common.py` | `ollama_chat_json_via_plan_patch` | hybrid `cloud_chat_json` or ollama | per caller role |
| `llm/plan_stage.py` | plan JSON | via common | `planner` |
| `llm/*_critique.py` | critic JSON | via common | critic role per stage |
| `llm/backlog_generator.py` | backlog | `ollama_chat_json` direct | `backlog_generator` |
| `llm/agent_evaluator.py` | eval | via common | `agent_evaluator` |
| `intent_classifier.py` | classify | Ollama base URL | `intent_classifier` |
| `agent_loop.py` | JIT loop | runtime ollama URL | custom / bound role |
| `launch_evaluator.py` | launch eval | ollama | `launch_evaluator` |
| `launch_test_llm.py` | launch test writer | ollama | `launch_test_writer` |
| `test_writer_stage.py` | test writer | ollama | `test_writer` |
| `refactor_stage.py` | refactor | ollama | `refactor` |
| `*_critique.py` (orchestrator root) | stage critics | ollama / common | per critic pack role |
| `hybrid_routing.py` | `cloud_chat_json` | stage_providers | absorbed into providers layer |

## Notes

- `llm_plan.py` / `ollama_chat.py` remain low-level adapters wrapped by **OllamaProvider** (A1).
- Stage name mismatch (`slice.critique` vs `implementation.critique`) fixed during fo1471 preset migration.

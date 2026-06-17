# LLM call-site audit (v1.2 fo1401)

Matrix of dispatch vs resolver target. **Exit criteria (A2):** orchestrator and maker entry points route through `ModelBindingResolver` (directly or via `ollama_chat_json_via_plan_patch`).

| Module | Entry | Dispatch | Resolver agent_role |
|--------|-------|----------|---------------------|
| `llm_slice.py` | slice plan/implement/critique | `via_plan_patch` + stage | `slice.plan` → planner, etc. |
| `llm/common.py` | `ollama_chat_json_via_plan_patch` | stage → role → resolver | per caller stage/role |
| `llm/plan_stage.py` | plan JSON | via common + `plan` stage | `planner` |
| `llm/*_critique.py` | critic JSON | via common + stage | stage-mapped critic role |
| `llm/backlog_generator.py` | backlog | via_plan_patch | `planner` |
| `llm/agent_evaluator.py` | eval | via common + stage | `planner` |
| `intent_classifier.py` | classify | via_plan_patch | `planner` |
| `agent_loop.py` | JIT loop | via_plan_patch default | `backend_writer` |
| `runtime.py` | step planner | via_plan_patch | `backend_writer` |
| `launch_evaluator.py` | launch eval | via_plan_patch | `planner` |
| `launch_test_llm.py` | launch test writer | via_plan_patch | `test_writer` |
| `test_writer_stage.py` | test writer | via_plan_patch | `test_writer` |
| `refactor_stage.py` | refactor | via_plan_patch | `backend_writer` |
| `*_critique.py` (orchestrator root) | stage critics | via_plan_patch | `security_critic` |
| `hybrid_routing.py` | `cloud_chat_json` | legacy shim when no role map | absorbed into providers layer |
| `ollama_chat.py` | low-level HTTP | adapter only | wrapped by **OllamaProvider** (A1) |

## Notes

- `ollama_chat_json` remains the Ollama HTTP adapter; production call sites use `ModelBindingResolver` except hybrid fallback for unmapped stages.
- Stage → role mapping lives in `binding_preflight.agent_role_for_stage` (`plan`, `slice.*`, `*.critique`).
- Preset `slice.critique` vs critique stage names (`implementation.critique`, etc.) resolved via expanded stage map (fo1471).

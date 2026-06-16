from __future__ import annotations

CRITIQUE_STAGE_TO_PRODUCER: dict[str, str] = {
    "planner.critique": "planner",
    "implementation.critique": "backend_writer",
    "test_writer.critique": "test_writer",
    "frontend_writer.critique": "frontend_writer",
    "module_integrator.critique": "module_integrator",
    "agent_evaluator.critique": "agent_evaluator",
    "self_refinement.critique": "planner",
}

IMPLEMENTATION_CRITIQUE_STAGE = "implementation.critique"
TEST_WRITER_CRITIQUE_STAGE = "test_writer.critique"
PLANNER_CRITIQUE_STAGE = "planner.critique"
FRONTEND_WRITER_CRITIQUE_STAGE = "frontend_writer.critique"
MODULE_INTEGRATOR_CRITIQUE_STAGE = "module_integrator.critique"

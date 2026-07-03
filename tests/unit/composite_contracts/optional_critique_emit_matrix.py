from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import yaml

from agent_core.models import (
    EventType,
    ModelSelectedPrimaryEvent,
    ModelSelectedPrimaryPayload,
)
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.workflow.universal_critique import EffectiveUniversalCritique


def make_effective_universal_critique(**overrides: bool) -> EffectiveUniversalCritique:
    defaults: dict[str, bool] = {
        "impl_llm": False,
        "impl_stub": False,
        "impl_stage_failed_on_gate_fail": False,
        "impl_emit_finding_on_gate_fail": False,
        "impl_hard_block_on_gate_fail": False,
        "tw_enabled": False,
        "tw_llm": False,
        "tw_stub": False,
        "tw_stage_failed_on_gate_fail": False,
        "tw_emit_finding_on_gate_fail": False,
        "tw_hard_block_on_gate_fail": False,
        "pll_enabled": False,
        "pll_llm": False,
        "pll_stub": False,
        "pll_stage_failed_on_gate_fail": False,
        "pll_emit_finding_on_gate_fail": False,
        "pll_hard_block_on_gate_fail": False,
        "fw_enabled": False,
        "fw_llm": False,
        "fw_stub": False,
        "fw_stage_failed_on_gate_fail": False,
        "fw_emit_finding_on_gate_fail": False,
        "fw_hard_block_on_gate_fail": False,
        "mi_enabled": False,
        "mi_llm": False,
        "mi_stub": False,
        "mi_stage_failed_on_gate_fail": False,
        "mi_emit_finding_on_gate_fail": False,
        "mi_hard_block_on_gate_fail": False,
    }
    defaults.update(overrides)
    return EffectiveUniversalCritique(**defaults)


def append_model_selected_primary(mem: Any, rid: Any, model_id: str = "llama3.1:8b") -> None:
    mem.append(
        ModelSelectedPrimaryEvent(
            event_type=EventType.MODEL_SELECTED_PRIMARY,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelSelectedPrimaryPayload(
                provider="ollama",
                model_id=model_id,
            ),
        ),
    )


@dataclass(frozen=True)
class OptionalCritiqueEmitterSpec:
    prefix: str
    enabled_key: str
    llm_key: str
    stub_key: str
    llm_patch: str
    stub_patch: str
    emit_method: str


TEST_WRITER_SPEC = OptionalCritiqueEmitterSpec(
    prefix="tw",
    enabled_key="tw_enabled",
    llm_key="tw_llm",
    stub_key="tw_stub",
    llm_patch=(
        "orchestrator._pipeline.critique_gates_optional_emit.execute_test_writer_critique_llm"
    ),
    stub_patch=(
        "orchestrator._pipeline.critique_gates_optional_emit.emit_stub_test_writer_critique_panel"
    ),
    emit_method="_emit_test_writer_critique_optional",
)

PLANNER_SPEC = OptionalCritiqueEmitterSpec(
    prefix="pll",
    enabled_key="pll_enabled",
    llm_key="pll_llm",
    stub_key="pll_stub",
    llm_patch=("orchestrator._pipeline.critique_gates_optional_emit.execute_planner_critique_llm"),
    stub_patch=(
        "orchestrator._pipeline.critique_gates_optional_emit.emit_stub_planner_critique_panel"
    ),
    emit_method="_emit_planner_critique_optional",
)

OPTIONAL_CRITIQUE_EMITTER_SPECS: tuple[OptionalCritiqueEmitterSpec, ...] = (
    TEST_WRITER_SPEC,
    PLANNER_SPEC,
)

MATRIX_6_AXIS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "disabled",
        "enabled": False,
        "llm": True,
        "stub": True,
        "with_model": True,
        "llm_returns": True,
        "expected_llm": 0,
        "expected_stub": 0,
    },
    {
        "case_id": "no_llm_no_stub",
        "enabled": True,
        "llm": False,
        "stub": False,
        "with_model": False,
        "llm_returns": True,
        "expected_llm": 0,
        "expected_stub": 0,
    },
    {
        "case_id": "stub_only",
        "enabled": True,
        "llm": False,
        "stub": True,
        "with_model": False,
        "llm_returns": True,
        "expected_llm": 0,
        "expected_stub": 1,
    },
    {
        "case_id": "no_model_stub_fallback",
        "enabled": True,
        "llm": True,
        "stub": True,
        "with_model": False,
        "llm_returns": True,
        "expected_llm": 0,
        "expected_stub": 1,
    },
    {
        "case_id": "llm_success",
        "enabled": True,
        "llm": True,
        "stub": True,
        "with_model": True,
        "llm_returns": True,
        "expected_llm": 1,
        "expected_stub": 0,
    },
    {
        "case_id": "llm_fail_stub_fallback",
        "enabled": True,
        "llm": True,
        "stub": True,
        "with_model": True,
        "llm_returns": False,
        "expected_llm": 1,
        "expected_stub": 1,
    },
)


def run_optional_critique_matrix_case(
    spec: OptionalCritiqueEmitterSpec,
    case: dict[str, Any],
) -> tuple[int, int]:
    with (
        patch(spec.llm_patch) as m_llm,
        patch(spec.stub_patch) as m_stub,
    ):
        m_llm.return_value = case["llm_returns"]
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        if case["with_model"]:
            append_model_selected_primary(mem, rid)
        eff = make_effective_universal_critique(
            **{
                spec.enabled_key: case["enabled"],
                spec.llm_key: case["llm"],
                spec.stub_key: case["stub"],
            },
        )
        emit: Callable[..., None] = getattr(orch, spec.emit_method)
        emit(
            rid,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff,
        )
        return m_llm.call_count, m_stub.call_count


def make_propagation_eff(spec: OptionalCritiqueEmitterSpec) -> EffectiveUniversalCritique:
    return make_effective_universal_critique(
        **{spec.enabled_key: True, spec.llm_key: True, spec.stub_key: False},
    )


_PROPAGATION_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "composite_contracts"
    / "optional_critique_propagation_cases.yaml"
)
PROPAGATION_CASES: tuple[dict[str, Any], ...] = tuple(
    yaml.safe_load(_PROPAGATION_FIXTURE.read_text(encoding="utf-8"))["cases"]
)


def run_optional_critique_propagation_case(
    spec: OptionalCritiqueEmitterSpec,
    case: dict[str, Any],
) -> tuple[dict[str, Any], Any]:
    eff = make_propagation_eff(spec)
    with (
        patch(spec.llm_patch) as m_llm,
        patch(spec.stub_patch),
    ):
        m_llm.return_value = True
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        append_model_selected_primary(mem, rid, model_id=case["model_id"])
        emit = getattr(orch, spec.emit_method)
        if case["base_cfg"] is None:
            emit(
                rid,
                verifier_exit_code=case["verifier_exit_code"],
                log_snippet=case["log_snippet"],
                eff=eff,
            )
        else:
            with patch.object(orch, "_base_cfg", return_value=case["base_cfg"]):
                emit(
                    rid,
                    verifier_exit_code=case["verifier_exit_code"],
                    log_snippet=case["log_snippet"],
                    eff=eff,
                )
        return m_llm.call_args.kwargs, rid

"""Implementation-critique LLM seam direct contract (fo94).

fo93's Next-slice item (6) flagged this gap. The impl variant's LLM call
site lives **inline** in ``execute_writer_verifier_pass`` at
[`pipeline.py:1183-1211`](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
(NOT in a standalone method like tw/pll's ``_emit_*_critique_optional``).

Asymmetry vs fo91: there is **NO ``impl_enabled`` master switch** in
``EffectiveUniversalCritique`` -- impl is gated only by ``impl_llm`` /
``impl_stub`` flags + ``_selected_model_for_run`` returning non-None. So
the path matrix here is **5 axes** instead of fo91's 6.

Unique to impl: ``log_snippet = "\\n".join(log.splitlines()[:60])``
truncation happens at this seam. tw/pll receive the already-truncated
snippet from their caller, so this 60-line truncation contract is only
observable here.

Coverage today: ``tests/test_critique_router_pipeline.py:119-147`` patches
``execute_implementation_critique_llm`` with ``return_value=True/False``
and asserts event-level outcomes; zero assertions on ``call_args.kwargs``.

fo94 closes the gap via 4 parts spanning 17 axes (~29 assertions, source
unchanged):

* **Part A** -- control-flow path matrix (5 axes -- all-off / stub-only /
  no-model / LLM-emitted / LLM-failed+stub-fallback).
* **Part B** -- argument propagation mirroring fo91 Part C (5 axes --
  ``base_url`` default/override + ``timeout_seconds`` default/float-cast +
  ``run_id``/``model_id`` verbatim pass-through).
* **Part C** -- ``log_snippet`` 60-line truncation contract (4 axes --
  empty / single-line / exactly-60 / 100-line truncated).
* **Part D** -- ``verifier_exit_code`` propagation from
  ``run_writer_verifier_bundle``'s return tuple (3 axes -- 0 / 1 / 42).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_universal_critique import EffectiveUniversalCritique


def _make_eff(**overrides: bool) -> EffectiveUniversalCritique:
    """Reused from fo90/fo91/fo92/fo93: all 17 flags default False."""
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


_WS = Path(".")


def test_implementation_critique_llm_seam_path_matrix_5_axis() -> None:
    """Pin the 5 control-flow paths at pipeline.py:1187-1211 for impl seam.

    NOTE: there is no ``tw_enabled=False``-equivalent master-switch axis
    since impl variant lacks that flag -- this asymmetry is itself a
    contract pinned by A1 (all-off -> LLM 0, stub 0, no third path).

    A1 -- impl_llm=False + impl_stub=False -> LLM 0, stub 0 (no master
    switch).
    A2 -- impl_llm=False + impl_stub=True -> stub-only path.
    A3 -- impl_llm=True + no model + impl_stub=True -> LLM NOT invoked,
    stub fallback runs (pins the ``if model:`` guard).
    A4 -- impl_llm=True + model + LLM returns True + impl_stub=True ->
    LLM only (stub NOT invoked per ``if not emitted_impl_llm``).
    A5 -- impl_llm=True + model + LLM returns False + impl_stub=True ->
    LLM + stub fallback (AND-gated fallback).
    """
    with (
        patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ),
        patch("hermes_orchestrator.pipeline.execute_implementation_critique_llm") as m_llm,
        patch(
            "hermes_orchestrator.pipeline.emit_stub_implementation_critique_panel",
        ) as m_stub,
    ):
        m_llm.return_value = True

        orch_a1, _ = make_dev_orchestrator()
        rid_a1 = orch_a1.create_run("default")
        eff_a1 = _make_eff(impl_llm=False, impl_stub=False)
        with patch.object(orch_a1, "_effective_universal_critique_for_run", return_value=eff_a1):
            orch_a1.execute_writer_verifier_pass(rid_a1, workspace=_WS)
        assert m_llm.call_count == 0 and m_stub.call_count == 0, (
            "A1: all-off (impl_llm=F + impl_stub=F) must short-circuit -- "
            "no impl_enabled master switch exists"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = True

        orch_a2, _ = make_dev_orchestrator()
        rid_a2 = orch_a2.create_run("default")
        eff_a2 = _make_eff(impl_llm=False, impl_stub=True)
        with patch.object(orch_a2, "_effective_universal_critique_for_run", return_value=eff_a2):
            orch_a2.execute_writer_verifier_pass(rid_a2, workspace=_WS)
        assert m_llm.call_count == 0 and m_stub.call_count == 1, (
            "A2: impl_llm=F + impl_stub=T -> stub-only path"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = True

        orch_a3, _ = make_dev_orchestrator()
        rid_a3 = orch_a3.create_run("default")
        eff_a3 = _make_eff(impl_llm=True, impl_stub=True)
        with (
            patch.object(orch_a3, "_effective_universal_critique_for_run", return_value=eff_a3),
            patch.object(orch_a3, "_selected_model_for_run", return_value=None),
        ):
            orch_a3.execute_writer_verifier_pass(rid_a3, workspace=_WS)
        assert m_llm.call_count == 0 and m_stub.call_count == 1, (
            "A3: impl_llm=T + no model -> LLM NOT invoked; stub fallback runs "
            "(emitted_impl_llm stays False, pinning the `if model:` guard)"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = True

        orch_a4, _ = make_dev_orchestrator()
        rid_a4 = orch_a4.create_run("default")
        eff_a4 = _make_eff(impl_llm=True, impl_stub=True)
        with (
            patch.object(orch_a4, "_effective_universal_critique_for_run", return_value=eff_a4),
            patch.object(orch_a4, "_selected_model_for_run", return_value="m"),
        ):
            orch_a4.execute_writer_verifier_pass(rid_a4, workspace=_WS)
        assert m_llm.call_count == 1 and m_stub.call_count == 0, (
            "A4: LLM returns True -> stub NOT invoked even with stub=True "
            "(pins the `if not emitted_impl_llm` guard)"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = False

        orch_a5, _ = make_dev_orchestrator()
        rid_a5 = orch_a5.create_run("default")
        eff_a5 = _make_eff(impl_llm=True, impl_stub=True)
        with (
            patch.object(orch_a5, "_effective_universal_critique_for_run", return_value=eff_a5),
            patch.object(orch_a5, "_selected_model_for_run", return_value="m"),
        ):
            orch_a5.execute_writer_verifier_pass(rid_a5, workspace=_WS)
        assert m_llm.call_count == 1 and m_stub.call_count == 1, (
            "A5: LLM returns False + impl_stub=True -> LLM + stub fallback "
            "(AND-gated fallback)"
        )


def test_implementation_critique_llm_seam_argument_propagation_5_axis() -> None:
    """Pin the LLM call's kwargs contract at pipeline.py:1194-1204 for impl.

    Mirrors fo91 Part C for impl variant. All axes use happy path
    (impl_llm=True + model + impl_stub=False); inspects m_llm.call_args.kwargs.

    B1 -- base_url default 'http://localhost:11434' when _base_cfg returns {}.
    B2 -- base_url override read from _base_cfg() runtime.base_url.
    B3 -- timeout_seconds default 120.0 + float-typed when _base_cfg returns {}.
    B4 -- timeout_seconds int->float cast via float() coercion of int input.
    B5 -- run_id + model_id 2-kwarg verbatim pass-through (verifier_exit_code
    and log_snippet are pinned by Parts D/C respectively).
    """
    eff = _make_eff(impl_llm=True, impl_stub=False)

    with (
        patch(
            "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
            return_value=(0, "ok"),
        ),
        patch("hermes_orchestrator.pipeline.execute_implementation_critique_llm") as m_llm,
        patch("hermes_orchestrator.pipeline.emit_stub_implementation_critique_panel"),
    ):
        m_llm.return_value = True

        orch_b1, _ = make_dev_orchestrator()
        rid_b1 = orch_b1.create_run("default")
        with (
            patch.object(orch_b1, "_effective_universal_critique_for_run", return_value=eff),
            patch.object(orch_b1, "_selected_model_for_run", return_value="m"),
            patch.object(orch_b1, "_base_cfg", return_value={}),
        ):
            orch_b1.execute_writer_verifier_pass(rid_b1, workspace=_WS)
        assert m_llm.call_args.kwargs["base_url"] == "http://localhost:11434", (
            "B1: base_url must default to localhost:11434 when runtime config missing"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_b2, _ = make_dev_orchestrator()
        rid_b2 = orch_b2.create_run("default")
        with (
            patch.object(orch_b2, "_effective_universal_critique_for_run", return_value=eff),
            patch.object(orch_b2, "_selected_model_for_run", return_value="m"),
            patch.object(
                orch_b2,
                "_base_cfg",
                return_value={"runtime": {"base_url": "http://example:9000"}},
            ),
        ):
            orch_b2.execute_writer_verifier_pass(rid_b2, workspace=_WS)
        assert m_llm.call_args.kwargs["base_url"] == "http://example:9000", (
            "B2: base_url must be read from _base_cfg runtime.base_url"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_b3, _ = make_dev_orchestrator()
        rid_b3 = orch_b3.create_run("default")
        with (
            patch.object(orch_b3, "_effective_universal_critique_for_run", return_value=eff),
            patch.object(orch_b3, "_selected_model_for_run", return_value="m"),
            patch.object(orch_b3, "_base_cfg", return_value={}),
        ):
            orch_b3.execute_writer_verifier_pass(rid_b3, workspace=_WS)
        timeout_b3 = m_llm.call_args.kwargs["timeout_seconds"]
        assert timeout_b3 == 120.0, "B3: timeout_seconds must default to 120.0"
        assert isinstance(timeout_b3, float), (
            "B3: timeout_seconds must be float-typed even on default"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_b4, _ = make_dev_orchestrator()
        rid_b4 = orch_b4.create_run("default")
        with (
            patch.object(orch_b4, "_effective_universal_critique_for_run", return_value=eff),
            patch.object(orch_b4, "_selected_model_for_run", return_value="m"),
            patch.object(
                orch_b4,
                "_base_cfg",
                return_value={"runtime": {"request_timeout_seconds": 30}},
            ),
        ):
            orch_b4.execute_writer_verifier_pass(rid_b4, workspace=_WS)
        timeout_b4 = m_llm.call_args.kwargs["timeout_seconds"]
        assert timeout_b4 == 30.0, "B4: timeout_seconds must propagate runtime override"
        assert isinstance(timeout_b4, float), (
            "B4: int request_timeout_seconds must be cast to float via float()"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_b5, _ = make_dev_orchestrator()
        rid_b5 = orch_b5.create_run("default")
        with (
            patch.object(orch_b5, "_effective_universal_critique_for_run", return_value=eff),
            patch.object(orch_b5, "_selected_model_for_run", return_value="custom-impl-model:13b"),
        ):
            orch_b5.execute_writer_verifier_pass(rid_b5, workspace=_WS)
        kw_b5 = m_llm.call_args.kwargs
        assert kw_b5["run_id"] == rid_b5, "B5: run_id must propagate verbatim"
        assert kw_b5["model_id"] == "custom-impl-model:13b", (
            "B5: model_id must propagate from _selected_model_for_run verbatim"
        )


def test_implementation_critique_llm_seam_log_snippet_60_line_truncation_4_axis() -> None:
    """Pin the impl-only 60-line log_snippet truncation contract at pipeline.py:1183.

    ``log_snippet = "\\n".join(log.splitlines()[:60])`` is unique to the
    impl seam; tw/pll receive the already-truncated snippet via parameter.

    C1 -- empty log '' -> log_snippet == '' (join of [] is '').
    C2 -- single-line log preserved as-is (no truncation, no trailing newline).
    C3 -- exactly 60-line log fully preserved (all 60 lines).
    C4 -- 100-line log truncated to first 60 lines, last line is 'line59'.
    """
    eff = _make_eff(impl_llm=True, impl_stub=False)

    def _run_with_log(log: str) -> str:
        with (
            patch(
                "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
                return_value=(0, log),
            ),
            patch("hermes_orchestrator.pipeline.execute_implementation_critique_llm") as m_llm,
            patch("hermes_orchestrator.pipeline.emit_stub_implementation_critique_panel"),
        ):
            m_llm.return_value = True
            orch, _ = make_dev_orchestrator()
            rid = orch.create_run("default")
            with (
                patch.object(orch, "_effective_universal_critique_for_run", return_value=eff),
                patch.object(orch, "_selected_model_for_run", return_value="m"),
            ):
                orch.execute_writer_verifier_pass(rid, workspace=_WS)
            return str(m_llm.call_args.kwargs["log_snippet"])

    assert _run_with_log("") == "", "C1: empty log must yield empty log_snippet"

    assert _run_with_log("only line") == "only line", (
        "C2: single-line log must be preserved as-is (no trailing newline)"
    )

    log_60 = "\n".join(f"line{i}" for i in range(60))
    out_c3 = _run_with_log(log_60)
    assert len(out_c3.splitlines()) == 60, (
        "C3: exactly-60-line log must preserve all 60 lines"
    )
    assert out_c3.splitlines()[-1] == "line59", (
        "C3: last line of 60-line snippet must be 'line59'"
    )

    log_100 = "\n".join(f"line{i}" for i in range(100))
    out_c4 = _run_with_log(log_100)
    assert len(out_c4.splitlines()) == 60, (
        "C4: 100-line log must be truncated to first 60 lines via splitlines()[:60]"
    )
    assert out_c4.splitlines()[-1] == "line59", (
        "C4: last preserved line must be 'line59' (zero-indexed line 0..59 = first 60)"
    )


def test_implementation_critique_llm_seam_verifier_exit_code_propagation_3_axis() -> None:
    """Pin verifier_exit_code propagation from run_writer_verifier_bundle.

    Unique to impl: ``verifier_exit_code=code`` reads from the bundle's
    return tuple directly. tw/pll receive ``verifier_exit_code`` as a
    method parameter from their caller (which is this same code variable).

    D1 -- code=0 (success): kwargs verifier_exit_code == 0.
    D2 -- code=1 (failure): kwargs verifier_exit_code == 1.
    D3 -- code=42 (arbitrary): kwargs verifier_exit_code == 42 + LLM called
    exactly once (proves the seam reaches the call site regardless of code).
    """
    eff = _make_eff(impl_llm=True, impl_stub=False)

    def _run_with_code(code: int) -> tuple[int, int]:
        with (
            patch(
                "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
                return_value=(code, "ok"),
            ),
            patch("hermes_orchestrator.pipeline.execute_implementation_critique_llm") as m_llm,
            patch("hermes_orchestrator.pipeline.emit_stub_implementation_critique_panel"),
        ):
            m_llm.return_value = True
            orch, _ = make_dev_orchestrator()
            rid = orch.create_run("default")
            with (
                patch.object(orch, "_effective_universal_critique_for_run", return_value=eff),
                patch.object(orch, "_selected_model_for_run", return_value="m"),
            ):
                orch.execute_writer_verifier_pass(rid, workspace=_WS)
            return int(m_llm.call_args.kwargs["verifier_exit_code"]), int(m_llm.call_count)

    code_d1, calls_d1 = _run_with_code(0)
    assert code_d1 == 0, "D1: code=0 must propagate to kwargs.verifier_exit_code"

    code_d2, calls_d2 = _run_with_code(1)
    assert code_d2 == 1, "D2: code=1 must propagate to kwargs.verifier_exit_code"

    code_d3, calls_d3 = _run_with_code(42)
    assert code_d3 == 42, "D3: code=42 must propagate to kwargs.verifier_exit_code"
    assert calls_d1 == 1 and calls_d2 == 1 and calls_d3 == 1, (
        "D3 cross-cut: LLM must be invoked exactly once for each verifier_exit_code value "
        "(proves the seam reaches the call site regardless of verifier outcome)"
    )

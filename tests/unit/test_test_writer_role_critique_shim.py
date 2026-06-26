from __future__ import annotations


def test_test_writer_critique_shim_exports() -> None:
    from nimbusware_orchestrator.llm import post_verify_role_bindings as bindings
    from nimbusware_orchestrator.llm import test_writer_critique as shim

    assert (
        shim.emit_stub_test_writer_critique_panel is bindings.emit_stub_test_writer_critique_panel
    )
    assert shim.execute_test_writer_critique_llm is bindings.execute_test_writer_critique_llm

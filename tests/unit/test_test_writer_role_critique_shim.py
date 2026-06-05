from __future__ import annotations


def test_test_writer_role_critique_shim_exports() -> None:
    from nimbusware_orchestrator.llm import test_writer_critique as shim
    from nimbusware_orchestrator.llm import test_writer_role_critique as role

    assert shim.emit_stub_test_writer_critique_panel is role.emit_stub_test_writer_critique_panel
    assert shim.execute_test_writer_critique_llm is role.execute_test_writer_critique_llm

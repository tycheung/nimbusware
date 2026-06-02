"""Backward-compatible re-export shim (fo620).

Production LLM code for the ``test_writer`` critique role lives in
``test_writer_role_critique.py`` — not a pytest module.
"""

from hermes_orchestrator.llm.test_writer_role_critique import *  # noqa: F403

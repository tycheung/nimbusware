"""LLM-backed plan/critique — stable import and patch target."""

import nimbusware_orchestrator.ollama_chat as _ollama_chat_mod
from nimbusware_orchestrator.llm import *  # noqa: F403

ollama_chat_json = _ollama_chat_mod.ollama_chat_json

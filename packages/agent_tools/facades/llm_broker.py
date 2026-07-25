"""LLM facade after sak411 thin delete of facades/llm.py."""
from __future__ import annotations

from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch
from orchestrator.llm.slice_facade import execute_slice_implement_llm

__all__ = ["execute_slice_implement_llm", "ollama_chat_json_via_plan_patch"]

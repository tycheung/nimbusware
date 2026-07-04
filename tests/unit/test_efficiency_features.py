from __future__ import annotations

from uuid import uuid4

from agent_core.prompt_tiers import CacheBreakingSection, assemble_prompt_with_cache_metadata
from agent_core.read_outline import python_file_outline, read_mode_for_file
from agent_core.token_telemetry import (
    TokenTelemetrySample,
    record_token_sample,
    token_savings_summary,
)
from agent_core.tool_schema import default_tool_schema_resolver
from memory.index.index_table import build_memory_index_table
from memory.index.models import MemoryRetrievalHit
from orchestrator.role_context_audit import (
    artifact_only_handoff_enabled,
    filter_implement_context,
    implement_context_sources,
)


def test_memory_index_table_is_compact() -> None:
    hits = [
        MemoryRetrievalHit(
            chunk_id=uuid4(),
            excerpt="x" * 500,
            score=0.9,
            run_id=uuid4(),
            category="note",
        ),
    ]
    table = build_memory_index_table(hits, max_chars=400)
    assert "| id |" in table
    assert len(table) < 400


def test_python_outline_extracts_signatures() -> None:
    src = "class Foo:\n    def bar(self, x):\n        return x\n\ndef baz():\n    pass\n"
    outline = python_file_outline(src, rel_path="pkg/mod.py")
    assert "class Foo" in outline
    assert "def bar" in outline
    assert "def baz" in outline


def test_read_mode_outline_for_large_non_target() -> None:
    assert (
        read_mode_for_file(
            "pkg/huge.py",
            line_count=400,
            in_slice_targets=False,
            outline_threshold=200,
            digest_threshold=800,
        )
        == "outline"
    )
    assert read_mode_for_file("pkg/huge.py", line_count=400, in_slice_targets=True) == "full"
    assert (
        read_mode_for_file(
            "pkg/huge.py",
            line_count=900,
            in_slice_targets=False,
            outline_threshold=200,
            digest_threshold=800,
        )
        == "digest"
    )


def test_campaign_read_staleness_tracker(tmp_path) -> None:
    from pathlib import Path

    from agent_core.read_staleness import CampaignReadStalenessTracker

    fp = tmp_path / "ctx.py"
    fp.write_text("a = 1\n", encoding="utf-8")
    tracker = CampaignReadStalenessTracker()
    tracker.note_read(Path(fp))
    assert tracker.is_stale(Path(fp)) is False


def test_cache_breaking_dynamic_section() -> None:
    assembled = assemble_prompt_with_cache_metadata(
        stable="stable rules",
        volatile="slice body",
        dynamic_sections=[
            CacheBreakingSection(label="steer", content="change every turn"),
        ],
    )
    assert len(assembled.cache_blocks) >= 3
    assert any(b.get("cache_breaking") for b in assembled.cache_blocks)


def test_tool_schema_resolver_shorthand() -> None:
    resolver = default_tool_schema_resolver()
    text = resolver.shorthand_list(frozenset({"read", "grep"}))
    assert "read" in text
    assert resolver.schema_for("read") is not None


def test_token_telemetry_aggregates() -> None:
    record_token_sample(TokenTelemetrySample(tokens_in=100, tokens_out=20, offload_saved=30))
    summary = token_savings_summary()
    assert summary["tokens_in"] >= 100
    assert summary["offload_saved"] >= 30


def test_implement_context_filter_and_sources() -> None:
    assert artifact_only_handoff_enabled()
    assert "slice.plan" in implement_context_sources()
    filtered = filter_implement_context({"slice.plan": "x", "chat_transcript": "y"})
    assert "chat_transcript" not in filtered


def test_assembled_prompt_cache_blocks_carry_text() -> None:
    assembled = assemble_prompt_with_cache_metadata(
        stable="stable rules",
        context="session ctx",
        volatile="slice body",
    )
    texts = [str(b.get("text") or "") for b in assembled.cache_blocks]
    assert "stable rules" in texts
    assert "session ctx" in texts
    assert "slice body" in texts


def test_anthropic_system_blocks_split_tiers() -> None:
    from orchestrator.llm.prompt_cache import anthropic_system_content_blocks

    blocks = anthropic_system_content_blocks(
        [
            {"tier": "stable", "text": "A", "cache_control": {"type": "ephemeral"}},
            {"tier": "context", "text": "B", "cache_control": {"type": "ephemeral"}},
        ],
    )
    assert isinstance(blocks, list)
    assert len(blocks) == 2
    assert blocks[0].get("cache_control") == {"type": "ephemeral"}

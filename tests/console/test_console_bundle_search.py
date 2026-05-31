"""Console bundle catalog helper (follow-on 24 §14 #12)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

from nimbusware_console.bundle_catalog import (
    BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH,
    bundle_search_after_hits_stale_caption,
    bundle_search_empty_hits_readiness_caption,
    bundle_search_filename_slug,
    bundle_search_hit_count_caption,
    bundle_search_hits_summary_caption,
    bundle_search_k_caption,
    bundle_search_query_length_caption,
    bundle_search_top_hit_preview_caption,
    run_bundle_catalog_search,
)


def test_bundle_search_empty_hits_readiness_caption_when_index_not_ready() -> None:
    cap = bundle_search_empty_hits_readiness_caption(
        {"query": "auth", "hits": [], "faiss_index_ready": False},
    )
    assert cap is not None
    assert "not ready" in cap.lower()
    assert BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH in cap


def test_bundle_search_empty_hits_readiness_caption_when_index_ready() -> None:
    cap = bundle_search_empty_hits_readiness_caption(
        {"query": "auth", "hits": [], "faiss_index_ready": True},
    )
    assert cap is not None
    assert "zero hits" in cap.lower()


def test_bundle_search_empty_hits_readiness_caption_none_when_hits_present() -> None:
    assert (
        bundle_search_empty_hits_readiness_caption(
            {"query": "auth", "hits": [{"id": "x"}], "faiss_index_ready": False},
        )
        is None
    )


def test_bundle_search_empty_hits_readiness_caption_none_for_bad_payload() -> None:
    assert bundle_search_empty_hits_readiness_caption(None) is None
    assert bundle_search_empty_hits_readiness_caption("x") is None
    assert (
        bundle_search_empty_hits_readiness_caption(
            {"query": "", "hits": [], "faiss_index_ready": False},
        )
        is None
    )


def test_bundle_search_k_caption() -> None:
    cap = bundle_search_k_caption({"query": "auth", "k": 5})
    assert cap is not None
    assert "**5**" in cap
    assert bundle_search_k_caption(None) is None
    assert bundle_search_k_caption({}) is None
    assert bundle_search_k_caption({"query": "auth"}) is None
    assert bundle_search_k_caption({"query": "  ", "k": 3}) is None
    assert bundle_search_k_caption({"query": "auth", "k": 0}) is None
    assert bundle_search_k_caption({"query": "auth", "k": True}) is None


def test_bundle_search_query_length_caption() -> None:
    assert bundle_search_query_length_caption("   ") is None
    cap = bundle_search_query_length_caption("  auth rbac  ")
    assert cap is not None
    assert "**9**" in cap
    cap_hits = bundle_search_query_length_caption("q", hit_count=2)
    assert cap_hits is not None
    assert "**2** hits" in cap_hits
    cap_bad_hits = bundle_search_query_length_caption("q", hit_count=True)
    assert cap_bad_hits is not None
    assert "hits" not in cap_bad_hits


def test_bundle_search_hit_count_caption() -> None:
    cap = bundle_search_hit_count_caption(
        {"query": "auth", "hits": [{"id": "a"}, {"id": "b"}]},
    )
    assert cap is not None
    assert "**2**" in cap
    assert "hits" in cap
    cap1 = bundle_search_hit_count_caption(
        {"query": "x", "hits": [{"id": "only"}]},
    )
    assert cap1 is not None
    assert "**1**" in cap1
    assert "hit." in cap1
    assert bundle_search_hit_count_caption({"query": "x", "hits": []}) is None
    assert bundle_search_hit_count_caption(None) is None


def test_bundle_search_top_hit_preview_caption() -> None:
    cap = bundle_search_top_hit_preview_caption(
        {
            "query": "auth",
            "hits": [{"id": "auth-rbac", "score": 0.91}],
        },
    )
    assert cap is not None
    assert "auth-rbac" in cap
    assert "0.91" in cap
    assert bundle_search_top_hit_preview_caption({"query": "x", "hits": []}) is None
    assert bundle_search_top_hit_preview_caption(None) is None


def test_bundle_search_hits_summary_caption_after_search() -> None:
    cap = bundle_search_hits_summary_caption(
        {
            "query": "auth",
            "k": 5,
            "hits": [{"id": "a"}, {"id": "b"}],
            "faiss_index_ready": True,
            "faiss_index_stale": False,
        },
    )
    assert cap is not None
    assert "q='auth'" in cap
    assert "k=5" in cap
    assert "hits=2" in cap
    assert "faiss_index_ready=yes" in cap
    assert "faiss_index_stale=no" in cap


def test_bundle_search_hits_summary_caption_none_for_bad_payload() -> None:
    assert bundle_search_hits_summary_caption(None) is None
    assert bundle_search_hits_summary_caption({"query": "", "k": 5, "hits": []}) is None


def test_bundle_search_after_hits_stale_caption_when_stale_and_hits() -> None:
    cap = bundle_search_after_hits_stale_caption(
        {
            "faiss_index_stale": True,
            "hits": [{"id": "x"}],
        },
    )
    assert cap is not None
    assert "stale" in cap.lower()
    assert BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH in cap


def test_bundle_search_after_hits_stale_caption_none_when_not_stale() -> None:
    assert (
        bundle_search_after_hits_stale_caption(
            {"faiss_index_stale": False, "hits": [{"id": "x"}]},
        )
        is None
    )


def test_bundle_search_after_hits_stale_caption_none_when_stale_but_no_hits() -> None:
    assert (
        bundle_search_after_hits_stale_caption(
            {"faiss_index_stale": True, "hits": []},
        )
        is None
    )


def test_bundle_search_after_hits_stale_caption_none_for_bad_payload() -> None:
    assert bundle_search_after_hits_stale_caption(None) is None
    assert bundle_search_after_hits_stale_caption("x") is None


def test_run_bundle_catalog_search_finds_auth_bundle() -> None:
    root = Path(__file__).resolve().parents[2]
    out = run_bundle_catalog_search(root, "auth", k=5)
    assert out["query"] == "auth"
    assert out["k"] == 5
    assert "faiss_index_ready" in out and isinstance(out["faiss_index_ready"], bool)
    assert "faiss_index_stale" in out
    ids = {str(h.get("id")) for h in out["hits"] if isinstance(h, dict)}
    assert "auth-rbac-starter" in ids


def test_run_bundle_catalog_search_empty_query_returns_no_hits() -> None:
    root = Path(__file__).resolve().parents[2]
    out = run_bundle_catalog_search(root, "   ", k=3)
    assert out["hits"] == []
    assert out["query"] == ""
    assert out["k"] == 3
    assert "faiss_index_ready" in out


def test_run_bundle_catalog_search_clamps_k() -> None:
    root = Path(__file__).resolve().parents[2]
    out = run_bundle_catalog_search(root, "billing", k=99)
    assert out["k"] == 20


def test_bundle_search_filename_slug_sanitizes() -> None:
    assert bundle_search_filename_slug("auth rbac!") == "auth_rbac"


def test_bundle_search_filename_slug_empty_fallback() -> None:
    assert bundle_search_filename_slug("   @@  ") == "query"



"""Smoke tests for ingestion + retrieval."""
from __future__ import annotations

from src.ingestion import build_or_load_index, chunk_corpus
from src.retrieval import compare_retrieval_methods, index_status, retrieve, retrieve_hybrid


def test_chunking_produces_chunks():
    chunks = chunk_corpus()
    assert len(chunks) > 0
    sources = {c.source for c in chunks}
    assert "rtl_design_basics.md" in sources
    assert "clock_reset_cdc_notes.md" in sources
    for c in chunks:
        assert c.text.strip()
        assert c.section


def test_index_builds():
    bundle = build_or_load_index(force=False)
    assert bundle["index"] is not None
    assert len(bundle["chunks"]) > 0


def test_retrieve_known_query_hits_relevant_source():
    items = retrieve("non-blocking assignment in sequential logic", top_k=5)
    assert items, "Expected at least one retrieval result"
    sources = {it.chunk.source for it in items}
    assert sources & {"rtl_design_basics.md", "systemverilog_notes.md"}


def test_retrieve_scores_sorted_descending():
    items = retrieve("CDC and metastability risks", top_k=5)
    scores = [it.score for it in items]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_empty_query_returns_empty():
    assert retrieve("") == []
    assert retrieve("   ") == []


def test_hybrid_retrieval_returns_ranked_results():
    items = retrieve_hybrid("include path missing compile error", top_k=5)
    assert items
    assert len(items) <= 5
    scores = [it.score for it in items]
    assert scores == sorted(scores, reverse=True)
    assert all(it.dense_score is not None for it in items)
    assert all(it.lexical_score is not None for it in items)


def test_compare_retrieval_methods_returns_dense_and_hybrid():
    out = compare_retrieval_methods("CDC synchronizer metastability", top_k=3)
    assert set(out) == {"dense", "hybrid"}
    assert out["dense"]
    assert out["hybrid"]


def test_index_status_reports_sources():
    status = index_status()
    assert status["n_chunks"] > 0
    assert status["n_sources"] >= 6

"""Sanity tests for utils, mock LLM, and evaluation runner."""
from __future__ import annotations

import json

from src.evaluation import evaluate_qa, evaluate_workflows
from src.mock_llm import compose_answer, hash_embed
from src.utils import clean_text, keyword_match_count, truncate


def test_clean_text_idempotent_and_safe_on_empty():
    assert clean_text("") == ""
    assert clean_text(None) == ""  # type: ignore[arg-type]
    s = "line1\r\n\r\n\r\nline2"
    cleaned = clean_text(s)
    assert "\r" not in cleaned
    assert clean_text(cleaned) == cleaned


def test_keyword_match_count():
    assert keyword_match_count("non-blocking assignment in always_ff", ["non-blocking", "always_ff"]) == 2
    assert keyword_match_count("", ["x"]) == 0
    assert keyword_match_count("anything", []) == 0


def test_truncate_respects_limit():
    assert truncate("short") == "short"
    out = truncate("a" * 500, 100)
    assert len(out) <= 100
    assert out.endswith("…")


def test_compose_answer_with_no_chunks_returns_safe_message():
    out = compose_answer("anything", [])
    assert "could not find" in out.lower() or "escalate" in out.lower()


def test_hash_embed_shape_and_normalization():
    mat = hash_embed(["hello world", "foo bar"])
    assert mat.shape == (2, 384)
    norms = (mat * mat).sum(axis=1) ** 0.5
    # rows with content should be unit-normalized
    assert all(abs(n - 1.0) < 1e-3 for n in norms)


def test_evaluate_qa_runs_and_returns_metrics():
    report = evaluate_qa()
    d = report.to_dict()
    json.dumps(d)  # serializable
    assert d["n"] == 20
    for key in (
        "hit_rate",
        "mrr",
        "citation_coverage",
        "grounded_answer_rate",
        "high_risk_routing_accuracy",
    ):
        assert 0.0 <= d[key] <= 1.0


def test_evaluate_workflows_runs_and_returns_metrics():
    report = evaluate_workflows()
    d = report.to_dict()
    json.dumps(d)
    assert d["n"] == 8
    assert 0.0 <= d["category_accuracy"] <= 1.0
    assert 0.0 <= d["escalation_accuracy"] <= 1.0

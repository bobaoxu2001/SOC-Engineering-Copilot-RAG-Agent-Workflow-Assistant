"""Evaluation runners for QA retrieval/answer quality and triage workflow.

Metrics implemented:
- Retrieval hit rate @ k
- MRR of expected source
- Citation coverage
- Average top-k similarity
- Missing-context rate
- Grounded Answer Rate / Citation Faithfulness (custom rule-based metric)
- Out-of-scope handling accuracy (safety / refusal cases)
- Workflow classification accuracy / owner accuracy / escalation accuracy
- Calibration: avg confidence on correct vs incorrect
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config
from .agent_workflows import triage
from .rag_pipeline import answer
from .retrieval import retrieve
from .utils import keyword_match_count, read_json, write_json


# ---------------------------------------------------------------------------
# QA evaluation
# ---------------------------------------------------------------------------


@dataclass
class QAItemResult:
    id: str
    question: str
    topic: str
    is_out_of_scope: bool
    expected_sources: list[str]
    retrieved_sources: list[str]
    top_score: float
    avg_topk_score: float
    hit: bool
    reciprocal_rank: float
    cited_expected: bool
    keyword_hits: int
    expected_keywords: int
    answer_grounded: bool
    out_of_scope_handled: bool
    expect_human_review: bool
    actual_human_review: bool
    high_risk_correct: bool
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QAReport:
    n: int
    n_regular: int
    n_out_of_scope: int
    hit_rate: float
    mrr: float
    citation_coverage: float
    avg_top_score: float
    avg_topk_score: float
    missing_context_rate: float
    grounded_answer_rate: float
    high_risk_routing_accuracy: float
    out_of_scope_handling_accuracy: float
    items: list[dict] = field(default_factory=list)
    timestamp: float = 0.0
    mode: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _grounded(item_result: dict) -> bool:
    """Grounded Answer Rate / Citation Faithfulness for regular (in-scope) items.

    Counts as grounded when:
      - at least one expected source appears in the retrieved sources, AND
      - at least one expected keyword appears in the answer text, AND
      - human-review routing matches expectation for high-risk topics.
    """
    if item_result.get("is_out_of_scope"):
        return False  # handled by the separate out-of-scope metric
    return (
        item_result["hit"]
        and item_result["keyword_hits"] >= 1
        and item_result["high_risk_correct"]
    )


def _out_of_scope_handled(item_result: dict, actual_hr: bool) -> bool:
    """An out-of-scope / refusal case is handled correctly when:
      - human_review_required is True (system declines to auto-answer), AND
      - at least one expected keyword appears in the answer (refusal language present).
    """
    if not item_result.get("is_out_of_scope"):
        return False
    return actual_hr and item_result["keyword_hits"] >= 1


def evaluate_qa(top_k: int | None = None) -> QAReport:
    eval_path = config.EVAL_DIR / "qa_eval_set.json"
    data = read_json(eval_path)
    items = data["items"]
    k = top_k or config.TOP_K_DEFAULT

    results: list[QAItemResult] = []
    for it in items:
        is_oos = bool(it.get("is_out_of_scope", False))
        retrieved = retrieve(it["question"], top_k=k)
        retrieved_sources = [r.chunk.source for r in retrieved]
        expected = it.get("expected_sources", [])
        hit = any(s in retrieved_sources for s in expected) if expected else False

        rr = 0.0
        for rank, r in enumerate(retrieved, start=1):
            if r.chunk.source in expected:
                rr = 1.0 / rank
                break

        top_score = retrieved[0].score if retrieved else 0.0
        avg_top = (
            sum(r.score for r in retrieved) / len(retrieved) if retrieved else 0.0
        )
        cited_expected = hit

        rag = answer(it["question"], top_k=k)
        kw_hits = keyword_match_count(rag.answer, it.get("expected_keywords", []))

        expect_hr = bool(it.get("expect_human_review", False))
        actual_hr = bool(rag.human_review_required)
        # For regular items: routing is correct if expectation matches actuality.
        # For out-of-scope: always measure against expected_human_review=True.
        high_risk_correct = (expect_hr == actual_hr) if (expect_hr or is_oos) else True

        item_dict = {
            "id": it["id"],
            "question": it["question"],
            "topic": it.get("topic", ""),
            "is_out_of_scope": is_oos,
            "expected_sources": expected,
            "retrieved_sources": retrieved_sources,
            "top_score": round(float(top_score), 4),
            "avg_topk_score": round(float(avg_top), 4),
            "hit": hit,
            "reciprocal_rank": round(rr, 4),
            "cited_expected": cited_expected,
            "keyword_hits": kw_hits,
            "expected_keywords": len(it.get("expected_keywords", [])),
            "answer_grounded": False,
            "out_of_scope_handled": False,
            "expect_human_review": expect_hr,
            "actual_human_review": actual_hr,
            "high_risk_correct": high_risk_correct,
            "confidence": round(float(rag.confidence), 4),
        }
        item_dict["answer_grounded"] = _grounded(item_dict)
        item_dict["out_of_scope_handled"] = _out_of_scope_handled(item_dict, actual_hr)
        results.append(QAItemResult(**item_dict))

    regular = [r for r in results if not r.is_out_of_scope]
    oos = [r for r in results if r.is_out_of_scope]

    n = len(results) or 1
    n_reg = len(regular) or 1
    n_oos = len(oos) or 1

    # Retrieval / citation metrics computed on regular items only.
    hit_rate = sum(1 for r in regular if r.hit) / n_reg
    mrr = sum(r.reciprocal_rank for r in regular) / n_reg
    citation_coverage = sum(1 for r in regular if r.cited_expected) / n_reg
    avg_top_score = sum(r.top_score for r in regular) / n_reg
    avg_topk_score = sum(r.avg_topk_score for r in regular) / n_reg
    missing_context_rate = sum(
        1 for r in regular if r.top_score < config.RELEVANCE_THRESHOLD
    ) / n_reg
    grounded = sum(1 for r in regular if r.answer_grounded) / n_reg
    high_risk_acc = sum(1 for r in results if r.high_risk_correct) / n

    # Out-of-scope safety metric.
    oos_acc = (
        sum(1 for r in oos if r.out_of_scope_handled) / max(len(oos), 1)
        if oos
        else 1.0
    )

    return QAReport(
        n=n,
        n_regular=len(regular),
        n_out_of_scope=len(oos),
        hit_rate=round(hit_rate, 4),
        mrr=round(mrr, 4),
        citation_coverage=round(citation_coverage, 4),
        avg_top_score=round(avg_top_score, 4),
        avg_topk_score=round(avg_topk_score, 4),
        missing_context_rate=round(missing_context_rate, 4),
        grounded_answer_rate=round(grounded, 4),
        high_risk_routing_accuracy=round(high_risk_acc, 4),
        out_of_scope_handling_accuracy=round(oos_acc, 4),
        items=[r.to_dict() for r in results],
        timestamp=time.time(),
        mode=config.llm_mode_label(),
    )


# ---------------------------------------------------------------------------
# Workflow evaluation
# ---------------------------------------------------------------------------


@dataclass
class WorkflowItemResult:
    id: str
    expected_category: str
    predicted_category: str
    category_correct: bool
    expected_owner: str
    predicted_owner: str
    owner_correct: bool
    expected_human_review: bool
    actual_human_review: bool
    escalation_correct: bool
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowReport:
    n: int
    category_accuracy: float
    owner_accuracy: float
    escalation_accuracy: float
    avg_confidence_correct: float
    avg_confidence_incorrect: float
    human_review_rate: float
    items: list[dict] = field(default_factory=list)
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_workflows() -> WorkflowReport:
    data = read_json(config.EVAL_DIR / "workflow_eval_set.json")
    items = data["items"]
    results: list[WorkflowItemResult] = []
    for it in items:
        tr = triage(it["log_text"])
        results.append(
            WorkflowItemResult(
                id=it["id"],
                expected_category=it["expected_category"],
                predicted_category=tr.issue_category,
                category_correct=(tr.issue_category == it["expected_category"]),
                expected_owner=it["expected_owner"],
                predicted_owner=tr.suggested_owner_team,
                owner_correct=(tr.suggested_owner_team == it["expected_owner"]),
                expected_human_review=bool(it["expected_human_review"]),
                actual_human_review=bool(tr.human_review_required),
                escalation_correct=(
                    bool(tr.human_review_required) == bool(it["expected_human_review"])
                ),
                confidence=tr.confidence,
            )
        )

    n = len(results) or 1
    cat_acc = sum(1 for r in results if r.category_correct) / n
    owner_acc = sum(1 for r in results if r.owner_correct) / n
    esc_acc = sum(1 for r in results if r.escalation_correct) / n
    correct = [r.confidence for r in results if r.category_correct]
    incorrect = [r.confidence for r in results if not r.category_correct]
    avg_correct = sum(correct) / len(correct) if correct else 0.0
    avg_incorrect = sum(incorrect) / len(incorrect) if incorrect else 0.0
    hr_rate = sum(1 for r in results if r.actual_human_review) / n

    return WorkflowReport(
        n=n,
        category_accuracy=round(cat_acc, 4),
        owner_accuracy=round(owner_acc, 4),
        escalation_accuracy=round(esc_acc, 4),
        avg_confidence_correct=round(avg_correct, 4),
        avg_confidence_incorrect=round(avg_incorrect, 4),
        human_review_rate=round(hr_rate, 4),
        items=[r.to_dict() for r in results],
        timestamp=time.time(),
    )


def save_eval_results(qa: QAReport, wf: WorkflowReport, name: str = "eval_results.json") -> Path:
    out = {"qa": qa.to_dict(), "workflow": wf.to_dict()}
    path = config.EVAL_DIR / name
    write_json(path, out)
    return path

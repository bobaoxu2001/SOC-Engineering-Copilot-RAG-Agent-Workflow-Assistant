"""SOC Engineering Copilot — FastAPI service layer.

Exposes five endpoints that wrap the existing src modules so the copilot
functionality can be consumed by other internal tools, scripts, or CI pipelines.

All endpoints work without OPENAI_API_KEY; the deterministic mock LLM is
used automatically when no key is configured.

Run with:
    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /health         — liveness check
    POST /retrieve       — top-k RAG retrieval
    POST /ask            — full RAG answer with citations
    POST /triage         — 6-step log triage
    POST /evaluate       — run QA + workflow eval set and return metrics
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src import config
from src.agent_workflows import triage as _triage
from src.evaluation import evaluate_qa, evaluate_workflows
from src.rag_pipeline import answer as _answer
from src.retrieval import retrieve as _retrieve, index_status

app = FastAPI(
    title="SOC Engineering Copilot API",
    description=(
        "Internal AI productivity service for SOC / hardware engineering teams. "
        "Provides cited RAG answers, transparent retrieval, deterministic triage, "
        "and evaluation metrics. Synthetic public-safe knowledge base; not a "
        "sign-off authority."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query string")
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class RetrievedChunk(BaseModel):
    rank: int
    score: float
    source: str
    section: str
    text: str
    likely_relevant: bool


class RetrieveResponse(BaseModel):
    query: str
    top_k: int
    results: list[RetrievedChunk]
    embedder: str


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question for the copilot")
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[str]
    confidence: float
    human_review_required: bool
    high_risk_topic: bool
    used_mock: bool
    n_chunks: int


class TriageRequest(BaseModel):
    log_text: str = Field(..., min_length=1, description="Build / verification / lint log snippet")


class TriageResponse(BaseModel):
    issue_category: str
    severity: str
    likely_root_cause: str
    related_knowledge_sources: list[str]
    recommended_next_steps: list[str]
    suggested_owner_team: str
    confidence: float
    human_review_required: bool
    generated_ticket_summary: str


class EvaluateResponse(BaseModel):
    qa: dict[str, Any]
    workflow: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    """Liveness check. Also reports index status and LLM mode."""
    try:
        status = index_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Index not ready: {exc}") from exc
    return {
        "status": "ok",
        "llm_mode": config.llm_mode_label(),
        "n_chunks": status["n_chunks"],
        "n_sources": status["n_sources"],
        "embedder": status["embedder"],
    }


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve_endpoint(req: RetrieveRequest) -> RetrieveResponse:
    """Return top-k chunks for a query with similarity scores."""
    k = req.top_k or config.TOP_K_DEFAULT
    try:
        items = _retrieve(req.query, top_k=k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    chunks = [
        RetrievedChunk(
            rank=it.rank,
            score=round(float(it.score), 4),
            source=it.chunk.source,
            section=it.chunk.section,
            text=it.chunk.text,
            likely_relevant=it.likely_relevant,
        )
        for it in items
    ]
    embedder = ""
    try:
        embedder = index_status()["embedder"]
    except Exception:
        pass
    return RetrieveResponse(query=req.query, top_k=k, results=chunks, embedder=embedder)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest) -> AskResponse:
    """Generate a cited RAG answer. High-risk topics trigger human-review flag."""
    try:
        resp = _answer(req.query, top_k=req.top_k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AskResponse(
        query=resp.query,
        answer=resp.answer,
        citations=resp.citations,
        confidence=round(resp.confidence, 4),
        human_review_required=resp.human_review_required,
        high_risk_topic=resp.high_risk_topic,
        used_mock=resp.used_mock,
        n_chunks=len(resp.chunks),
    )


@app.post("/triage", response_model=TriageResponse)
def triage_endpoint(req: TriageRequest) -> TriageResponse:
    """Run the 6-step triage agent on a build / verification / lint log."""
    try:
        result = _triage(req.log_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TriageResponse(
        issue_category=result.issue_category,
        severity=result.severity,
        likely_root_cause=result.likely_root_cause,
        related_knowledge_sources=result.related_knowledge_sources,
        recommended_next_steps=result.recommended_next_steps,
        suggested_owner_team=result.suggested_owner_team,
        confidence=result.confidence,
        human_review_required=result.human_review_required,
        generated_ticket_summary=result.generated_ticket_summary,
    )


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate_endpoint() -> EvaluateResponse:
    """Run the full QA + workflow evaluation and return metrics."""
    try:
        qa = evaluate_qa()
        wf = evaluate_workflows()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    qa_dict = qa.to_dict()
    qa_dict.pop("items", None)  # keep response lean
    wf_dict = wf.to_dict()
    wf_dict.pop("items", None)
    return EvaluateResponse(qa=qa_dict, workflow=wf_dict)

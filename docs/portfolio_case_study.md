# Engineering Knowledge Copilot - RAG + Agent Workflow Assistant

## One-line pitch

A portfolio-grade internal AI tool that gives engineering teams cited answers from a domain knowledge base and deterministic first-pass triage for build, verification, and lint failures.

## Problem

Engineering teams accumulate design notes, debug playbooks, checklists, and repeated failure patterns across many documents. When an engineer hits a build or verification issue, the work often starts with manual search: find the right note, identify the likely owner, decide whether the issue is routine or high-risk, and write a usable handoff summary.

This project models that workflow with a synthetic, public-safe SOC/hardware knowledge base. The goal is not to replace engineers; it is to show how an internal AI assistant can reduce search and routing friction while staying transparent about evidence and limitations.

## Why a general chatbot is not enough

A general chatbot is too opaque for engineering support workflows. It may provide plausible answers without showing the source, change its routing behavior from run to run, or fail to distinguish routine build issues from high-risk hardware topics.

This project uses RAG, citations, deterministic routing, and human-review gates so reviewers can inspect why the system answered the way it did. CDC, reset, integration, assertion, sign-off, and proprietary-data topics are treated as high-risk and require human review.

## Solution overview

The application has four main surfaces:

- **Ask Copilot:** RAG Q&A with source+section citations, confidence, and human-review flags.
- **Retrieval Inspector:** top-k retrieved chunks with scores, sources, sections, and relevance indicators.
- **Workflow Triage Agent:** deterministic six-step triage for build, verification, lint, CDC/reset, and unknown issues.
- **Evaluation Dashboard:** QA and workflow metrics over held-out synthetic eval sets.

The same core modules are also exposed through a FastAPI service layer, making the project feel like an internal tool that could be integrated into CI, ticketing, or engineering support workflows.

## System architecture

The system is intentionally lightweight:

- `app.py` provides the Streamlit interface.
- `api.py` exposes `/health`, `/retrieve`, `/ask`, `/triage`, and `/evaluate`.
- `src/ingestion.py` chunks the markdown knowledge base and builds the FAISS index.
- `src/retrieval.py` performs top-k retrieval with optional source filters.
- `src/rag_pipeline.py` builds prompts, calls the live or mock LLM path, attaches citations, and computes confidence.
- `src/agent_workflows.py` runs deterministic workflow triage.
- `src/evaluation.py` computes QA and workflow evaluation metrics.

The app runs without an API key using a deterministic mock LLM and hash-vector embedding fallback. That makes demos, tests, and CI reproducible.

## RAG design

The RAG layer uses a synthetic markdown knowledge base that represents engineering notes and playbooks. The ingestion pipeline preserves document and section metadata so the answer layer can cite `source.md > Section` labels.

Key design choices:

- Header-aware markdown chunking to keep sections coherent.
- FAISS vector retrieval for fast local search.
- Sentence-transformer embeddings when available.
- Deterministic hash-vector fallback when model download or external services are unavailable.
- Confidence derived from retrieval strength and score separation.
- Human-review gating for high-risk topics and low-confidence answers.

## Agent workflow design

The triage agent is deterministic by design. It follows a six-step workflow:

1. Classify the log using regex and keyword patterns.
2. Retrieve relevant playbook context for the predicted category.
3. Generate a root-cause hypothesis from known patterns.
4. Recommend next steps from category defaults and retrieved checklist lines.
5. Decide owner team, confidence, and human-review requirement.
6. Generate a compact ticket-ready summary.

This design is less flashy than a fully LLM-driven agent, but it is more suitable for operational triage because the category, owner, and escalation behavior are reproducible.

## Evaluation methodology

The project includes two held-out synthetic evaluation sets:

- **QA eval set:** 26 questions, including 20 in-scope questions and 6 out-of-scope or safety cases.
- **Workflow eval set:** 8 triage cases covering build, verification, lint, CDC/reset, and unknown issues.

QA metrics include retrieval hit rate, MRR, citation coverage, average similarity, missing-context rate, Grounded Answer Rate / Citation Faithfulness, high-risk routing accuracy, and out-of-scope handling accuracy.

Workflow metrics include issue-category accuracy, owner-team accuracy, escalation accuracy, human-review rate, and confidence calibration.

## Key results

The README reports the current deterministic mock-LLM baseline:

- QA retrieval hit rate at k=5: **95%** on in-scope questions.
- Mean reciprocal rank: **0.875** on in-scope questions.
- Citation coverage: **95%** on in-scope questions.
- Grounded Answer Rate / Citation Faithfulness: **90%** on in-scope questions.
- Out-of-scope handling accuracy: **100%** on safety/refusal cases.
- Workflow issue-category accuracy: **100%**.
- Workflow owner-team accuracy: **100%**.
- Workflow escalation accuracy: **100%**.

These results are from the included synthetic eval sets and should be interpreted as portfolio validation, not production performance. Because the knowledge base is synthetic and intentionally small, near-perfect scores are expected in this controlled demo. A real deployment would need larger historical logs, richer internal documentation, confidence calibration, access control, monitoring, and source-level permissions before the metrics could be treated as operational evidence.

## Limitations

- The knowledge base is synthetic, intentionally small, and much simpler than a real internal documentation corpus.
- The retrieval stack does not include a reranker or hybrid lexical+dense search.
- The workflow categories are intentionally narrow.
- The app does not include authentication, access control, audit logging, or document permissions.
- The mock LLM is deterministic and useful for reproducibility, but it is not a substitute for evaluating a production LLM endpoint.

## Future improvements

- Add a cross-encoder reranker and compare against the FAISS-only baseline.
- Add hybrid BM25+dense retrieval for exact-match engineering terms.
- Add latency, retrieval drift, and per-step observability metrics.
- Add a connector pattern for private documentation systems.
- Add auth, permissions, and source-level access filtering.
- Extend triage categories and evaluate on a larger failure-log set.

## What this project demonstrates for AI engineering roles

This project demonstrates practical AI engineering beyond a basic chatbot:

- RAG architecture with citations, retrieval inspection, and groundedness metrics.
- Agent workflow design where deterministic routing is used for reliability.
- API design that exposes the AI workflow as a service.
- Evaluation discipline with held-out test sets and reproducible mock-mode behavior.
- Product judgment around trust, high-risk domains, human review, and public-safe demo data.
- Recruiter-facing communication through screenshots, demo script, case study, and deployment docs.

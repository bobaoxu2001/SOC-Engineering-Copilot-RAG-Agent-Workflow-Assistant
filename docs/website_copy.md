# Website-ready Project Copy

## Short project title

Engineering Knowledge Copilot

## One-line website subtitle

Cited RAG answers and deterministic workflow triage for internal engineering teams.

## 3 project card bullets

- Built a cited RAG assistant over a synthetic public-safe engineering knowledge base.
- Designed a deterministic six-step triage agent for build, verification, and lint logs.
- Added FastAPI endpoints, evaluation metrics, screenshots, CI tests, and offline mock-LLM mode.

## 6 technical tags

RAG, AI Agents, FastAPI, Streamlit, FAISS, Evaluation

## 100-word project summary

Engineering Knowledge Copilot is a portfolio-grade internal AI tooling project for engineering knowledge retrieval and workflow triage. It combines cited RAG over a synthetic SOC/hardware knowledge base, a retrieval inspector, a deterministic six-step triage agent for build/verification/lint logs, a FastAPI service layer, and an evaluation dashboard. The system is designed for reliability rather than chatbot novelty: answers cite source sections, high-risk topics trigger human review, and the project runs without an API key using a deterministic mock LLM. It demonstrates practical RAG design, agent workflow orchestration, evaluation rigor, and product judgment for applied AI roles.

## 200-word case study summary

Engineering teams often lose time searching internal docs, interpreting repeated failure logs, and routing issues to the right owner. Engineering Knowledge Copilot models a safer internal AI assistant for that workflow. It uses a synthetic public-safe SOC/hardware knowledge base to demonstrate cited RAG, transparent retrieval, deterministic triage, and measurable evaluation without relying on proprietary data.

The app has four surfaces: Ask Copilot for cited answers, Retrieval Inspector for top-k evidence review, Workflow Triage Agent for log classification and owner routing, and Evaluation Dashboard for QA and workflow metrics. The backend is intentionally modular: ingestion builds a FAISS index from markdown knowledge files, retrieval returns scored chunks with source metadata, the RAG layer composes cited answers using a live or mock LLM path, and the triage workflow applies deterministic rules for category, next steps, escalation, and ticket summary. A FastAPI layer exposes the same capabilities for service-style integration.

The project emphasizes reliability patterns expected in real internal tools: offline reproducibility, human-review gates for high-risk topics, explicit limitations, CI tests, and held-out eval sets measuring retrieval hit rate, MRR, grounded-answer rate, safety handling, and workflow routing accuracy.

## Resume bullet versions

### AI Engineer version

- Built a portfolio-grade RAG + agent workflow assistant using Python, Streamlit, FastAPI, FAISS, and an OpenAI-compatible LLM interface, with cited answers, deterministic mock-LLM fallback, retrieval inspection, and human-review gating for high-risk engineering topics.

### Data Scientist version

- Designed an evaluation framework for a synthetic engineering RAG system, measuring retrieval hit rate, MRR, citation coverage, Grounded Answer Rate / Citation Faithfulness, out-of-scope handling, and workflow triage accuracy over held-out QA and log-triage datasets.

### AI Product / Strategy version

- Framed and shipped an internal AI tooling prototype that balances automation with trust: transparent citations, deterministic issue routing, public-safe demo data, human-review escalation, API-ready service boundaries, and recruiter-facing documentation.

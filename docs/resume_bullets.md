# Resume Bullets

Targeted to **NVIDIA JR2017063 — SOC AI Application Engineer, AI Services, Agents and Knowledge Systems, Shanghai**.

---

## Short resume bullets (one-liners for a tight resume)

- Built a **RAG + agent-workflow AI productivity prototype** for SOC/hardware engineering teams using Python, FAISS, sentence-transformers, and an OpenAI-compatible LLM interface with a deterministic mock fallback — all citations are grounded in a local knowledge base; high-risk hardware topics (CDC, reset, integration, assertion failures) always require human review.

- Designed a **quantitative evaluation harness** with retrieval hit rate (95%), MRR, citation coverage, Grounded Answer Rate (90%), out-of-scope safety accuracy, and a full workflow triage accuracy suite (classification 100%, escalation 100%) over held-out eval sets.

- Shipped a **FastAPI service layer** (`/health`, `/ask`, `/retrieve`, `/triage`, `/evaluate`) over the existing RAG + agent modules, enabling downstream integration with internal engineering tooling pipelines.

---

## Detailed resume bullets (for a project section or cover letter)

**SOC Engineering Copilot — RAG + Agent Workflow Assistant**
Portfolio project · Python · FAISS · Streamlit · FastAPI · sentence-transformers · OpenAI-compatible LLM

- Designed and implemented a **retrieval-augmented generation (RAG) knowledge system** for SOC/hardware engineering teams: header-aware markdown chunking, FAISS vector index (sentence-transformers or hash-vector fallback), top-k retrieval with similarity scores, and cited answers surfaced through a four-tab Streamlit UI.

- Built a **six-step deterministic triage agent** (`classify → retrieve → hypothesize → next-steps → escalate → ticket`) for build, verification, and lint log analysis — rule-based classification, playbook-grounded root-cause hypotheses, owner-team routing (CAD/Methodology / Verification / Design + Human Review), and explicit human-review gating on high-risk hardware topics.

- Shipped a **FastAPI service layer** (five endpoints: `/health`, `/ask`, `/retrieve`, `/triage`, `/evaluate`) that exposes the same RAG and agent capabilities for programmatic access by CI pipelines or other internal tools; includes a 9-test suite using FastAPI TestClient.

- Implemented a **custom evaluation framework** with two held-out sets (20 QA questions, 8 triage cases) measuring retrieval hit rate, MRR, citation coverage, Grounded Answer Rate / Citation Faithfulness, out-of-scope handling accuracy, and triage classification + escalation accuracy; baseline results: 95% QA hit rate, 90% grounded-answer rate, 100% workflow classification and escalation accuracy.

- Applied **safety-first reliability patterns**: deterministic mock LLM fallback for offline demos, confidence-threshold gating, mandatory human-review on CDC / reset / integration / assertion topics, and refusal / insufficient-context handling for sign-off and proprietary-data requests.

---

## LinkedIn project description

**SOC Engineering Copilot: RAG + Agent Workflow Assistant**

An internal AI productivity prototype for SOC and hardware engineering teams. Built as a portfolio project targeting NVIDIA JR2017063 (AI Application Engineer, Shanghai).

**What it does:**
- Cited Q&A over an engineering knowledge base (RTL, SystemVerilog, SOC integration, build flow, verification, CDC/reset) — every answer references the source file and section.
- Transparent FAISS-backed retrieval with similarity scores visible in a dedicated "Retrieval Inspector" tab.
- Six-step deterministic triage agent for build, verification, and lint logs — classifies, retrieves playbook context, generates a root-cause hypothesis, recommends next steps, routes to the right team, and drafts a Jira-ready ticket.
- Quantitative evaluation dashboard: retrieval hit rate, MRR, Grounded Answer Rate / Citation Faithfulness, out-of-scope safety accuracy, and triage classification + escalation accuracy.
- FastAPI service layer for programmatic access by CI pipelines or internal tooling.

**Why it matters for an AI application engineering role:**
The project shows the full engineering pattern for a reliable, non-toy internal LLM tool: RAG design choices (chunking strategy, embedding fallback, scored retrieval), agent orchestration (explicit multi-step pipeline with auditable rules), evaluation rigor (custom metrics, held-out eval sets), and safety framing (human-review gating on high-risk hardware topics, refusal on out-of-scope requests).

**Stack:** Python · FastAPI · Streamlit · FAISS · sentence-transformers · OpenAI-compatible API · pytest · GitHub Actions CI

**Public-safe synthetic knowledge base.** Not a sign-off authority. Not production-ready. High-risk hardware topics (CDC, reset synchronization, integration, assertion failures) always require human engineering review.

🔗 [GitHub repo](https://github.com/bobaoxu2001/SOC-Engineering-Copilot-RAG-Agent-Workflow-Assistant)

# NVIDIA JR2017063 — Job-Description Alignment

This document maps the responsibilities listed in the job description for **SOC AI Application Engineer — AI Services, Agents and Knowledge Systems (Job ID JR2017063)** to concrete features in this project. Every feature is implemented in the repository; line references point to where the behavior lives.

| JD requirement | Project feature | Where to find it |
|---|---|---|
| Build LLM-backed services for engineering teams | RAG answer pipeline with cited responses, live + mock LLM paths, deterministic fallback | [src/rag_pipeline.py](../src/rag_pipeline.py), [src/mock_llm.py](../src/mock_llm.py) |
| RAG and knowledge systems (chunking, embeddings, vector retrieval, citations) | Header-aware chunking, sentence-transformer or hash-vector embeddings, FAISS index, source+section citations | [src/ingestion.py](../src/ingestion.py), [src/retrieval.py](../src/retrieval.py) |
| Agent orchestration / agentic workflows | 6-step deterministic triage agent: classify → retrieve → hypothesize → recommend → escalate → ticket | [src/agent_workflows.py](../src/agent_workflows.py) |
| Claude Code-style reusable skills / playbooks | Reusable triage playbook templates per category (build / verification / lint / cdc_reset) and prompt templates for RAG | [src/agent_workflows.py](../src/agent_workflows.py), [src/rag_pipeline.py](../src/rag_pipeline.py) |
| Evaluation of retrieval and answer quality | QA eval runner with hit rate, MRR, citation coverage, grounded answer rate; workflow eval runner with classification, owner, escalation accuracy | [src/evaluation.py](../src/evaluation.py), [data/eval/](../data/eval/) |
| Reliability — confidence, fallback, human review | Confidence computed from retrieval signals; high-risk topic detection; mandatory human-review on CDC / reset / integration / assertion topics; deterministic mock fallback | [src/rag_pipeline.py](../src/rag_pipeline.py), [src/agent_workflows.py](../src/agent_workflows.py), [src/config.py](../src/config.py) |
| Internal tools / web UI for non-AI engineering users | Streamlit four-tab internal-tool UI: Ask, Retrieval Inspector, Triage, Evaluation | [app.py](../app.py) |
| Collaboration with non-AI stakeholders | UI surfaces retrieved context, scores, pipeline trace, and structured JSON so a hardware engineer can audit every answer | [app.py](../app.py) |
| Test coverage and engineering rigor | pytest suite covering retrieval, agent, and evaluation paths | [tests/](../tests/) |
| Public-safe, non-proprietary content | Synthetic, general engineering knowledge base; project framed as a productivity prototype, not sign-off authority | [data/knowledge_base/](../data/knowledge_base/), [README.md](../README.md) |

## Specific responses to JD signals

**"Help engineering teams be more productive."** Every tab maps to a hardware-engineer task: looking up design guidance, inspecting how the retrieval works, triaging a build/verification log, and proving the system's quality. The project is framed as a productivity prototype, not a chip-design assistant.

**"Reliability of LLM applications."** The system computes confidence from retrieval scores plus topic risk and forces human-review gating on high-risk hardware topics. The mock LLM path keeps the demo deterministic when no API key is available, which matters for reproducible internal tooling.

**"Build and evaluate."** The evaluation tab is not decorative — it computes retrieval hit rate, MRR, citation coverage, a custom Grounded Answer Rate / Citation Faithfulness metric, and workflow classification + escalation accuracy on held-out evaluation sets, with per-item failure analysis.

**"Knowledge systems."** The ingestion path does header-aware splitting, attaches `source` + `section` metadata, and exposes citations in the form `source.md › Section` so an engineer can find the underlying material in seconds.

**"Agentic workflows."** The triage agent is explicitly multi-step with auditable rules at each stage. Routing decisions are deterministic so the agent does not silently change behavior between runs.

**"What this prototype is not."** It is not a sign-off authority, not production software, and not built on proprietary data. CDC, reset, integration, and assertion topics always trigger human-review gating and are phrased as general guidance.

# Interview Talking Points

## 30-second project pitch

I built an internal AI tooling prototype for engineering knowledge retrieval and workflow triage. It combines cited RAG over a synthetic SOC/hardware knowledge base, a transparent retrieval inspector, a deterministic six-step triage agent for build/verification/lint logs, a FastAPI service layer, and an evaluation dashboard. The point of the project is reliability: every answer is grounded in retrieved sources, high-risk topics require human review, and the whole system runs without an API key using a deterministic mock LLM.

## 2-minute technical walkthrough

The project has three core layers. First, the ingestion and retrieval layer chunks markdown engineering notes, preserves source and section metadata, builds a FAISS index, and retrieves top-k chunks for each query. Second, the RAG layer builds a cited prompt from those chunks, calls either an OpenAI-compatible LLM or a deterministic mock fallback, and computes confidence plus human-review flags. Third, the workflow layer triages logs through a deterministic pipeline: classify the issue, retrieve relevant playbook context, hypothesize root cause, recommend next steps, route to an owner, and draft a ticket summary.

The Streamlit app exposes this in four tabs: Ask Copilot, Retrieval Inspector, Workflow Triage Agent, and Evaluation Dashboard. The FastAPI layer exposes the same functionality through `/health`, `/retrieve`, `/ask`, `/triage`, and `/evaluate`, so the app is not only a UI demo. The evaluation dashboard runs held-out QA and workflow test sets and reports retrieval hit rate, MRR, citation coverage, grounded-answer rate, out-of-scope handling, and triage routing accuracy.

## How the RAG pipeline works

The knowledge base is a set of synthetic public-safe markdown files. The ingestion code splits them into coherent chunks while retaining document and section metadata. Retrieval uses FAISS with sentence-transformer embeddings when available, and a deterministic hash-vector fallback when external models are unavailable.

For a question, the pipeline retrieves top-k chunks, formats them as numbered context blocks, asks the answer layer to cite source labels, and returns the final answer with citations, retrieved chunks, confidence, high-risk-topic status, and mock/live LLM mode. If the query touches CDC, reset, integration, assertion failures, sign-off, or proprietary data, the response is explicitly flagged for human review.

## How the triage agent works

The triage agent is a deterministic workflow rather than a free-form LLM agent. It:

1. Classifies the input log as build, verification, lint, CDC/reset, or unknown.
2. Retrieves category-specific playbook context.
3. Produces a root-cause hypothesis from known log patterns.
4. Combines default next steps with relevant retrieved checklist lines.
5. Selects an owner team and human-review requirement.
6. Generates a ticket-ready summary.

The output includes structured fields such as issue category, severity, related sources, recommended steps, owner team, confidence, and human-review status.

## Why deterministic routing was used instead of fully LLM-based routing

The routing decision is operationally sensitive. If the same log routes to different teams on different runs, the tool becomes hard to trust. Deterministic classification and escalation rules make the workflow reproducible, testable, and easier to debug.

The LLM is better used for summarization and explanation, while routing, escalation, and high-risk gating should be controlled by explicit policy. That balance is the product judgment behind the agent design.

## How evaluation works

The QA eval set checks whether expected sources are retrieved, where they rank, whether the answer cites the expected source, whether expected keywords appear in the answer, and whether high-risk or out-of-scope questions trigger review/refusal behavior.

The workflow eval set checks predicted category, owner team, and escalation decision against expected values. The dashboard also reports confidence summaries so reviewers can see whether the model is calibrated enough for the demo setting.

## What tradeoffs were made

- The project uses synthetic data so it can be public and recruiter-safe.
- The retrieval stack is simple and local; no reranker or hybrid search is included yet.
- The triage agent favors deterministic rules over LLM autonomy.
- The app prioritizes transparent evaluation over a flashy chat-only interface.
- The mock LLM fallback improves reproducibility but is not meant to represent production LLM quality.

## How this could be productionized

Productionization would require authentication, role-based access controls, source-level document permissions, audit logs, observability, latency tracking, private document connectors, CI/CD deployment, and a stronger evaluation loop using real historical issues. I would also add hybrid retrieval, reranking, drift monitoring, human feedback capture, and a review queue for low-confidence or high-risk answers.

## 5 likely interview questions and strong answers

### 1. Why did you build a deterministic agent instead of using an LLM planner?

Because the highest-risk part of this workflow is not prose generation; it is routing and escalation. I wanted the system to behave consistently, be easy to test, and make policy decisions auditable. An LLM can help with summaries, but owner-team routing and human-review rules should be deterministic in this type of internal engineering tool.

### 2. How do you know the RAG answers are grounded?

I evaluate grounding with several signals: whether expected sources appear in top-k retrieval, the reciprocal rank of the expected source, citation coverage, expected keyword matches in the answer, and whether high-risk routing matches expectation. The custom Grounded Answer Rate only counts an answer when retrieval, answer content, and review routing all pass.

### 3. What would you improve first for production quality?

I would add access control and source permissions first because internal knowledge tools often contain sensitive documents. On the ML side, I would add hybrid search plus reranking and evaluate whether it improves hit rate and grounded-answer rate on a larger dataset.

### 4. Why include a mock LLM?

The mock LLM makes the project runnable in CI, demos, and recruiter review without requiring an API key. It also makes tests deterministic. That is important for a portfolio project because reviewers can validate behavior without external dependencies.

### 5. How would this generalize beyond SOC/hardware engineering?

The domain can change while the pattern remains the same: chunk domain documents, retrieve cited context, gate risky topics, expose an API, and evaluate both answer quality and workflow decisions. The triage rules would be replaced with the policies and routing categories of the new domain.

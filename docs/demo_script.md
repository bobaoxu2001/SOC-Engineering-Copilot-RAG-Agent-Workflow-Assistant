# Demo Script — 60–90 Second Walkthrough

For a recruiter, hiring manager, or technical reviewer evaluating this project against NVIDIA JR2017063.

**Setup:** `streamlit run app.py` open, browser on `http://localhost:8501`.

---

## Opening (10 sec)

> "Hardware engineering teams generate enormous amounts of internal knowledge — design checklists, build-flow guides, debug playbooks. The challenge is not creating this knowledge; it's reliably retrieving it, getting cited answers, and routing issues to the right people without replacing the engineers who own those decisions."
>
> "This is the SOC Engineering Copilot — a prototype of the kind of AI internal tooling an AI Application Engineer would build for an SOC org. Let me walk you through four capabilities."

---

## Step 1 — Ask Copilot: cited RAG answer (20 sec)

Click the **Ask Copilot** tab.

Type or click the example question:
> "What are common CDC risks during SOC integration?"

Point out after the answer loads:
- **Answer bullets** are grounded in the retrieved knowledge — not a bare LLM response.
- **Citations row** shows `clock_reset_cdc_notes.md › CDC Risks` and `soc_integration_checklist.md › Clock and Reset Connections` — the engineer can go read the source.
- **Confidence badge** is amber/red because this is a high-risk topic.
- **"Human review required"** callout fires automatically — CDC and reset architecture decisions must be reviewed by a hardware engineer; the system does not present itself as a sign-off authority.

> "The system knows what it doesn't know, and it knows which topics are too high-risk for an LLM to make a call on."

---

## Step 2 — Retrieval Inspector: see inside the RAG layer (15 sec)

Click the **Retrieval Inspector** tab.

Type:
> "reset synchronization deassertion synchronizer"

Click **Search index**. Point out the table:
- **Score column** — cosine similarity, sorted descending. The reviewer can see exactly how good the match is.
- **Source + section** — chunk metadata so retrieval is auditable, not a black box.
- **Likely relevant** — boolean derived from a score threshold; signals when retrieval confidence is low.

> "This tab exists because RAG quality is not something you can assess just from the answer — you have to look at what was retrieved. It's the kind of transparency that matters in a production AI service."

---

## Step 3 — Workflow Triage Agent: multi-step orchestration (20 sec)

Click the **Workflow Triage Agent** tab.

Select `verification_failure_01.txt` from the dropdown. Click **Run triage agent**.

Point out the **pipeline trace**:
1. Classify → `verification` with assertion-failure detection
2. Retrieve → pulls from `verification_debug_playbook.md` and `systemverilog_notes.md`
3. Hypothesize root cause → specific message about the assertion and reset timing
4. Recommend next steps → 4–6 concrete actions
5. Decide escalation → `Verification` team, `human_review_required: True` because of assertion failure
6. Generate ticket → ready-to-paste Jira summary

> "This isn't a single LLM call. It's a deterministic six-step pipeline — rule-based classification, retrieval-grounded hypothesis, explicit escalation rules. The routing decision is reproducible and auditable."

Point to the **structured JSON output** panel.

> "Every field is typed, every escalation has a reason, and the system never silently auto-resolves a hardware failure."

---

## Step 4 — Evaluation Dashboard: quantitative reliability (15 sec)

Click the **Evaluation Dashboard** tab. Click **Run evaluation**.

Point to the metric cards after they load:
- **QA hit rate 95%** — 19 of 20 questions retrieve at least one expected source
- **Grounded Answer Rate 90%** — answers that cite a correct source AND contain expected keywords AND correctly route high-risk questions
- **Workflow classification accuracy 100%**, escalation accuracy 100% on 8 held-out cases
- **High-risk routing accuracy 100%** — every CDC/reset/integration/assertion question triggered human-review gating

> "An AI service is only as trustworthy as its evaluation. This dashboard shows retrieval hit rate, citation faithfulness, and agent classification accuracy — the metrics you'd track in a real deployment."

---

## Close (10 sec)

> "The entire stack runs offline with a deterministic fallback — no API key required for a demo. It's Python, Streamlit, FAISS, and an OpenAI-compatible LLM interface that works with any endpoint. There's also a FastAPI service layer exposing `/ask`, `/retrieve`, `/triage`, and `/evaluate` for integration into internal tooling pipelines."
>
> "This is the kind of AI application-layer engineering the JR2017063 role describes — LLM-backed services, RAG knowledge systems, agent orchestration, and evaluation — built on a public-safe synthetic knowledge base to show the approach without claiming proprietary content."

---

## NVIDIA JR2017063 alignment summary (for follow-up questions)

| JD signal | What the demo showed |
|---|---|
| LLM-backed services | RAG pipeline with cited responses, live + mock path |
| RAG & knowledge systems | Header-aware chunking, FAISS retrieval, source+section citations |
| Agent orchestration | 6-step triage pipeline with explicit stage trace |
| Evaluation | Retrieval hit rate, MRR, grounded-answer rate, workflow accuracy |
| Reliability | Deterministic fallback, confidence gating, mandatory human review |
| Internal tools for engineers | Streamlit UI + FastAPI service layer |
| Non-AI stakeholder collaboration | Every answer is citable and auditable by a hardware engineer |

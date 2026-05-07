# Project Brief

**Title:** SOC Engineering Copilot — RAG + Agent Workflow Assistant

**One-liner:** An internal AI productivity prototype that helps SOC and hardware engineering teams search design knowledge, get cited answers, and triage build/verification/lint logs through a deterministic agent — with retrieval and answer quality continuously evaluated.

## Problem

Hardware engineering teams accumulate large bodies of internal knowledge: design checklists, methodology notes, debug playbooks, and integration guides. Engineers spend significant time searching this material and routing build/verification failures to the right owner. A general-purpose chatbot is not appropriate here: hardware decisions are high-risk, must be cited, and must always defer to a human reviewer for sensitive topics like CDC, reset architecture, and integration sign-off.

## What this prototype does

- **Cited Q&A** over a synthetic, public-safe engineering knowledge base.
- **Transparent retrieval** so an engineer can see exactly which chunks fed an answer.
- **Deterministic multi-step triage** for build, verification, and lint logs, with explicit owner-team routing and human-review gating.
- **Quantitative evaluation** of retrieval and triage quality, with a custom Grounded Answer Rate / Citation Faithfulness metric.

## What this prototype is not

- Not a sign-off authority for any hardware decision.
- Not a substitute for hardware engineers. Final decisions on CDC, reset, integration, and assertion-related findings always require human review.
- Not built on proprietary data. The knowledge base is synthetic, general engineering material.
- Not production software. It is a demo-grade prototype meant to show an AI tooling approach, not to be deployed as-is.

## Who this is for

- **Hardware engineers** who want a faster path to relevant internal knowledge with citations they can audit.
- **CAD / methodology teams** who want a deterministic first-pass triage for repeated build and lint issues.
- **AI tooling engineers** who want to see how RAG, agent orchestration, and evaluation come together in a real-feeling internal tool.

## Why this design

- **Citation-first, never bare LLM output.** Every answer references the source file and section.
- **Human-review gating on high-risk topics.** Hard-coded list (CDC, reset, integration, assertion) plus low-confidence escalation.
- **Deterministic where it matters.** The triage agent's routing and escalation rules are rule-based, not LLM-based, so behavior is reproducible.
- **Offline-safe demo.** The mock LLM and hash-vector fallback let the project run end-to-end without external services.

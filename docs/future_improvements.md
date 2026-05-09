# Future Improvements

This roadmap keeps the project honest as a portfolio demo while outlining practical steps toward production-grade internal AI tooling.

## Expand Knowledge Base And Dynamic Indexing

- Expand the synthetic knowledge base with richer engineering docs, deeper playbooks, and more edge cases.
- Add dynamic indexing for new or updated documents, with clear index rebuild status and validation checks.

## Add Hybrid Retrieval And Reranking

- Compare dense FAISS retrieval against BM25+dense hybrid retrieval.
- Add a cross-encoder reranker and measure whether it improves hit rate, MRR, and grounded-answer rate.

## Add Confidence Calibration

- Calibrate answer and routing confidence against a larger validation set.
- Track calibration drift when the knowledge base, eval set, or embedding model changes.

## Expand Triage Categories

- Add timing, synthesis, formal verification, and DFT triage categories.
- Extend workflow eval coverage for each new category before surfacing it in the app.

## Add Deeper Error Analysis

- Add a confusion matrix for workflow classification and owner routing.
- Add richer per-question failure analysis for retrieval misses, citation misses, and safety-routing errors.

## Add Governance And Observability

- Add source-level permissions so users only retrieve documents they are allowed to access.
- Add audit logs and monitoring for usage, latency, low-confidence answers, and high-risk review events.

## Add Editable Ticketing Workflow Integration

- Keep the editable ticket draft pattern, but add an approval step before any ticketing-system integration.
- Preserve a human-in-the-loop workflow so the demo never auto-submits external tickets.

## Evaluate On Larger Historical Logs

- Evaluate routing and escalation quality on larger historical build, lint, verification, CDC, integration, and methodology logs.
- Compare controlled synthetic results against realistic historical failure distributions.

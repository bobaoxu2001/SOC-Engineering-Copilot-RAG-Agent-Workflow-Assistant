# Future Improvements

This roadmap keeps the project honest as a portfolio demo while outlining practical steps toward production-grade internal AI tooling.

## Expand Knowledge Base And Dynamic Indexing

- Expand the synthetic knowledge base with richer engineering docs, deeper playbooks, and more edge cases.
- Add dynamic indexing for new or updated documents, with clear index rebuild status and validation checks.

## Add Hybrid Retrieval And Reranking

- Replace the current lightweight lexical overlap scorer with a stronger BM25 implementation if the corpus grows.
- Tune dense/hybrid weighting by query type instead of using one fixed blend.
- Add a cross-encoder reranker and measure whether it improves hit rate, MRR, and grounded-answer rate.

## Add Confidence Calibration

- Calibrate answer and routing confidence against a larger validation set.
- Track calibration drift when the knowledge base, eval set, or embedding model changes.

## Expand Triage Categories

- Add deeper subcategories for timing, synthesis, formal verification, and DFT findings.
- Extend workflow eval coverage with more cases per category before treating category-level metrics as meaningful.

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

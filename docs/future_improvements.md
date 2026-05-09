# Future Improvements

Practical next steps to move this portfolio demo closer to production-grade internal AI tooling:

- Expand the synthetic knowledge base with richer engineering docs, more edge cases, and deeper playbooks.
- Add hybrid retrieval and reranking to compare dense-only retrieval against BM25+dense plus cross-encoder reranking.
- Add confidence calibration using a larger validation set and track calibration drift over time.
- Add a confusion matrix and deeper error analysis for both QA retrieval and workflow triage outcomes.
- Add an editable ticket workflow integration that keeps the human in control before any external submission.
- Add source-level permissions, audit logs, and monitoring for access-controlled internal documentation.
- Add larger historical log evaluation to test routing quality across more realistic build, lint, verification, CDC, and integration failures.

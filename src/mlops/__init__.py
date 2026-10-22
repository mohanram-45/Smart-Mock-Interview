"""MLOps support: experiment tracking (MLflow), run provenance and privacy-safe operational metrics.

Nothing here changes scoring, retrieval or the interview flow. Everything is optional and best-effort: if MLflow is not installed the tracker
reports that clearly, and the metrics / health hooks never raise into a request."""

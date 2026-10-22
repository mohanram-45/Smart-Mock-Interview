"""Stage 3C-3: human-validation workflow and read-only application hand-off for the modular evaluator.

Everything here READS results; nothing here scores, calls a model, or is imported by Flask (legacy scoring stays the default). Provenance is explicit:
real-model results, mock results, advisory-only questions and human-validated numbers are always labelled differently."""

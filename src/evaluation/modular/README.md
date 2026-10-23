# Modular evaluator (Stage 3C-1, offline prototype)

Pipeline: segment claims -> build requirements (scope sidecar) -> verifier (mock/LLM) -> validation gate -> consistency checks -> deterministic rubric -> optional feedback.

* Not imported by Flask or by the legacy evaluator; legacy backend is the default.
* Only 16 scope-eligible records can receive a numeric score; the other 650 are advisory only.
* All verifiers in the repo are mocks. Nothing here is human-validated or a measure of grading accuracy.

Full description: `reports/stage3c1_architecture.md`. Experiment plan: `reports/stage3c1_real_llm_experiment_plan.md`.

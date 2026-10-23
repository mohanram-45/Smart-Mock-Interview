"""Stage 4A: end-to-end mock-interview DEMONSTRATION layer for the existing Flask application (blueprint at /demo).

What it is: an operational interview flow (setup -> questions -> answers -> summary -> review) over the curated RAG question source, with every evaluation result
labelled by where it came from. What it is NOT: a grader. Nothing here is human-validated, nothing here feeds adaptive difficulty, and the legacy /api/* routes and the
AdaptiveInterviewSession are untouched.

Layers kept visibly separate on every screen:
  1. operational flow        (progress, questions, answers)
  2. legacy score            (the app's existing similarity scorer + its feedback; default)
  3. experimental modular    (opt-in; REAL MODEL live / MOCK VERIFIER; clearly marked, not validated)
  4. advisory feedback       (questions without penalty-eligible scope: findings and feedback, NO number)
  5. unavailable / abstained (a reason, never a fabricated score)
Importing this package is cheap: the modular evaluator, the scorers and the retrieval stack are imported lazily, only when a session actually asks for them.
"""

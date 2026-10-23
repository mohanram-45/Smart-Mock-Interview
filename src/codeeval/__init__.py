"""Stage 5A: experimental, opt-in CODE-AWARE assessment prototype. Independent of the legacy scorers and of the modular prose evaluator.

Layers (each has one job; none of them produces a grade):
  extract   split a submitted answer into code and prose (pure text handling)
  static    read the code with `ast` (the code is PARSED, never run) and report structure + unsafe constructs
  spec      what a question requires, as data: functional tests, structural requirements, explanation topics
  harness   the behaviour tests themselves; a self-contained file that only ever runs INSIDE an isolated environment
  runner    the execution interface: DISABLED by default; the only real backend is a locked-down container, enabled explicitly and only after a self-test
  evaluate  combines the above into findings, kept apart: verified correct / demonstrated / missing / incorrect / unverified

Nothing here may be used to drive adaptive difficulty, and nothing here is human-validated.
"""
ENGINE = "code-eval-prototype"
VERSION = "5a.0"

"""Stage 3A: evidence-grounded LLM answer evaluation FOUNDATION (offline, provider-independent).

Nothing here is wired into the live Flask scoring path. The legacy scorers stay the default
(SMART_EVALUATION_BACKEND=legacy). No provider is configured by default and no network call happens at import time.
"""
from .schema import (EVALUATION_SCHEMA_VERSION, EvaluationRequest, EvaluationResult, EvaluationStatus, LLMEvaluation,
                     ReferenceBundle, SupportSnippet)

__all__ = ["EVALUATION_SCHEMA_VERSION", "EvaluationRequest", "EvaluationResult", "EvaluationStatus", "LLMEvaluation",
           "ReferenceBundle", "SupportSnippet"]

"""Tiny, dependency-free contract between AdaptiveInterviewSession and an optional question source.

A provider is a callable ``provider(domains: list[str]) -> list[dict]`` returning legacy-shaped question dicts
({id, domain, difficulty, question, reference_answer, ...}). ``None`` (the default) means the legacy JSON file.
Importing this module must stay free of faiss / torch / numpy so legacy mode never pays for the retrieval stack.
"""


class QuestionSourceUnavailable(RuntimeError):
    """The selected question source cannot serve requests (e.g. curated corpus failed integrity checks).
    The HTTP layer maps this to 503. It never triggers a silent fall back to another source."""

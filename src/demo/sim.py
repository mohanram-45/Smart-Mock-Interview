"""Scripted interview driver (Stage 10): plays a whole interview against the engine with a deterministic candidate. Used by tests and by scripts/stage10_eval_suite.py.
It is a simulator of CANDIDATES, not of models; whatever is measured with it is labelled 'scripted' wherever it is reported."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from . import interview as I

Answerer = Callable[[int, Dict[str, Any], Dict[str, Any]], Optional[str]]


def run(engine, payload: Dict[str, Any], answerer: Answerer, *, max_turns: int = 40, on_turn: Optional[Callable[[Dict[str, Any]], None]] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    s = engine.create(payload)
    sid = s["id"]
    transcript: List[Dict[str, Any]] = []
    for _ in range(max_turns):
        s = engine.get(sid)
        if s["status"] == "finished":
            break
        i = s["current"]
        q = s["questions"][i]
        text = answerer(i + 1, q, s)
        row = {"n": i + 1, "stage": I.stage_of(q), "origin": q.get("origin"), "lead": q.get("lead") or "", "question": q["question"], "competency": q.get("competency"),
               "followup_kind": q.get("followup_kind"), "memory_ref": (q.get("provenance") or {}).get("memory_ref"), "answer": text}
        if text is None:
            engine.skip(sid, i + 1)
        else:
            engine.submit(sid, i + 1, text)
        transcript.append(row)
        if on_turn:
            on_turn(row)
    return engine.get(sid), transcript


class Overlap:
    """Word-overlap stand-in for Sentence-BERT, used ONLY by the offline simulator. It is not a quality measure of anything."""
    def score(self, ref, ans):
        r, a = set(ref.lower().split()), ans.lower().split()
        return 0.0 if not a else min(1.0, sum(w in r for w in a) / len(a))


_LEXICAL_ONLY = None


def _lexical_service():
    """A private retrieval service that can ONLY rank lexically. It is deliberately NOT the process-wide singleton: asking `get_service()` for BM25 created the real default service (Sentence-BERT + FAISS
    where installed) and left it cached, so every later `S._service is not None` check in the same process saw a service that ranks semantically (10N final Windows repair, failure 1)."""
    global _LEXICAL_ONLY
    if _LEXICAL_ONLY is None:
        from src.retrieval.service import RetrievalService

        class LexicalOnlyService(RetrievalService):
            def _load_semantic(self):                     # never loads an embedder, a model or an index
                self._sem_attempted = True
                return None
        _LEXICAL_ONLY = LexicalOnlyService()
    return _LEXICAL_ONLY


def bm25_search(query: str, domain: str) -> Dict[str, Any]:
    """Candidate-question ranking by BM25 ONLY. 10M: the offline engine used to call the process-wide retrieval service, which silently switches to Sentence-BERT + FAISS wherever those are
    installed (a Windows .bot environment) and so orders the candidate questions differently from a machine without them; every scripted test that depends on WHICH question comes next then
    passed on one platform and failed on the other. This ranker never loads a model, and (10N) never creates or touches the process-wide service, so the order is the same everywhere."""
    from src.retrieval.retriever import validate_query
    svc = _lexical_service()
    q = validate_query(query, 40)
    hits = svc._lex().search(q, k=40, domain=domain)
    return {"query": q, "mode": "bm25_fallback", "score_type": "bm25", "degraded_reason": "offline simulator: BM25 only, by design", "results": [svc._public(h, rank, "bm25") for rank, h in enumerate(hits, 1)]}


def offline_engine(directory, *, seed: int = 11, followup_generator=None):
    """A DemoEngine on a scratch folder with the stand-in scorer (no torch, no model, no network). Retrieval falls back to BM25 when sentence-transformers is absent."""
    import random
    from pathlib import Path

    from .engine import DemoEngine
    from .store import DemoStore
    return DemoEngine(DemoStore(Path(directory) / "sessions"), scorer_factory=lambda k, c: Overlap(), feedback_fn=lambda s, q, a, m: "", rng=random.Random(seed), followup_generator=followup_generator,
                      search_fn=bm25_search)

"""Shared helpers for the Stage 3C-1 modular-evaluator tests (offline; mock verifiers only)."""
from src.evaluation.modular import ModularEvaluator, ReferenceMaterial, ScopeStore
from src.evaluation.modular.mock_verifiers import ScriptedVerifier, scripted

_STORE = None


def store() -> ScopeStore:
    global _STORE
    if _STORE is None:
        _STORE = ScopeStore.load()
    return _STORE


def ref_of(by_id, qid) -> ReferenceMaterial:
    return ReferenceMaterial.from_corpus_record(by_id[qid])


def run(by_id, qid, answer, behaviour=None, *, spec=None, store_=None, **kw):
    """Evaluate `answer` with a scripted mock verifier. `spec` goes through mock_verifiers.scripted(); `behaviour` is used as-is."""
    v = ScriptedVerifier(behaviour if behaviour is not None else scripted(spec or {}, **kw))
    res = ModularEvaluator(store_ or store(), v).evaluate(qid, by_id[qid]["question"], answer, ref_of(by_id, qid))
    return res, v


def dim(res, name):
    return next(d for d in res.dimensions if d.name == name)

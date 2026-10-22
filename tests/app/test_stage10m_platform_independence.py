"""Stage 10M: platform independence of the scripted engine tests, and the restart scoring bug. Windows has sentence-transformers + FAISS and the sandbox does not; nothing below may depend on which."""
import collections
import json
import math
import random

import pytest

from src.demo import memory as M, opportunity_eval as OE, sim
from src.demo.engine import DemoEngine
from src.demo.store import DemoStore

PAYLOAD = {"role": "Data Scientist", "practical": False, "size": 8, "followup_mode": "mock", "max_followups": 2}


def _engine(tmp_path, search_fn):
    return DemoEngine(DemoStore(tmp_path / "sessions"), scorer_factory=lambda k, c: sim.Overlap(), feedback_fn=lambda s, q, a, m: "", rng=random.Random(11), search_fn=search_fn)


def test_the_offline_engine_never_loads_a_semantic_model_or_calls_the_service_search(monkeypatch, tmp_path):
    from src.retrieval import service as SV
    real = SV.get_service()

    class Guard:
        def __getattr__(self, name):
            if name in ("search", "_load_semantic", "warm"):
                raise AssertionError(f"the offline engine used the semantic retrieval path ({name})")
            return getattr(real, name)
    monkeypatch.setattr(SV, "get_service", lambda *a, **k: Guard())
    e = sim.offline_engine(tmp_path)
    e._followup_generator = OE.scripted_generator()
    s, _ = sim.run(e, PAYLOAD, OE._partial_answers(e, OE.MED))
    assert s["status"] == "finished" and s["plan"]["retrieval"]["mode"] == "bm25_fallback"


class _DenseEmbedder:
    """A stand-in with Sentence-BERT's behaviour that matters here: it calls itself 'sentence-bert' and gives every pair a non-zero similarity."""
    name = "sentence-bert"

    @staticmethod
    def _v(t):
        t = " " + t.lower() + " "
        c = collections.Counter(t[i:i + 3] for i in range(len(t) - 2))
        n = math.sqrt(sum(v * v for v in c.values())) or 1
        return {k: v / n for k, v in c.items()}

    def rank(self, q, docs):
        a = self._v(q)
        return [sum(a.get(k, 0) * v for k, v in self._v(d).items()) for d in docs]


def _reversed(q, d):
    r = sim.bm25_search(q, d)
    r["results"] = list(reversed(r["results"]))
    return r


@pytest.mark.parametrize("name", ["bm25", "reversed_ranking", "no_ranking", "dense_sentence_bert_like_memory_embedder"])
def test_a_grounded_memory_question_appears_whatever_the_ranking_or_embedder(monkeypatch, tmp_path, name):
    for k in ("SMART_DEMO_MEMORY_SBERT", "SMART_DEMO_MEMORY_SEMANTIC_FLOOR"):
        monkeypatch.delenv(k, raising=False)
    fn = {"bm25": sim.bm25_search, "reversed_ranking": _reversed, "no_ranking": None, "dense_sentence_bert_like_memory_embedder": sim.bm25_search}[name]
    if name.startswith("dense"):
        monkeypatch.setattr(M, "default_embedder", lambda: _DenseEmbedder())
    e = _engine(tmp_path, fn)
    e._followup_generator = OE.scripted_generator()
    s, _ = sim.run(e, PAYLOAD, OE._partial_answers(e, OE.MED))
    stages = {x.get("memory_stage") for x in s["plan"]["followup_log"]}
    mem_q = [q for q in s["questions"] if q.get("followup_kind") in ("llm", "mock") and q.get("memory_id")]
    assert "used" in stages and mem_q, (name, stages)
    for q in mem_q:
        it = M.get(s["memory"], q["memory_id"])
        assert it["turn"] == 1 and q["lead"] == M.recall_lead(it)


def test_a_restarted_engine_still_scores_answers_with_the_legacy_scorer(tmp_path):
    """10M: `legacy scoring failed: 'bert'`. A session stores 'legacy scorer available'; the scorer registry is per process, so after a restart the lookup raised KeyError and every score became 'unavailable'."""
    e1 = sim.offline_engine(tmp_path)
    sid = e1.create(PAYLOAD)["id"]
    ans = OE._partial_answers(e1, OE.MED)
    for _ in range(2):
        s = e1.get(sid)
        i = s["current"]
        e1.submit(sid, i + 1, ans(i + 1, s["questions"][i], s))
    e2 = sim.offline_engine(tmp_path)
    assert not e2._scorers, "a fresh process has nothing loaded"
    s = e2.get(sid)
    i = s["current"]
    e2.submit(sid, i + 1, "Cross validation splits the data into folds and rotates the held out fold.")
    a = e2.get(sid)["answers"][i]
    assert a["legacy"]["status"] in ("scored", "skipped") or "KeyError" not in str(a["legacy"].get("reason")), a["legacy"]
    scored = [x for x in e2.get(sid)["answers"] if x and x["legacy"]["status"] == "scored"]
    assert scored, "scoring works after a restart"


def test_a_scorer_that_cannot_load_after_a_restart_is_reported_as_unavailable_with_its_reason(tmp_path):
    e1 = sim.offline_engine(tmp_path)
    sid = e1.create(PAYLOAD)["id"]
    ans = OE._partial_answers(e1, OE.MED)
    s = e1.get(sid)
    e1.submit(sid, 1, ans(1, s["questions"][0], s))

    def boom(k, c):
        raise RuntimeError("model files missing")
    e2 = DemoEngine(DemoStore(tmp_path / "sessions"), scorer_factory=boom, feedback_fn=lambda s, q, a, m: "", rng=random.Random(11), search_fn=sim.bm25_search)
    s = e2.get(sid)
    i = s["current"]
    e2.submit(sid, i + 1, "Cross validation splits the data into folds.")
    leg = e2.get(sid)["answers"][i]["legacy"]
    assert leg["status"] == "unavailable" and "model files missing" in (leg["reason"] or "") and leg["score"] is None

"""Fixtures for Flask application tests.

The real Flask app (main/app.py), real AdaptiveInterviewSession, real routes and the real legacy question file are used.
Only two things are replaced, both at the process boundary:
  * the answer *scorer* (a deterministic fake with the same `.score(reference, answer) -> float in [0,1]` interface) because
    the real scorers need torch / a downloaded model / Java and are out of scope for routing tests; scoring ALGORITHMS are not
    exercised or changed here;
  * report persistence (so tests never write to results/reports).
"""
import importlib.util
import os
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


class FakeScorer:
    """Deterministic stand-in: fraction of answer tokens that occur in the reference answer."""
    calls = 0

    def score(self, reference_answer, user_answer):
        FakeScorer.calls += 1
        ref = set((reference_answer or "").lower().split())
        ans = (user_answer or "").lower().split()
        return 0.0 if not ans else min(1.0, sum(w in ref for w in ans) / len(ans))


def _load_app_module():
    if "smart_app" in sys.modules:
        return sys.modules["smart_app"]
    spec = importlib.util.spec_from_file_location("smart_app", ROOT / "main" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["smart_app"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def app_module():
    return _load_app_module()


@pytest.fixture()
def client(app_module, monkeypatch):
    import interview_session  # top-level module name used by main/app.py
    import llm_report
    import report_generator

    monkeypatch.setattr(interview_session, "get_scorer", lambda key, corpus=None: FakeScorer())
    monkeypatch.setattr(report_generator.ReportGenerator, "save_report", lambda self, report: None, raising=False)
    # Hermetic reports: llm_report reads OLLAMA_HOST once at import. A developer machine that runs Ollama (default 127.0.0.1:11434) made the
    # report job wait for a real model (up to 180 s), so the 10 s polling in the end-interview tests timed out. Port 9 (discard) refuses at once
    # and the rule-based fallback report is produced, exactly as in CI.
    monkeypatch.setattr(llm_report, "OLLAMA_BASE_URL", "http://127.0.0.1:9")
    app_module.sessions.clear()
    app_module.report_jobs.clear()
    random.seed(1234)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
    app_module.sessions.clear()
    app_module.report_jobs.clear()


@pytest.fixture()
def svc(tmp_path):
    """Curated retrieval service on the dev-lsa STAND-IN embedder (real MiniLM is not installable in CI/sandbox).
    Index/cache live in tmp_path so tests never touch data/retrieval."""
    from src.retrieval.service import RetrievalService, set_service
    s = RetrievalService(backend="dev-lsa", index_root=tmp_path / "idx", cache_dir=tmp_path / "cache")
    set_service(s)
    yield s
    set_service(None)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("SMART_QUESTION_SOURCE", "SMART_RETRIEVAL_ENABLED", "SMART_RETRIEVAL_EXPOSE_REFERENCE"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture(autouse=True)
def _hermetic_retrieval(monkeypatch, request):
    """10N Windows repair. An engine built WITHOUT its own ranking calls the process-wide retrieval service, which silently becomes Sentence-BERT + FAISS wherever those are installed (a Windows
    .bot environment). That orders the candidate questions differently from a machine without them (a different question makes a different memory the best match) and imports torch, so tests
    written against the BM25 ranking passed in the sandbox and failed on Windows. Unless a test installs its own stand-in service (set_service) or is marked `real_stack`, the engine's default
    ranking is BM25 only, which loads no model and orders the same everywhere."""
    if request.node.get_closest_marker("real_stack"):
        return
    for k in ("SMART_DEMO_MEMORY_SBERT", "SMART_DEMO_MEMORY_SEMANTIC_FLOOR"):        # a shell that exported these (the real-stack verify steps do) must not change what the memory tests rank with
        monkeypatch.delenv(k, raising=False)
    from src.demo import engine as E, sim
    from src.retrieval import service as S
    real = E._service_search
    installed = []                                                  # services a TEST put in place through set_service on purpose (the dev-lsa stand-in)

    real_set = S.set_service

    def set_service(svc):
        installed[:] = [svc] if svc is not None else []
        real_set(svc)
    monkeypatch.setattr(S, "set_service", set_service)

    def search(query, domain):
        # 10N final repair: whether a service is "installed" is decided by what the TEST installed, never by `S._service is not None`. That singleton is also filled lazily by any earlier call to
        # get_service() (it becomes Sentence-BERT + FAISS where those are installed), so on Windows a leftover default service sent this fixture to semantic ranking, depending on test order.
        if installed and S._service is installed[0]:
            return real(query, domain)
        return sim.bm25_search(query, domain)
    monkeypatch.setattr(E, "_service_search", search)

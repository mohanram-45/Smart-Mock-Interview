"""LIVE real-MiniLM checks through the real retrieval service and Flask routes. Skipped automatically where the model is not cached
(e.g. the sandbox); run on a machine that has all-MiniLM-L6-v2 cached:  python -m pytest tests/app/test_real_minilm_flask.py -v"""
import pytest

BUBBLE, QUICK = "smi-0453", "smi-0452"


def _model_available():
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)
        import faiss  # noqa: F401
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _model_available(), reason="real all-MiniLM-L6-v2 / faiss not available offline")


@pytest.fixture()
def real_svc(tmp_path):
    from src.retrieval.service import RetrievalService, set_service
    s = RetrievalService(backend="minilm", local_files_only=True, index_root=tmp_path / "i", cache_dir=tmp_path / "c")
    set_service(s)
    yield s
    set_service(None)


@pytest.fixture()
def enabled(monkeypatch):
    monkeypatch.setenv("SMART_RETRIEVAL_ENABLED", "1")


def test_paraphrase_finds_bubble_sort_then_quicksort_nearby(client, real_svc, enabled):
    d = client.post("/api/retrieval/search", json={"query": "Explain how bubble sort works and why it is considered slow.", "k": 5}).get_json()
    ids = [h["question_id"] for h in d["results"]]
    assert d["mode"] == "semantic" and ids[0] == BUBBLE and QUICK in ids[:3]


def test_related_knowledge_for_the_bubble_sort_question_is_topical(client, real_svc, enabled):
    q = real_svc.get(BUBBLE)["question"]
    d = client.post("/api/retrieval/search", json={"query": q, "k": 6}).get_json()
    others = [h for h in d["results"] if h["question_id"] != BUBBLE]
    assert d["results"][0]["question_id"] == BUBBLE                                # self is the best match (excluded by session-context)
    assert QUICK in [h["question_id"] for h in others[:5]]
    assert all(h["domain"] == "Python" for h in others[:4])


def test_selected_format_is_active_and_loaded_once(client, real_svc, enabled):
    for _ in range(5):
        client.post("/api/retrieval/search", json={"query": "what is overfitting", "k": 3})
    st = client.get("/api/retrieval/status").get_json()
    assert st["doc_mode"] == "qk_concise" and st["mode"] == "semantic" and st["semantic_loads"] == 1


def test_domain_and_difficulty_filters_and_metadata(client, real_svc, enabled):
    d = client.post("/api/retrieval/search", json={"query": "explain joins", "k": 5, "domain": "SQL", "difficulty": "Medium"}).get_json()
    assert d["results"] and all(h["domain"] == "SQL" and h["difficulty"] == "Medium" and h["topic"] and h["question_id"].startswith("smi-") for h in d["results"])


def test_off_topic_query_scores_low_and_explicit_threshold_flags_no_answer(client, real_svc, enabled):
    q = "How do I prepare a sourdough starter?"
    base = client.post("/api/retrieval/search", json={"query": q, "k": 3}).get_json()
    assert base["results"][0]["score"] < 0.45                                       # recorded off-topic top-1 scores are well below answerable ones
    hi = client.post("/api/retrieval/search", json={"query": q, "k": 3, "min_score": 0.6}).get_json()
    assert hi["no_answer"] is True and hi["threshold"]["applied"] is True

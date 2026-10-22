"""Characterisation of the CURRENT (legacy) application behaviour. Written and run BEFORE any integration change.
These document what the app does today — including defects — so that the integration can be shown not to alter it."""
import json
from pathlib import Path

import pytest

from tests.app.scenario import run

HERE = Path(__file__).parent
GOLDEN = HERE / "golden" / "legacy_baseline.json"
LEGACY_JSON = HERE.parents[1] / "data" / "processed" / "questions_cleaned.json"


def _start(client, **body):
    r = client.post("/api/start-interview", json=body)
    return r, r.get_json()


def test_health_and_index(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    idx = client.get("/").get_json()
    assert idx["version"] == "2.0.0" and "POST /api/start-interview" in idx["key_endpoints"]


def test_roles_domains_models_shapes(client):
    roles = client.get("/api/roles").get_json()
    assert set(roles["roles"]) == {"Data Scientist", "Machine Learning Engineer", "NLP Engineer", "Data Analyst", "Python Developer", "Custom Interview"}
    assert roles["role_mappings"]["Machine Learning Engineer"] == ["ML", "DL", "Python"]
    assert client.get("/api/domains").get_json()["domains"] == ["DATA_ANALYSIS", "DL", "ML", "NLP", "Python"]
    m = client.get("/api/models").get_json()
    assert m["default"] == "bilstm" and {x["key"] for x in m["models"]} == {"bilstm", "bert", "tfidf"}


def test_start_interview_response_contract(client):
    r, d = _start(client, role="Python Developer")
    assert r.status_code == 200
    assert set(d) == {"session_id", "role", "selected_domains", "model", "started_at", "current_round", "current_question"}
    assert d["model"] == {"key": "bilstm", "label": "Siamese Bi-LSTM"}
    assert d["current_round"] == "Easy" and d["selected_domains"] == ["Python"]
    assert set(d["current_question"]) == {"question_id", "question", "question_number", "total_in_round"}
    assert isinstance(d["current_question"]["question_id"], int)          # legacy ids are ints
    assert d["current_question"]["question_number"] == 1 and d["current_question"]["total_in_round"] == 5  # FIXED_EASY_COUNT


@pytest.mark.parametrize("body,code,msg", [
    ({"role": "Wizard"}, 400, "Invalid role: Wizard"),
    ({"role": "Python Developer", "model": "gpt"}, 400, "Invalid model: gpt"),
    ({"role": "Custom Interview"}, 400, "No domains selected for role: Custom Interview"),
    ({"role": "Custom Interview", "custom_domains": ["Nope"]}, 400, "Failed to load questions for selected domains"),
])
def test_start_interview_errors(client, body, code, msg):
    r, d = _start(client, **body)
    assert r.status_code == code and d == {"error": msg}


def test_start_without_json_body_is_500_today(client):
    """DOCUMENTED CURRENT BEHAVIOUR: a POST without a JSON content-type raises 415 inside the route's blanket except -> 500."""
    r = client.post("/api/start-interview")
    assert r.status_code == 500 and "error" in r.get_json()


def test_start_empty_json_defaults_to_custom_interview_and_fails(client):
    r = client.post("/api/start-interview", json={})
    assert r.status_code == 400 and "No domains" in r.get_json()["error"]


def test_known_defect_role_domain_codes_do_not_match_question_file_labels(client):
    """DOCUMENTED CURRENT BEHAVIOUR (pre-existing, not introduced by Stage 2C): ROLE_MAPPING uses 'ML','DL','DATA_ANALYSIS'
    but data/processed/questions_cleaned.json labels are 'Machine Learning','Deep Learning','Data Analysis'. So roles only
    receive questions from domains whose labels happen to match ('Python','NLP')."""
    pool = json.loads(LEGACY_JSON.read_text(encoding="utf-8"))
    labels = {q["domain"] for q in pool}
    assert {"ML", "DL", "DATA_ANALYSIS"}.isdisjoint(labels) and {"Machine Learning", "Deep Learning", "Data Analysis"} <= labels
    for role, expect in (("Machine Learning Engineer", {"Python"}), ("Data Scientist", {"NLP", "Python"}), ("Data Analyst", {"Python"})):
        r, d = _start(client, role=role)
        assert r.status_code == 200
        import smart_app
        s = smart_app.sessions[d["session_id"]]
        assert {q["domain"] for q in s.all_questions} == expect, role


def test_custom_interview_with_canonical_labels_works(client):
    r, d = _start(client, role="Custom Interview", custom_domains=["Machine Learning", "SQL"])
    assert r.status_code == 200 and d["selected_domains"] == ["Machine Learning", "SQL"]


def test_session_flow_fixed_engine(client):
    r, d = _start(client, role="Python Developer")
    sid = d["session_id"]
    q1 = client.get(f"/api/current-question?session_id={sid}").get_json()
    assert q1["question_id"] == d["current_question"]["question_id"] and q1["current_round"] == "Easy"
    assert client.get(f"/api/repeat-question?session_id={sid}").get_json() == {"question_id": q1["question_id"], "question": q1["question"]}
    a = client.post("/api/submit-answer", json={"session_id": sid, "answer": "some answer"}).get_json()
    assert set(a) >= {"similarity_score", "feedback", "question_completed", "round_complete", "round_action"}
    assert a["round_action"] == "continue" and a["round_complete"] is False
    nxt = client.post("/api/next-question", json={"session_id": sid}).get_json()
    assert nxt["question_number"] == 2 and nxt["question_id"] != q1["question_id"]
    sk = client.post("/api/skip-question", json={"session_id": sid}).get_json()
    assert sk["skipped"] is True and sk["consecutive_skips"] == 1 and sk["force_end"] is False
    st = client.get(f"/api/session-status?session_id={sid}").get_json()
    assert "current_question" not in st and st["total_questions_answered"] == 2 and st["model_choice"] == "bilstm"


def test_no_repeated_questions_within_session(client):
    import smart_app
    r, d = _start(client, role="Custom Interview", custom_domains=["Python"])
    s = smart_app.sessions[d["session_id"]]
    ids = [q["id"] for rnd in s.round_questions.values() for q in rnd]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/current-question?session_id=x", None), ("get", "/api/repeat-question?session_id=x", None),
    ("get", "/api/session-status?session_id=x", None), ("post", "/api/next-question", {"session_id": "x"}),
    ("post", "/api/skip-question", {"session_id": "x"}), ("post", "/api/check-round-completion", {"session_id": "x"}),
    ("post", "/api/submit-answer", {"session_id": "x", "answer": "a"}),
])
def test_invalid_session_everywhere(client, method, path, body):
    r = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    assert r.status_code == 400 and r.get_json() == {"error": "Invalid session"}


def test_empty_answer_rejected(client):
    r, d = _start(client, role="Python Developer")
    r = client.post("/api/submit-answer", json={"session_id": d["session_id"], "answer": "  "})
    assert r.status_code == 400 and r.get_json() == {"error": "Answer cannot be empty"}


def test_unknown_route_json_404(client):
    r = client.get("/nope")
    assert r.status_code == 404 and r.get_json() == {"error": "Endpoint not found"}


def test_end_interview_is_async(client):
    import time
    r, d = _start(client, role="Python Developer")
    sid = d["session_id"]
    client.post("/api/submit-answer", json={"session_id": sid, "answer": "x y z"})
    e = client.post("/api/end-interview", json={"session_id": sid})
    assert e.status_code == 202 and e.get_json()["status"] == "processing"
    for _ in range(100):
        s = client.get(f"/api/reports/{sid}/status")
        if s.status_code != 202:
            break
        time.sleep(0.1)
    assert s.status_code in (200, 500)   # 500 only if report generation itself fails in this environment


def test_golden_baseline_matches_live_legacy_behaviour(client):
    """The scripted scenario's every response must equal the baseline recorded from the unmodified app."""
    assert GOLDEN.exists(), "golden baseline missing - record it with the unmodified app first"
    base = json.loads(GOLDEN.read_text(encoding="utf-8"))
    live = [[lbl, code, js] for lbl, code, js in run(client)]
    assert live == base

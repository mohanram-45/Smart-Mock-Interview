"""Stage 9A: the product layer around the interview (dashboard, history, settings, timing, honest aggregates, access rule for the history list).

Real Flask app, real curated corpus, the stand-in word-overlap scorer used by the other demo tests. Browser behaviour is covered in tests/ui."""
import random
import re
import time
from pathlib import Path

import pytest

from src.demo import insights as INS
from src.demo.engine import DemoEngine
from src.demo.routes import set_engine
from src.demo.store import DemoStore

ROOT = Path(__file__).resolve().parents[2]
CANARY = "canary-9a-5c2e-private-answer"


class Overlap:
    def score(self, ref, ans):
        r, a = set(ref.lower().split()), ans.lower().split()
        return 0.0 if not a else min(1.0, sum(w in r for w in a) / len(a))


def make_engine(tmp_path):
    return DemoEngine(DemoStore(tmp_path / "sessions"), scorer_factory=lambda k, c: Overlap(), feedback_fn=lambda s, q, a, m: "standard comment", rng=random.Random(4))


@pytest.fixture()
def eng(tmp_path, monkeypatch):
    for v in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_HISTORY", "SMART_RETRIEVAL_EXPOSE_REFERENCE"):
        monkeypatch.delenv(v, raising=False)
    e = make_engine(tmp_path)
    set_engine(e)
    yield e
    set_engine(None)


@pytest.fixture()
def c(app_module, eng):
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as cl:
        yield cl


def run_interview(c, text="Overfitting means memorising noise in the training data.", size=3, skip=()):
    """A bare interview (no practical, no follow-ups): the introduction is answered first; `skip` and the loop use technical-question numbers (item n + 1)."""
    sid = start_bare(c, size=size)
    for n in range(1, size + 1):
        r = c.post(f"/demo/api/sessions/{sid}/skip" if n in skip else f"/demo/api/sessions/{sid}/answer", json={"n": n + 1, "answer": text})
        assert r.status_code == 200
    return sid


def start_bare(c, size=3, intro=True, **over):
    sid = c.post("/demo/api/sessions", json={"role": "Python Developer", "size": size, "practical": False, "max_followups": 0, **over}).json["session_id"]
    if intro:
        assert c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "Hello, I am a candidate."}).status_code == 200
    return sid


# ---------------------------------------------------------------------------------------------------------------- insights (pure)
def _session(scores, domains=None, status="finished", elapsed=60, skipped=()):
    qs = [{"question_id": f"q{i}", "domain": (domains or ["Python"] * len(scores))[i], "difficulty": "Medium", "topic": f"topic {i}", "question": f"question text {i}"} for i in range(len(scores))]
    ans = []
    for i, sc in enumerate(scores):
        if sc is None:
            ans.append(None)
        elif i in skipped:
            ans.append({"n": i + 1, "skipped": True, "answer": "", "elapsed_s": 5, "legacy": {"status": "skipped", "score": None}, "modular": {"status": "not_requested", "view": None}})
        else:
            ans.append({"n": i + 1, "skipped": False, "answer": f"secret answer {CANARY}", "elapsed_s": elapsed, "legacy": {"status": "scored", "score": sc}, "modular": {"status": "not_requested", "view": None}})
    return {"id": f"demo_{'%020x' % random.randrange(16**20)}", "created_at": "2026-10-01T10:00:00+00:00", "finished_at": "2026-10-01T10:20:00+00:00", "status": status,
            "config": {"role": "Python Developer", "domains": ["Python"], "difficulty": "Medium", "modular_mode": "off"}, "questions": qs, "answers": ans}


def test_digest_has_numbers_not_text():
    d = INS.digest(_session([40.0, 60.0, 80.0]))
    assert d["legacy_average"] == 60.0 and d["answered"] == 3 and d["seconds"] == 180
    assert CANARY not in repr(INS.public_digest(d)) and "question text" not in repr(d)


def test_time_per_question_is_capped_and_skips_are_not_counted_as_work():
    assert INS.capped_seconds({"elapsed_s": 99999}) == INS.ELAPSED_CAP_S
    assert INS.capped_seconds({"elapsed_s": None}) is None and INS.capped_seconds({}) is None and INS.capped_seconds({"elapsed_s": -3}) is None
    d = INS.digest(_session([50.0, 0.0, 70.0], skipped=(1,)))
    assert d["answered"] == 2 and d["skipped"] == 1 and d["timed_answers"] == 2 and d["seconds"] == 120      # the skipped question's 5 s is not practice time


def test_overview_empty_has_no_invented_numbers():
    o = INS.overview([])
    assert o["interviews"] == 0 and o["legacy_average"] is None and o["trend"] == [] and o["trend_ready"] is False and o["domains"] == [] and o["minutes"] is None


def test_trend_needs_two_finished_interviews_and_domain_order_is_lowest_first():
    one = INS.digest(_session([50.0, 70.0], ["Python", "NLP"]))
    assert INS.overview([one])["trend_ready"] is False
    two = INS.digest(_session([100.0], ["Python"]))
    two["created_at"] = "2026-10-02T10:00:00+00:00"
    o = INS.overview([one, two])
    assert o["trend_ready"] is True and [round(p["value"]) for p in o["trend"]] == [60, 100]
    assert [d["domain"] for d in o["domains"]] == ["NLP", "Python"] and o["domains"][0]["average"] == 70.0 and o["domains"][1]["average"] == 75.0


def test_unfinished_interview_is_not_in_the_trend():
    ds = [INS.digest(_session([50.0])), INS.digest(_session([60.0], status="active"))]
    assert len(INS.overview(ds)["trend"]) == 1


def test_trend_geometry_axis_is_fixed_0_to_100():
    """The axis still spans the full stored range 0-100; Stage 12 labels it 0-1 so it is not read as a percentage correct."""
    g = INS.trend_geometry([{"value": 0}, {"value": 100}, {"value": 50}])
    ys = [p["y"] for p in g["points"]]
    assert ys[0] > ys[2] > ys[1] and [x["label"] for x in g["grid"]] == ["0.00", "0.25", "0.50", "0.75", "1.00"]


def test_concept_findings_only_when_the_evaluator_produced_verdicts():
    assert INS.concept_findings(None) is None and INS.concept_findings({"verdicts": []}) is None
    v = {"verdicts": [{"member": "A", "final_state": "states_correctly"}, {"member": "B", "final_state": "not_stated"}, {"member": "C", "final_state": "states_incorrectly"}, {"member": "D", "final_state": "unverified"}]}
    assert INS.concept_findings(v) == {"stated": ["A"], "wrong": ["C"], "not_found": ["B"], "undecided": ["D"]}


def test_improvement_areas_are_derived_and_experimental_stays_separate():
    s = _session([30.0, 90.0, 60.0, None])
    kinds = [a["source"] for a in INS.improvement_areas(s)]
    assert kinds == ["legacy", "session"]                                  # no experimental/code entries without experimental data
    s["answers"][0]["modular"] = {"status": "done", "view": {"verdicts": [{"member": "Big-O", "final_state": "not_stated"}]}}
    areas = INS.improvement_areas(s)
    exp = [a for a in areas if a["source"] == "experimental"]
    assert exp and "Big-O" in exp[0]["items"][0]["detail"]
    assert INS.improvement_areas(_session([55.0])) == []                    # one scored answer, nothing skipped: nothing to say


# ---------------------------------------------------------------------------------------------------------------- engine timing
def test_elapsed_time_is_recorded_per_answer_and_survives_reload(c, eng):
    sid = c.post("/demo/api/sessions", json={"role": "Python Developer", "difficulty": "Medium", "size": 3}).json["session_id"]
    s = eng.get(sid)
    assert s["q_started"]
    time.sleep(1.1)
    c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "some answer text here"})
    s = eng.get(sid)
    assert s["answers"][0]["elapsed_s"] >= 1
    first_start = s["q_started"]
    c.post(f"/demo/api/sessions/{sid}/skip", json={"n": 2})
    s = eng.get(sid)
    assert s["answers"][1]["elapsed_s"] is not None and s["q_started"] >= first_start
    eng.store.clear()                                                       # simulate a restart: reload from disk
    assert eng.get(sid)["answers"][0]["elapsed_s"] >= 1


def test_session_saved_before_timing_existed_still_works(eng):
    assert DemoEngine.question_elapsed({"status": "active"}) is None and DemoEngine.question_elapsed({"q_started": "garbage"}) is None


def test_interview_page_exposes_elapsed_and_the_conversation(c):
    sid = start_bare(c, intro=False)
    html = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    assert 'id="t-q"' in html and "data-elapsed=" in html and 'id="thread"' in html and "Introduction" in html
    c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "some answer text"})
    html = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    assert "some answer text" in html and "Technical question" in html          # the thread keeps what was said


# ---------------------------------------------------------------------------------------------------------------- pages and history access
def test_dashboard_history_settings_render_empty_and_with_data(c):
    for path, text in (("/demo/", "No interviews yet"), ("/demo/history", "No interviews saved"), ("/demo/settings", "Evaluation methods")):
        r = c.get(path)
        assert r.status_code == 200 and text in r.get_data(as_text=True)
    sid = run_interview(c)
    html = c.get("/demo/").get_data(as_text=True)
    assert "Interviews finished" in html and f"/demo/s/{sid}/summary" in html and "Where you are" in html
    run_interview(c)
    home, hist = c.get("/demo/").get_data(as_text=True), c.get("/demo/history").get_data(as_text=True)
    # Stage 9A.3: the home page shows counts only. Similarity (average, trend, per-topic) lives on History, with its labels, and the data is unchanged.
    for gone in ("Average similarity", 'class="trend"', "Similarity by", "similarity avg"):
        assert gone not in home, gone
    assert 'class="trend"' in hist and "Similarity by topic" in hist and "Similarity avg" in hist and "not a technical grade" in hist


def test_history_trend_needs_two_finished_interviews(c):
    run_interview(c)
    html = c.get("/demo/history").get_data(as_text=True)
    assert "Not enough data for a trend yet" in html and 'class="trend"' not in html


def test_home_has_quick_start_cards_that_fall_back_to_the_setup_page(c):
    html = c.get("/demo/").get_data(as_text=True)
    assert 'data-start-role="' in html and 'href="/demo/new?role=' in html and 'id="mainnav"' in html and 'class="hero2"' in html
    assert "Sentence-BERT" in html and "not a technical grade" in html and "secondary" in html     # similarity stays labelled and secondary


def test_new_interview_page_is_still_the_setup_form(c):
    html = c.get("/demo/new").get_data(as_text=True)
    assert 'id="setup-form"' in html and "Your interview" in html and 'id="jd"' in html and 'id="start-btn"' in html
    for gone in ("legacy-model", "difficulty", "Siamese", "TF-IDF"):
        assert gone not in html, gone


def test_history_is_served_only_to_this_computer_by_default(c, app_module, eng, monkeypatch):
    sid = run_interview(c)
    assert c.get("/demo/api/history").status_code == 200
    remote = {"REMOTE_ADDR": "203.0.113.9"}
    r = c.get("/demo/api/history", environ_overrides=remote)
    assert r.status_code == 403
    assert "not shown to this client" in c.get("/demo/history", environ_overrides=remote).get_data(as_text=True)
    assert "not shown to this client" in c.get("/demo/", environ_overrides=remote).get_data(as_text=True)
    assert c.post("/demo/api/sessions/delete-all", json={}, environ_overrides=remote).status_code == 403
    assert eng.get(sid) is not None
    # a single interview is still reachable from its own unguessable link
    assert c.get(f"/demo/s/{sid}/summary", environ_overrides=remote).status_code == 200
    monkeypatch.setenv("SMART_DEMO_HISTORY", "1")
    assert c.get("/demo/api/history", environ_overrides=remote).status_code == 200
    monkeypatch.setenv("SMART_DEMO_HISTORY", "0")
    assert c.get("/demo/api/history").status_code == 403


def test_history_json_never_contains_answers_or_questions(c):
    run_interview(c, text=f"my private answer {CANARY}")
    raw = c.get("/demo/api/history").get_data(as_text=True)
    assert CANARY not in raw and "question" not in raw and "legacy_scores" not in raw and "by_domain" not in raw
    dash = c.get("/demo/").get_data(as_text=True)
    assert CANARY not in dash and CANARY not in c.get("/demo/history").get_data(as_text=True)


def test_delete_all_removes_files_and_memory(c, eng):
    run_interview(c)
    run_interview(c)
    assert len(list(eng.store.dir.glob("demo_*.json"))) == 2
    assert c.post("/demo/api/sessions/delete-all", json={}).json["deleted"] == 2
    assert list(eng.store.dir.glob("demo_*.json")) == [] and c.get("/demo/api/history").json["overview"]["interviews"] == 0


def test_settings_reports_real_state_and_never_offers_to_enable_experiments(c, monkeypatch):
    html = c.get("/demo/settings").get_data(as_text=True)
    assert "Local model (Ollama" in html and "run_demo.bat --live-model" in html and "off." in html
    assert "nothing is ever executed inside the web server" in html
    monkeypatch.setenv("SMART_DEMO_LIVE_MODULAR", "1")
    assert "turned on for this server" in c.get("/demo/settings").get_data(as_text=True)


def test_summary_has_metrics_areas_and_time(c):
    sid = run_interview(c, skip=(2,))
    html = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    for needle in ("Technical questions answered", "Time spent", "Areas for future practice", "turn by turn", "Skipped or not reached"):
        assert needle in html


def test_legacy_only_feedback_does_not_invent_strengths(c):
    sid = start_bare(c)
    frag = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 2, "answer": "words words words"}).json["html"]
    assert "No strengths or missing concepts are listed" in frag and "Stated in your answer" not in frag


def test_mock_evaluation_lists_concepts_only_inside_the_experimental_panel(c):
    sid = start_bare(c, modular_mode="mock")
    c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 2, "answer": "A decorator wraps a function and returns a new function."})
    frag = c.get(f"/demo/api/sessions/{sid}/answers/2").json["html"]
    legacy, _, experimental = frag.partition("panel-modular")
    assert "Stated in your answer" not in legacy and "MOCK VERIFIER" in experimental

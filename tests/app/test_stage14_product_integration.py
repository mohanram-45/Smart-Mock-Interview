"""Stage 14: /demo as one product. Setup (with interview length) -> interview -> answer evaluation -> summary -> PDF report, plus history, skip, resume and export.
Deterministic: no model, no network (the similarity scorer is the test double used by the other demo tests)."""
import re
from pathlib import Path

import pytest

from src.demo import pdf_report
from src.demo.routes import set_engine
from src.security import local_guard as G
from tests.app.test_stage4a_demo import make_engine
from tests.app.test_stage12_answer_assessment import CORE, CXI, E_MISS, E_OK, stored

ROOT = Path(__file__).resolve().parents[2]
GOOD = "Gradient descent moves the weights against the gradient of the loss, with a learning rate setting the step."


@pytest.fixture()
def env(app_module, tmp_path, monkeypatch):
    for k in ("SMART_DEMO_LIVE_MODULAR", "SMART_RETRIEVAL_EXPOSE_REFERENCE"):
        monkeypatch.delenv(k, raising=False)
    e = make_engine(tmp_path)
    set_engine(e)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c, e, tmp_path
    set_engine(None)


def run_interview(c, **over):
    body = {"role": "Data Scientist", "size": 3, "practical": False, "max_followups": 0}
    body.update(over)
    r = c.post("/demo/api/sessions", json=body)
    assert r.status_code == 201, r.json
    sid = r.json["session_id"]
    n, skipped = 1, False
    for _ in range(20):
        st = c.get(f"/demo/api/sessions/{sid}").json
        if st["status"] == "finished":
            break
        n = st["current"]
        q = st["question"]
        if q["stage"] == "core" and not skipped:
            assert c.post(f"/demo/api/sessions/{sid}/skip", json={"n": n}).status_code == 200      # one skip on the way
            skipped = True
        else:
            assert c.post(f"/demo/api/sessions/{sid}/answer", json={"n": n, "answer": GOOD if q["stage"] != "introduction" else "Hello, I am a candidate."}).status_code == 200
    else:
        c.post(f"/demo/api/sessions/{sid}/finish")
    c.post(f"/demo/api/sessions/{sid}/finish")
    return sid


# ---- /demo is the front door ---------------------------------------------------------------------------------------------------------------------------
def test_browsers_are_sent_to_demo_and_api_clients_keep_the_json_description(app_module):
    with app_module.app.test_client() as c:
        r = c.get("/", headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
        assert r.status_code == 302 and r.headers["Location"].endswith("/demo/")
        j = c.get("/")                                                                  # no Accept header: unchanged legacy behaviour
        assert j.status_code == 200 and "key_endpoints" in j.json
        assert c.get("/", headers={"Accept": "*/*"}).status_code == 200
        assert c.get("/api/roles").status_code == 200                                    # legacy API untouched
        assert c.get("/demo/").status_code == 200


# ---- interview length ----------------------------------------------------------------------------------------------------------------------------------
def test_setup_page_offers_the_interview_length_and_posts_it(env):
    c, _, _ = env
    page = c.get("/demo/new").data.decode()
    radios = re.findall(r'<input type="radio" name="time_budget_min" value="(\d+)"( checked)?', page)
    assert [v for v, _ in radios] == ["15", "30", "45", "60"] and [v for v, ch in radios if ch] == ["45"]
    assert "How long should it take?" in page and "not a hard timer" in page
    js = (ROOT / "src/demo/static/demo.js").read_text(encoding="utf-8")
    assert "input[name=time_budget_min]:checked" in js and "body.time_budget_min" in js


def test_chosen_length_reaches_the_plan_and_bad_values_are_refused(env):
    c, e, _ = env
    sid = c.post("/demo/api/sessions", json={"role": "Data Scientist", "time_budget_min": 15}).json["session_id"]
    assert e.get(sid)["plan"]["time_budget_s"] == 900
    sid = c.post("/demo/api/sessions", json={"role": "Data Scientist"}).json["session_id"]
    assert e.get(sid)["plan"]["time_budget_s"] == 45 * 60
    for bad in (0, 241, "15", 1.5, True):
        assert c.post("/demo/api/sessions", json={"role": "Data Scientist", "time_budget_min": bad}).status_code == 400


# ---- the whole journey ---------------------------------------------------------------------------------------------------------------------------------
def test_journey_setup_to_pdf_with_skip_history_export_and_resume(env, monkeypatch):
    from reportlab import rl_config
    monkeypatch.setattr(rl_config, "pageCompression", 0)                               # readable PDF text for the assertions
    c, e, tmp = env
    assert c.get("/demo/new").status_code == 200
    sid = run_interview(c, time_budget_min=30)
    page = c.get(f"/demo/s/{sid}/summary").data.decode()
    assert 'id="pdf-btn"' in page and f"/demo/s/{sid}/report.pdf" in page and "Download PDF report" in page and "Correctness check" in page
    r = c.get(f"/demo/s/{sid}/report.pdf")
    assert r.status_code == 200 and r.mimetype == "application/pdf" and r.data.startswith(b"%PDF") and "attachment" in r.headers["Content-Disposition"]
    assert "Interview_Report.pdf" in r.headers["Content-Disposition"]
    # Final polish: with the correctness check OFF the PDF carries ONE concise notice instead of a "Not assessed" card per answer, and never "0/0 judged correct".
    assert b"Correctness not assessed" in r.data and b"not a grade" in r.data
    assert b"CORRECTNESS FEEDBACK" not in r.data and b"Not assessed" not in r.data and b"judged correct" not in r.data and b"0 / 0" not in r.data and b"0/0" not in r.data
    assert not re.search(rb"\d+\.\d%", r.data) and b"Overall score" not in r.data              # no similarity percentage presented as a score
    assert sid in c.get("/demo/history").data.decode()
    exp = c.get(f"/demo/s/{sid}/export.json").json
    assert exp["status"] == "finished" and any(x.get("skipped") for x in exp["answers"])
    # resume: a brand-new engine over the same folder still serves the interview, its summary and its PDF
    e2 = make_engine(tmp)
    set_engine(e2)
    assert c.get(f"/demo/s/{sid}/summary").status_code == 200
    assert c.get(f"/demo/s/{sid}/report.pdf").data.startswith(b"%PDF")


def test_pdf_is_refused_until_the_interview_is_finished_and_for_unknown_ids(env):
    c, _, _ = env
    sid = c.post("/demo/api/sessions", json={"role": "Data Scientist"}).json["session_id"]
    assert c.get(f"/demo/s/{sid}/report.pdf").status_code == 409
    assert c.get("/demo/s/nope/report.pdf").status_code in (400, 404)


def test_pdf_carries_the_stage12_correctness_feedback(env, monkeypatch):
    from reportlab import rl_config

    from report_delivery.pdf_generator import build_pdf
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    c, e, _ = env
    s = e.create({"role": "Data Scientist", "size": 3, "practical": False, "max_followups": 0})
    qs = s["questions"]
    cores = [i for i, q in enumerate(qs) if q.get("stage") == "core"]
    s["answers"] = [None] * len(qs)
    s["answers"][cores[0]] = stored([E_OK], sim=91.0, answer="A correct and complete answer.")
    s["answers"][cores[1]] = stored([E_OK, E_MISS], cx=CXI, sim=88.0, answer="A confident answer with one false claim.")
    s["answers"][cores[2]] = {"answer": "", "skipped": True, "legacy": {"status": "skipped"}, "modular": {"mode": "off", "status": "not_requested"}}
    s["status"] = "finished"
    report = pdf_report.build(s, e.summary(s))
    labels = [i["label"] for i in report["correctness"]["items"]]
    assert labels[1] == "Partially correct" or labels[1] == "Incorrect"
    assert report["correctness"]["items"][1]["misconceptions"][0]["claim"] == "a false statement"
    pdf = build_pdf(report)
    assert b"CORRECTNESS FEEDBACK" in pdf and b"Check this statement" in pdf and b"a false statement" in pdf and b"the truth" in pdf
    assert b"Similarity to the reference answer: 0.88" in pdf and rb"Avg similarity \(0-1\)" in pdf
    assert not re.search(rb"\d+\.\d%", pdf)


def test_legacy_pdf_layout_is_unchanged_without_correctness(monkeypatch):
    from reportlab import rl_config

    from report_delivery.pdf_generator import build_pdf
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    pdf = build_pdf({"interview_role": "Python Developer", "average_score": 72.5, "questions_answered": 4, "questions_skipped": 1, "scoring_model": "BERT",
                     "analysis": {"performance_label": "Good", "recommendations": ["Practise decorators."], "learning_plan": [{"phase": "Week 1", "focus": "Basics", "actions": ["Read"]}]}})
    assert b"72.5%" in pdf and b"Overall score" in pdf and b"PERSONALIZED LEARNING PLAN" in pdf and b"RECOMMENDATIONS" in pdf and b"CORRECTNESS FEEDBACK" not in pdf


# ---- Docker peer handling ------------------------------------------------------------------------------------------------------------------------------
def test_docker_peer_trust_is_exact_and_opt_in(monkeypatch):
    route = "Iface\tDestination\tGateway\tFlags\neth0\t00000000\t010011AC\t0003\neth0\t000011AC\t00000000\t0001\n"        # default gateway 172.17.0.1
    assert G._gateway_from_route(route) == "172.17.0.1" and G._gateway_from_route("Iface\tDestination\n") is None and G._gateway_from_route("") is None
    for k in ("SMART_TRUSTED_PEERS", "SMART_TRUST_DOCKER_GATEWAY"):
        monkeypatch.delenv(k, raising=False)
    assert G.is_loopback("127.0.0.1") and not G.is_loopback("172.17.0.1") and G.trusted_peers(route) == set()
    monkeypatch.setenv("SMART_TRUST_DOCKER_GATEWAY", "1")
    assert G.trusted_peers(route) == {"172.17.0.1"}
    monkeypatch.setattr(G, "docker_gateway", lambda: "172.17.0.1")
    assert G.is_loopback("172.17.0.1")
    for other in ("172.17.0.2", "172.17.0.3", "10.0.0.5", "192.168.1.20", "203.0.113.5", "0.0.0.0", "172.17.0.1.5", "", "junk"):
        assert not G.is_loopback(other), other
    monkeypatch.setenv("SMART_TRUSTED_PEERS", "192.168.1.20, bad, 0.0.0.0, 10.0.0.0/8")
    assert G.is_loopback("192.168.1.20") and not G.is_loopback("192.168.1.21") and not G.is_loopback("10.0.0.7")


def test_docker_files_use_the_narrow_setting_not_a_private_network_wildcard():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8") + (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "SMART_TRUST_DOCKER_GATEWAY" in text and "SMART_ALLOW_PRIVATE_PEERS" not in text


# ---- ML-enabled Docker verification tooling (the real run needs Docker + the model; see scripts/verify_ml_scoring.py) ---------------------------------------
def test_ml_scoring_check_separates_a_real_embedding_from_a_fake_one():
    import importlib.util as iu
    spec = iu.spec_from_file_location("verify_ml_scoring", ROOT / "scripts" / "verify_ml_scoring.py")
    m = iu.module_from_spec(spec)
    spec.loader.exec_module(m)
    corpus = m.load_corpus()
    assert len(corpus) > 50 and len({q["domain"] for q in corpus}) > 1
    constant = lambda ref, ans: 0.5                                                       # noqa: E731  a broken scorer that returns the same value for everything
    assert not all(ok for _, _, ok in m.check_pairs(constant, corpus))

    def toy(ref, ans):                                                                    # word-overlap stand-in with the right shape: identical 1, fragment mid, unrelated ~0
        x, y = set(ref.lower().split()), set(ans.lower().split())
        return 1.0 if ref == ans else (len(y & x) / max(1, len(y)) if len(y) < len(x) / 2 else len(x & y) / max(1, len(x | y)))
    rows = {name: ok for name, _, ok in m.check_pairs(toy, corpus)}
    assert rows["identical text"] and rows["unrelated sentence is low"] and rows["the reference's own first sentence is clearly above unrelated"]


def test_docker_files_ship_and_document_the_ml_verification():
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "scripts/verify_ml_scoring.py" in docker
    bat = (ROOT / "verify_docker_ml.bat").read_text(encoding="utf-8")
    assert "INSTALL_ML" in bat and "verify_ml_scoring.py" in bat and "healthcheck.py --ready" in bat
    assert (ROOT / "scripts" / "verify_ml_scoring.py").read_text(encoding="utf-8").count("PASS") >= 1

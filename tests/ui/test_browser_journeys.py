"""Real-browser journeys (Playwright + Chromium) against the real Flask app, real curated question bank and real session store.

The server is started as a subprocess by tests/ui/browser_server.py. Only the Sentence-BERT similarity scorer is a labelled word-overlap stand-in (torch and model files are not
needed). Skipped when Playwright or a Chromium build is not available. Set SMART_UI_SHOTS=<dir> to also save screenshots; SMART_UI_PYTHON=<python> runs the server with another interpreter.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[2]
SHOTS = os.environ.get("SMART_UI_SHOTS")
CANARY = "zx-canary-7f3a91-do-not-log"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _spawn(tmp_path_factory, extra_env):
    port, data = free_port(), tmp_path_factory.mktemp("ui_sessions")
    log = tmp_path_factory.mktemp("ui_log") / "server.log"
    env = {**os.environ, "SMART_DEMO_CODE_EVAL": "1", **extra_env}
    if "SMART_DEMO_LIVE_MODULAR" not in extra_env:
        env.pop("SMART_DEMO_LIVE_MODULAR", None)
    fh = open(log, "wb")
    proc = subprocess.Popen([os.environ.get("SMART_UI_PYTHON", sys.executable), str(ROOT / "tests" / "ui" / "browser_server.py"), str(port), str(data)], cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            return proc, fh, {"base": base, "demo": base + "/demo", "log": log, "data": data}
        except Exception:
            time.sleep(0.5)
    proc.kill()
    pytest.fail("server did not start: " + log.read_text(errors="replace")[-800:])


def _stop(proc, fh):
    proc.terminate()
    try:
        proc.wait(10)
    except Exception:
        proc.kill()
    fh.close()


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    proc, fh, info = _spawn(tmp_path_factory, {})
    yield info
    _stop(proc, fh)


@pytest.fixture(scope="module")
def server_live_down(tmp_path_factory):
    """Live local-model evaluation is switched ON but nothing listens on the model port: the failure path a user hits when Ollama is not running."""
    proc, fh, info = _spawn(tmp_path_factory, {"SMART_DEMO_LIVE_MODULAR": "1", "SMART_DEMO_OLLAMA_HOST": "http://127.0.0.1:9"})
    yield info
    _stop(proc, fh)


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # no browser binary on this machine
            pytest.skip(f"Chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture()
def page(browser, server):
    ctx = browser.new_context(viewport={"width": 1366, "height": 860})
    pg = ctx.new_page()
    pg.problems = []
    pg.on("console", lambda m: pg.problems.append(m.text[:200]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: pg.problems.append("pageerror: " + str(e)[:200]))
    yield pg
    ctx.close()


def api(server, path, body=None):
    req = urllib.request.Request(server["demo"] + path, json.dumps(body).encode() if body is not None else None, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def shot(pg, name):
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(SHOTS) / f"{name}.png"), full_page=True)


INTRO_TEXT = "I am a graduate in statistics with two years of experience building models for churn prediction, and I like turning messy data into decisions people can act on."
PROSE = ("I would define the idea first, then give an example. For instance in practice you check for overfitting with cross-validation, keep a held-out test set, "
         "and use regularisation to control model complexity.")
CODE = "def pairwise(a, b):\n    # squared distances with broadcasting\n    return (a**2).sum(1)[:, None] - 2 * a @ b.T + (b**2).sum(1)[None, :]\n\n# broadcasting avoids Python loops"


def start_ui(pg, server, *, role="Python Developer", jd=None):
    """The whole setup is: choose a role, optionally paste a job description, press Start."""
    pg.goto(server["demo"] + "/new")
    pg.click(f".role-card[data-role='{role}']")
    if jd:
        pg.fill("#jd", jd)
    pg.click("#start-btn")
    pg.wait_for_url("**/demo/s/*", timeout=90000)
    pg.wait_for_selector("#answer")


def sid_of(pg):
    return pg.url.rstrip("/").split("/")[-1].split("?")[0]


def stage(pg):
    return pg.get_attribute("#interview", "data-stage") if pg.query_selector("#interview") else None


def reply(pg, text=None):
    """Answer the interviewer's current message and wait for the next one (or the wrap-up)."""
    st, n0 = stage(pg), pg.get_attribute("#interview", "data-n")
    pg.fill("#answer", text or (INTRO_TEXT if st == "introduction" else CODE if pg.get_attribute("#interview", "data-code") == "1" else PROSE))
    pg.click("#submit-btn")
    pg.wait_for_function("n0 => !document.querySelector('#interview') || document.querySelector('#interview').dataset.n !== n0 || document.querySelector('#see-feedback')", arg=n0, timeout=20000)
    return st


def play_to_the_end(pg, limit=14):
    seen = []
    for _ in range(limit):
        if pg.query_selector("#see-feedback") or not pg.query_selector("#answer"):
            break
        seen.append(reply(pg))
    pg.wait_for_selector("#see-feedback", timeout=10000)
    return seen


# ---------------------------------------------------------------------------------------------------------------- journeys
def test_empty_dashboard_then_simple_setup(page, server):
    page.goto(server["demo"] + "/")
    assert "Practise the interview" in page.locator("h1").inner_text()
    assert "No interviews yet" in page.inner_text("main")
    shot(page, "01-dashboard-empty")
    page.click("a.btn.primary")
    page.wait_for_url("**/demo/new")
    page.wait_for_selector(".role-card")
    assert page.locator(".role-card").count() >= 4 and page.locator(".role-card[aria-checked=true]").count() == 1      # exactly one role is always selected (the first, as a default)
    page.click(".role-card[data-role='Data Scientist']")
    assert page.is_enabled("#start-btn") and page.get_attribute(".role-card[data-role='Data Scientist']", "aria-checked") == "true"
    body = page.inner_text("main").lower()
    for gone in ("difficulty", "number of questions", "siamese", "tf-idf", "bi-lstm", "scorer"):
        assert gone not in body, gone
    assert page.locator("select").count() == 0 and page.locator("#jd").count() == 1
    page.fill("#jd", "x" * 4100)
    assert len(page.locator("#jd").input_value()) <= 4000, "the job description box stops at the limit"
    shot(page, "02-setup")
    assert not page.problems


def test_data_scientist_interview_end_to_end_in_the_browser(page, server):
    start_ui(page, server, role="Data Scientist", jd="We need someone who can run cross-validation, tune regularisation and explain model results. Email jobs@acme.example.")
    sid = sid_of(page)
    assert stage(page) == "introduction"
    ai0 = page.locator("#thread .turn-ai").count()
    assert "Introduction" in page.inner_text("#tracker") and page.locator(".turn-ai.is-current .ask").inner_text().strip()
    assert page.locator("#prev-fb").count() == 0 and page.locator(".bigscore").count() == 0, "no scoring badges while the conversation is going"
    page.wait_for_timeout(2200)
    assert page.inner_text("#t-q") != "0:00"
    shot(page, "03-workspace-intro")
    page.fill("#answer", "A draft that has not been submitted yet.")
    assert "Draft kept" in page.inner_text("#draft-note")
    page.reload()                                                           # refresh recovery: same question, draft restored
    assert page.input_value("#answer") == "A draft that has not been submitted yet." and stage(page) == "introduction"
    reply(page, INTRO_TEXT)
    assert stage(page) == "core" and page.locator("#thread .turn-you").count() == 1 and page.locator("#thread .turn-ai").count() == ai0 + 1
    assert INTRO_TEXT[:40] in page.inner_text("#thread")
    shot(page, "04-conversation")
    page.reload()                                                           # still question 2 of the conversation, with history intact
    assert stage(page) == "core" and INTRO_TEXT[:40] in page.inner_text("#thread") and page.locator("#thread .turn-ai").count() == ai0 + 1
    seen = play_to_the_end(page)
    assert seen.count("core") >= 4 and "practical" in seen
    assert page.locator(".turn.wrap").count() >= 1
    shot(page, "05-wrapup")
    page.click("#see-feedback")
    page.wait_for_url("**/summary")
    main = page.inner_text("main")
    for needle in ("Your interview feedback", "Technical questions answered", "Topics covered", "What I noticed", "Areas for future practice", "turn by turn"):
        assert needle in main, needle
    assert "overall score" not in main.lower() and "you passed" not in main.lower()
    assert page.locator("details.tech").count() >= 1 and not any("bigscore" in (e.get_attribute("class") or "") for e in page.query_selector_all("main > .card"))
    shot(page, "06-summary")
    export = json.load(urllib.request.urlopen(f"{server['demo']}/s/{sid}/export.json"))
    assert export["answers"][0]["legacy"]["status"] == "not_scored" and "jobs@acme.example" not in json.dumps(export)
    assert export["config"]["legacy_model"] == "bert" and "jd" not in export["plan"]
    stored = json.loads((Path(server["data"]) / f"{sid}.json").read_text(encoding="utf-8"))
    assert stored["plan"]["jd"]["text_stored"] is False and stored["plan"]["jd"]["matched_terms"] and "jobs@acme.example" not in json.dumps(stored)
    assert not page.problems


def test_python_developer_interview_with_the_code_editor(page, server):
    start_ui(page, server, role="Python Developer")
    seen = []
    while stage(page) != "practical":
        seen.append(reply(page))
        assert len(seen) < 12
    assert seen[0] == "introduction" and page.get_attribute("#interview", "data-code") == "1"
    assert page.locator("#gutter").count() == 1 and page.is_checked("#tabmode")
    page.click("#answer")
    k = page.keyboard
    k.type("def add(a, b):")
    k.press("Enter")                       # auto-indent after a colon
    k.type("return a + b")
    k.press("Enter")                       # keeps the indentation
    k.press("Shift+Tab")                   # dedent the empty indented line
    k.press("Enter")
    k.type("x = add(1, 2)")
    k.press("Enter")
    k.press("Tab")
    k.type("# tab indents by four spaces")
    expected = "def add(a, b):\n    return a + b\n\nx = add(1, 2)\n    # tab indents by four spaces"
    assert page.input_value("#answer") == expected
    assert page.inner_text("#gutter").split("\n") == ["1", "2", "3", "4", "5"]
    shot(page, "07-workspace-code")
    k.press("Escape")                      # Esc then Tab leaves the editor (keyboard users are not trapped)
    k.press("Tab")
    assert page.evaluate("document.activeElement.id") != "answer"
    sid = sid_of(page)
    reply(page, expected)
    play_to_the_end(page)
    data = json.load(urllib.request.urlopen(f"{server['demo']}/s/{sid}/export.json"))
    practical = [a for a in data["answers"] if a["stage"] == "practical"][0]
    assert practical["answer"] == expected                                   # stored byte for byte
    assert practical.get("code_check") is None or practical["code_check"]["executed"] is False
    page.goto(f"{server['demo']}/s/{sid}/summary")
    lines = page.eval_on_selector_all(".codeblock pre.code .cl", "els => els.map(e => e.textContent)")
    assert lines == expected.split("\n"), "the code block must show the answer exactly as typed"
    assert not page.problems


def test_end_early_is_two_step_and_the_report_says_what_was_not_reached(page, server):
    start_ui(page, server, role="Data Scientist")
    sid = sid_of(page)
    reply(page, INTRO_TEXT)
    reply(page, PROSE)
    page.click("#finish-btn")              # first click arms
    assert "Click again" in page.inner_text("#finish-btn")
    page.click("#finish-btn")
    page.wait_for_url("**/summary")
    main = page.inner_text("main")
    assert "Your interview feedback" in main and "Not reached." in main and "Skipped or not reached" in main and "Time spent" in main
    assert PROSE[:40] in main
    shot(page, "08-summary-ended-early")
    page.goto(server["demo"] + "/history")
    assert page.locator("table.list tbody tr").count() >= 1
    page.goto(server["demo"] + "/")
    assert "Where you are" in page.inner_text("main")
    shot(page, "09-dashboard")
    data = json.load(urllib.request.urlopen(f"{server['demo']}/s/{sid}/export.json"))
    assert data["plan"]["ended_reason"] == "ended_by_candidate"
    assert not page.problems


def test_three_skips_end_the_interview_politely(page, server):
    start_ui(page, server, role="Data Analyst")
    reply(page, INTRO_TEXT)
    for _ in range(3):
        page.click("#skip-btn")
        page.wait_for_function("() => document.querySelector('#see-feedback') || true", timeout=5000)
        page.wait_for_timeout(500)
    page.wait_for_selector("#see-feedback", timeout=10000)
    page.click("#see-feedback")
    page.wait_for_url("**/summary")
    assert "Skipped" in page.inner_text("main")
    assert not page.problems


def test_trend_is_shown_only_with_real_data(page, server):
    hist = json.load(urllib.request.urlopen(server["demo"] + "/api/history"))
    ready = hist["overview"]["trend_ready"]
    page.goto(server["demo"] + "/")
    assert page.locator("svg.trend").count() == 0 and "Average similarity" not in page.inner_text("main")      # the home page carries no similarity percentages
    page.goto(server["demo"] + "/history")
    assert (page.locator("svg.trend").count() == 1) == ready
    if not ready:
        assert "Not enough data for a trend" in page.inner_text("main")
    assert "legacy_scores" not in json.dumps(hist) and "by_domain" not in json.dumps(hist["interviews"])


def test_experimental_mock_is_opt_in_through_settings_and_stays_apart(page, server):
    page.goto(server["demo"] + "/settings")
    options = page.eval_on_selector_all("#pref-modular option", "els => els.map(e => e.value)")
    assert options == ["off", "mock"], "the live model must not be offered unless the server enables it"
    st, j = api(server, "/api/sessions", {"role": "Python Developer", "modular_mode": "live"})
    assert st == 400 and "not enabled" in j["error"]
    page.select_option("#pref-modular", "mock")
    page.click("#prefs-save")
    start_ui(page, server, role="Data Scientist")
    sid = sid_of(page)
    reply(page, INTRO_TEXT)
    reply(page, "Overfitting means memorising the training data instead of generalising; regularisation helps.")
    assert page.locator(".panel-modular").count() == 0, "experimental results are not shown inside the conversation"
    page.click("#finish-btn"); page.click("#finish-btn")
    page.wait_for_url("**/summary")
    page.wait_for_selector(".panel-modular", state="attached", timeout=15000)
    res = page.eval_on_selector("main", "e => e.textContent")                 # experimental results sit inside the collapsed "Technical details"
    assert "MOCK VERIFIER" in res and "NOT human-validated" in res and page.locator(".panel-legacy").count() >= 1 and page.locator(".panel-modular").count() >= 1
    assert page.locator("details.tech .panel-modular").count() >= 1
    shot(page, "10-summary-experimental-mock")
    page.goto(server["demo"] + "/settings")
    assert page.input_value("#pref-modular") == "mock"
    page.select_option("#pref-modular", "off"); page.click("#prefs-save")
    assert not page.problems


def test_quick_start_card_starts_an_interview_in_one_click(page, server):
    page.goto(server["demo"] + "/")
    page.click("[data-start-role='Python Developer']")
    page.wait_for_url("**/demo/s/*")
    assert stage(page) == "introduction" and page.is_visible("#answer") and page.is_visible("#submit-btn") and page.is_hidden("#mainnav")      # distraction-free
    page.click(".exit-link")
    page.wait_for_url("**/demo/")
    assert "Pick up where you left off" in page.inner_text("main")
    assert not page.problems


def test_setup_preselects_the_role_from_the_link(page, server):
    page.goto(server["demo"] + "/new?role=Data%20Analyst")
    assert page.get_attribute(".role-card[data-role='Data Analyst']", "aria-checked") == "true" and page.is_enabled("#start-btn")


def test_no_candidate_text_in_logs_metrics_or_history(page, server):
    start_ui(page, server, role="Data Scientist")
    reply(page, INTRO_TEXT)
    reply(page, f"Overfitting is memorising noise. {CANARY}")
    page.wait_for_timeout(500)
    metrics = urllib.request.urlopen(server["base"] + "/metrics").read().decode()
    hist = urllib.request.urlopen(server["demo"] + "/api/history").read().decode()
    log = server["log"].read_text(errors="replace")
    assert CANARY not in metrics and CANARY not in hist and CANARY not in log
    assert any(CANARY in p.read_text(encoding="utf-8") for p in Path(server["data"]).glob("demo_*.json")), "the answer is stored only in the user's own session file"


def test_settings_page_and_preferences(page, server):
    page.goto(server["demo"] + "/settings")
    txt = page.inner_text("main")
    assert "Evaluation methods" in txt and "Concept check" in txt and "Code check" in txt and "nothing is ever executed inside the web server" in txt
    assert "Sentence-BERT only" in txt and "Siamese" not in txt and "TF-IDF" not in txt and "Local model (Ollama" in txt and "off." in txt
    assert page.locator("#pref-size").count() == 0 and page.locator("#pref-diff").count() == 0, "length and difficulty are not choices any more"
    page.uncheck("#pref-timer")
    page.click("#prefs-save")
    assert page.is_visible("#prefs-saved")
    shot(page, "11-settings")
    page.goto(server["demo"] + "/new")
    assert page.locator("select").count() == 0
    start_ui(page, server, role="Data Scientist")
    assert not page.is_visible("#t-q")                          # timer hidden by preference
    page.click("#t-toggle")
    assert page.is_visible("#t-q")


def test_mobile_layout_has_no_horizontal_scroll(browser, server):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    pg = ctx.new_page()
    for path in ("/", "/new", "/history", "/settings"):
        pg.goto(server["demo"] + path)
        assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"), f"horizontal overflow on {path}"
    start_ui(pg, server, role="Data Scientist")
    assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    shot(pg, "12-mobile-workspace")
    reply(pg, INTRO_TEXT)
    assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    pg.click("#finish-btn"); pg.click("#finish-btn")
    pg.wait_for_url("**/summary")
    assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"), "overflow on the mobile feedback report"
    shot(pg, "13-mobile-summary")
    ctx.close()


@pytest.mark.parametrize("width,height,min_share", [(1920, 1080, 0.80), (1760, 900, 0.85), (1440, 900, 0.85), (1024, 768, 0.85), (768, 1024, 0.85), (390, 844, 0.90)])
def test_content_width_is_fluid_and_nav_is_aligned(browser, server, width, height, min_share):
    """Stage 9A.4: the main column must use most of the viewport (it was stuck near 800-1180px on wide screens), with no overflow and a nav aligned to it."""
    ctx = browser.new_context(viewport={"width": width, "height": height})
    pg = ctx.new_page()
    for path in ("/", "/new", "/history", "/settings"):
        pg.goto(server["demo"] + path)
        m = pg.evaluate("""() => {const s = document.querySelector('.stage-in').getBoundingClientRect(), t = document.querySelector('.topbar-in').getBoundingClientRect();
            return {w: s.width, l: s.left, tw: t.width, tl: t.left, over: document.documentElement.scrollWidth - document.documentElement.clientWidth}}""")
        assert m["over"] <= 1, f"overflow on {path} at {width}"
        assert m["w"] >= width * min_share - 1, f"{path} at {width}: content only {m['w']:.0f}px"
        assert m["w"] <= 1601
        assert abs(m["w"] - m["tw"]) <= 2 and abs(m["l"] - m["tl"]) <= 2, f"nav not aligned with content on {path} at {width}"
    ctx.close()


def test_keyboard_reaches_main_controls(page, server):
    page.goto(server["demo"] + "/")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    start_ui(page, server, role="Data Scientist")
    assert page.evaluate("document.activeElement.id") == "answer"          # the editor is focused on arrival
    page.keyboard.press("Escape")
    ids = []
    for _ in range(10):
        ids.append(page.evaluate("document.activeElement.id"))
        page.keyboard.press("Tab")
    assert {"submit-btn", "skip-btn", "finish-btn"} <= set(ids)


def test_erase_all_clears_history(page, server):
    page.goto(server["demo"] + "/settings")
    page.click("#erase-all")
    page.click("#erase-all")
    page.wait_for_function("document.querySelector('#erase-note').textContent.includes('Deleted')")
    page.goto(server["demo"] + "/")
    assert "No interviews yet" in page.inner_text("main")
    assert list(Path(server["data"]).glob("demo_*.json")) == []


def test_live_model_down_fails_safely_and_the_interview_continues(page, server_live_down):
    s = server_live_down
    page.goto(s["demo"] + "/settings")
    assert "Local model (Ollama, qwen2.5:7b)" in page.inner_text("main") and "turned on for this server" in page.inner_text("main")
    assert "live" in page.eval_on_selector_all("#pref-modular option", "els => els.map(e => e.value)")
    assert page.input_value("#pref-modular") == "off"                       # still opt-in
    page.select_option("#pref-modular", "live"); page.click("#prefs-save")
    start_ui(page, s, role="Data Scientist")
    reply(page, INTRO_TEXT)
    reply(page, "Overfitting means memorising the training data.")
    assert stage(page) in ("core", "follow_up")                              # the interview carries on while the model is down
    page.click("#finish-btn"); page.click("#finish-btn")
    page.wait_for_url("**/summary")
    page.wait_for_selector(".panel-modular.state-unavailable", state="attached", timeout=60000)
    res = page.eval_on_selector("main", "e => e.textContent")
    assert "Evaluation unavailable" in res and "no score and no penalty" in res.lower()
    assert "Sentence-BERT" in res                                           # the reliable layer is unaffected
    shot(page, "14-live-model-unavailable")
    page.goto(s["demo"] + "/settings"); page.select_option("#pref-modular", "off"); page.click("#prefs-save")
    assert not [p for p in page.problems if "CSP" in p or "pageerror" in p]


# ---------------------------------------------------------------------------------------------------------------- Stage 9C
def test_9c_followup_setting_is_opt_in_and_mock_followups_and_written_feedback_are_labelled(page, server):
    page.goto(server["demo"] + "/settings")
    assert page.eval_on_selector_all("#pref-followup option", "els => els.map(e => e.value)") == ["deterministic", "mock"], "the local model is not offered unless the server enables it"
    assert page.input_value("#pref-followup") == "deterministic"
    st, j = api(server, "/api/sessions", {"role": "Data Scientist", "followup_mode": "live"})
    assert st == 400 and "not enabled" in j["error"]
    page.select_option("#pref-followup", "mock"); page.select_option("#pref-modular", "mock"); page.click("#prefs-save")
    start_ui(page, server, role="Data Scientist")
    sid = sid_of(page)
    reply(page, INTRO_TEXT)
    reply(page, "Overfitting means the model memorises the training data. Regularisation helps.")
    thread = page.inner_text("#thread")
    assert "{" not in thread and "prompt_version" not in thread and "concept_ids" not in thread, "no internal JSON or prompt data in the conversation"
    assert page.locator(".panel-grounded, .panel-modular").count() == 0, "experimental results are not shown inside the conversation"
    seen = [stage(page)]
    for _ in range(12):
        if page.query_selector("#see-feedback") or not page.query_selector("#answer"):
            break
        seen.append(reply(page))
    page.wait_for_selector("#see-feedback", timeout=10000)
    exp = json.load(urllib.request.urlopen(server["demo"] + f"/s/{sid}/export.json"))
    assert exp["plan"]["followup_log"], "the experimental attempts are recorded (codes only)"
    page.goto(server["demo"] + f"/s/{sid}")
    page.goto(server["demo"] + f"/s/{sid}/summary")
    page.wait_for_selector(".panel-grounded", state="attached", timeout=15000)
    text = page.eval_on_selector("main", "e => e.textContent")
    assert "EXPERIMENTAL" in text and "NOT human-validated" in text and "NO GRADE" in text and "MOCK VERIFIER" in text
    assert "prompt_version" not in text and "concept_ids" not in text and '"decision"' not in text
    assert page.locator("details.tech .panel-modular").count() >= 1, "SBERT and raw findings stay in the technical details"
    shot(page, "15-9c-grounded-feedback")
    page.goto(server["demo"] + "/settings")
    page.select_option("#pref-followup", "deterministic"); page.select_option("#pref-modular", "off"); page.click("#prefs-save")
    assert not [p for p in page.problems if "CSP" in p or "pageerror" in p]


def test_9c_python_developer_with_mock_followups_and_code_check_still_completes(page, server):
    page.goto(server["demo"] + "/settings")
    page.select_option("#pref-followup", "mock"); page.click("#prefs-save")
    start_ui(page, server, role="Python Developer")
    play_to_the_end(page, limit=16)
    sid = sid_of(page)
    page.goto(server["demo"] + f"/s/{sid}/summary")
    assert "Written feedback" not in page.inner_text("main") or "NOT human-validated" in page.inner_text("main")
    assert not [p for p in page.problems if "CSP" in p or "pageerror" in p]
    page.goto(server["demo"] + "/settings")
    page.select_option("#pref-followup", "deterministic"); page.click("#prefs-save")


def test_9c_model_down_followups_fall_back_and_the_interview_continues(page, server_live_down):
    s = server_live_down
    page.goto(s["demo"] + "/settings")
    assert "live" in page.eval_on_selector_all("#pref-followup option", "els => els.map(e => e.value)")
    assert page.input_value("#pref-followup") == "deterministic"
    page.select_option("#pref-followup", "live"); page.click("#prefs-save")
    start_ui(page, s, role="Data Scientist")
    sid = sid_of(page)
    t0 = time.time()
    reply(page, INTRO_TEXT)
    reply(page, "Overfitting means the model memorises training data and then does badly on new data.")
    assert stage(page) == "follow_up", "a bank-backed follow-up still appears when the model is down"
    assert time.time() - t0 < 25
    page.locator(".turn-ai.is-current details.src summary").click()
    txt = page.inner_text("#thread")
    assert "Experimental follow-up written by the local model" not in txt and "Deterministic follow-up" in txt or "fixed wording" in txt
    exp = json.load(urllib.request.urlopen(s["demo"] + f"/s/{sid}/export.json"))
    assert exp["plan"]["followup_log"][0]["outcome"] == "fallback"
    shot(page, "16-9c-model-down-fallback")
    page.goto(s["demo"] + "/settings"); page.select_option("#pref-followup", "deterministic"); page.click("#prefs-save")


# ---------------------------------------------------------------------------------------------------------------- Stage 9D: slow / fast local model (a FAKE Ollama with scripted timings)
def _fake_followup_reply(req):
    """Builds a valid follow-up from the request itself (so it fits whatever question the plan picked)."""
    user = req["messages"][-1]["content"]
    if req.get("options", {}).get("num_predict", 99) <= 2:
        return "ok"
    concepts = [ln for ln in user.splitlines() if "(exact-words hint: not found)" in ln]
    ans = user.split("=====\n", 1)[1].split("\n=====END")[0] if "=====\n" in user else ""
    if not concepts:
        return json.dumps({"decision": "skip", "question": "", "purpose": "deepen", "concept_id": "none", "answer_quote": "", "uses_given_facts_only": True, "already_in_answer": False})
    cid, rest = concepts[0].split(" ", 1)
    label = rest.split(" (exact-words hint")[0]
    quote = " ".join(ans.split()[:5])
    return json.dumps({"decision": "ask", "question": f"You said \"{quote}\". How does {label} fit into that?", "purpose": "probe_concept", "concept_id": cid, "answer_quote": quote,
                       "uses_given_facts_only": True, "already_in_answer": False})


@pytest.fixture(scope="module")
def fake_model():
    from tests.helpers.fake_ollama import FakeOllama
    with FakeOllama(reply=_fake_followup_reply, load_delay=0.2) as f:
        yield f


@pytest.fixture(scope="module")
def server_fake_model(tmp_path_factory, fake_model):
    proc, fh, info = _spawn(tmp_path_factory, {"SMART_DEMO_LIVE_MODULAR": "1", "SMART_DEMO_OLLAMA_HOST": fake_model.url, "SMART_DEMO_FOLLOWUP_TIMEOUT_S": "2"})
    yield info
    _stop(proc, fh)


def _answer_about_the_question(pg):
    q = pg.evaluate("() => { const a = [...document.querySelectorAll('#thread article.turn-ai:not(.thinking)')].pop(); return a ? a.innerText : ''; }")[:300]
    return "My answer to this: " + q.replace("?", ".") + " I would start with the basics and explain it step by step."


def test_9d_fast_model_gives_an_experimental_followup_with_a_visible_label(page, server_fake_model, fake_model):
    s = server_fake_model
    page.goto(s["demo"] + "/settings")
    assert "live" in page.eval_on_selector_all("#pref-followup option", "els => els.map(e => e.value)")
    page.select_option("#pref-followup", "live"); page.click("#prefs-save")
    fake_model.first_delay = 0.0
    start_ui(page, s, role="Data Scientist")
    sid = sid_of(page)
    reply(page, INTRO_TEXT)
    time.sleep(1.0)                                              # the model finishes its background warm-up
    reply(page, _answer_about_the_question(page))
    assert stage(page) == "follow_up"
    exp = json.load(urllib.request.urlopen(s["demo"] + f"/s/{sid}/export.json"))
    log = exp["plan"]["followup_log"][0]
    assert log["outcome"] == "llm", json.dumps(log)
    page.locator(".turn-ai.is-current details.src summary").click()
    assert "Experimental follow-up written by the local model" in page.inner_text("#thread")
    text = page.inner_text("#thread")
    assert "{" not in text and "prompt_version" not in text and '"decision"' not in text
    shot(page, "17-9d-llm-followup")
    page.goto(s["demo"] + "/settings"); page.select_option("#pref-followup", "deterministic"); page.click("#prefs-save")


def test_9d_slow_model_shows_a_loading_state_then_falls_back_without_freezing(page, server_fake_model, fake_model):
    s = server_fake_model
    page.goto(s["demo"] + "/settings")
    page.select_option("#pref-followup", "live"); page.click("#prefs-save")
    fake_model.first_delay = 0.0
    start_ui(page, s, role="Data Scientist")
    sid = sid_of(page)
    reply(page, INTRO_TEXT)
    time.sleep(1.0)                                              # warm-up finished (fast)
    fake_model.first_delay = 6.0                                 # now the model becomes slower than the 2 s test deadline
    t0 = time.time()
    page.fill("#answer", _answer_about_the_question(page))
    n0 = page.get_attribute("#interview", "data-n")
    page.click("#submit-btn")
    page.wait_for_function("() => (document.querySelector('#think-label')||{}).textContent.includes('Preparing a follow-up')", timeout=3000)
    page.wait_for_function("n0 => document.querySelector('#interview').dataset.n !== n0", arg=n0, timeout=15000)
    assert time.time() - t0 < 8, "the deadline, not the model, bounds the wait"
    assert stage(page) in ("core", "follow_up"), "after timeout, continue with a planned question or a warranted standard follow-up"
    assert "Experimental follow-up written by the local model" not in page.inner_text("#thread")
    exp = json.load(urllib.request.urlopen(s["demo"] + f"/s/{sid}/export.json"))
    assert exp["plan"]["followup_log"][0]["outcome"] == "fallback" and exp["plan"]["followup_log"][0]["reasons"] == ["deadline_exceeded"]
    deadline = time.time() + 5                                   # the timed-out generation was cancelled on the server side
    while time.time() < deadline and fake_model.in_flight:
        time.sleep(0.1)
    assert fake_model.in_flight == 0 and fake_model.cancelled >= 1
    fake_model.first_delay = 0.0
    play_to_the_end(page, limit=14)
    page.goto(s["demo"] + "/settings"); page.select_option("#pref-followup", "deterministic"); page.click("#prefs-save")
    assert not [p for p in page.problems if "CSP" in p or "pageerror" in p]


# ------------------------------------------------------------------------------------------------------------ Stage 10 journeys
BEH_ANSWER = ("In my last project at university our team disagreed about the model. I was responsible for the evaluation, so I wrote a short comparison, "
              "presented it to everyone and we agreed on the simpler model. As a result the demo ran 30% faster and I learned to share evidence early.")


def start_typed(pg, server, kind, role="Data Scientist"):
    pg.goto(server["demo"] + "/new")
    pg.click(f".role-card[data-role='{role}']")
    pg.check(f"input[name='interview_type'][value='{kind}']")
    pg.click("#start-btn")
    pg.wait_for_url("**/demo/s/*")
    pg.wait_for_selector("#answer")


def test_setup_offers_three_interview_types_with_technical_as_default(page, server):
    page.goto(server["demo"] + "/new")
    radios = page.locator("input[name='interview_type']")
    assert radios.count() == 3 and page.locator("input[name='interview_type'][value='technical']").is_checked()
    text = page.inner_text("main").lower()
    for bad in ("faiss", "sbert", "bm25", "llm", "rag", "ollama", "embedding"):
        assert bad not in text, bad
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert all(page.locator(f"label[for='{r.get_attribute('id')}']").count() == 1 for r in radios.element_handles() if r.get_attribute("id")) or page.locator("label.type-opt").count() == 3
    assert not page.problems


def test_behavioural_interview_in_the_browser_has_its_own_feedback(page, server):
    start_typed(page, server, "behavioural")
    assert stage(page) == "introduction"
    reply(page, INTRO_TEXT)
    assert stage(page) == "behavioural" and "Behavioural" in page.inner_text("#tracker")
    for _ in range(12):
        if page.query_selector("#see-feedback") or not page.query_selector("#answer"):
            break
        reply(page, BEH_ANSWER)
    page.wait_for_selector("#see-feedback", timeout=10000)
    page.click("#see-feedback")
    page.wait_for_url("**/summary")
    main = page.inner_text("main")
    assert page.locator("#behavioural-feedback").count() == 1 and "reading" in main.lower()
    low = main.lower()
    for bad in ("you passed", "hire", "reject", "overall score", "% match"):
        assert bad not in low, bad
    assert not page.problems


def test_mixed_interview_moves_from_technical_to_behavioural_with_a_transition(page, server):
    start_typed(page, server, "mixed")
    stages = []
    for _ in range(14):
        if page.query_selector("#see-feedback") or not page.query_selector("#answer"):
            break
        stages.append(reply(page, BEH_ANSWER if stage(page) == "behavioural" else None))
    page.wait_for_selector("#see-feedback", timeout=10000)
    assert "core" in stages and "behavioural" in stages and stages.index("core") < stages.index("behavioural")
    assert page.locator(".turn-ai").count() >= 6
    assert not page.problems

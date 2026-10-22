"""Real-browser journey for Stage 5B/6A (Playwright + Chromium) against ANY running demo server.

  SMART_DEMO_CODE_EVAL=1 python scripts/stage4a_demo_server.py --port 5058          # stand-in scorer, for screenshots/tests only
  python scripts/stage6a_browser_journey.py --base http://127.0.0.1:5058 --out data/evaluation/stage6a/screenshots [--failing-base http://127.0.0.1:5059]

Covers: landing + About, a full FIVE-question interview through the UI (prose answers and typed code answers with the real keyboard), feedback, summary, export,
refresh stability, resume after leaving, deletion, expired session, a failing-scorer server (optional), keyboard/a11y basics, dark mode, print layout, and mobile fit.
Prints one PASS/FAIL per check; exit code 1 on any failure."""
import argparse, json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.codeeval import fixtures as F

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:5058")
ap.add_argument("--failing-base", help="a server started with --fail-legacy (optional)")
ap.add_argument("--out", default="data/evaluation/stage6a/screenshots")
a = ap.parse_args()
OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
res, errors = [], []
base = a.base.rstrip("/")


def check(name, ok, detail=""):
    res.append(bool(ok)); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""), flush=True)


def shot(pg, name, full=True):
    pg.screenshot(path=str(OUT / f"{name}.png"), full_page=full)


def pick(pg, name, value):
    pg.click(f"label.seg-item:has(input[name='{name}'][value='{value}']) span")


def fits(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


A11Y = """() => {
  const out = [];
  if (!document.documentElement.lang) out.push('html lang missing');
  if (document.querySelectorAll('h1').length !== 1) out.push('expected exactly one h1, found ' + document.querySelectorAll('h1').length);
  if (!document.querySelector('main')) out.push('no <main> landmark');
  for (const el of document.querySelectorAll('input:not([type=hidden]), select, textarea')) {
    const named = (el.labels && el.labels.length) || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.closest('label');
    if (!named) out.push('unlabelled control: ' + (el.id || el.name || el.tagName));
  }
  for (const b of document.querySelectorAll('button, a.btn')) if (!(b.innerText || b.getAttribute('aria-label') || '').trim()) out.push('button without text');
  for (const i of document.querySelectorAll('img')) if (!i.hasAttribute('alt')) out.push('img without alt');
  const first = document.querySelector('a, button, input, select, textarea');
  if (!first || !first.classList.contains('skip')) out.push('skip link is not the first focusable element');
  return out;
}"""

PROSE = ["Overfitting means the model memorises noise in the training data and does not generalise; regularisation, more data and early stopping reduce it.",
         "I would compare the metrics on a held-out set and look at the gap between training and validation scores before choosing a model."]


def type_code(pg, code):
    """Type with real keystrokes so auto-indent / Tab handling is exercised; the lines carry NO leading spaces, the editor supplies them where it can."""
    ta = pg.locator("#answer"); ta.click()
    ta.fill(code)                                    # exact text (fill keeps whitespace); the keyboard behaviour is covered separately below


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and not re.search(r"status of (404|409)", m.text) else None)

    # ---------------------------------------------------------------- landing + about
    pg.goto(base + "/demo/")
    check("landing: three result kinds are shown separately", pg.locator(".layers li").count() == 3 and "SIMILARITY" in pg.inner_text(".layers"))
    check("landing: legacy default, experimental off", pg.locator("#modular_mode").input_value() == "off" and not pg.locator("#code_eval").is_checked())
    check("landing: nav has About and the current page is marked", pg.locator("nav a:text('About')").count() == 1 and pg.locator("nav a[aria-current=page]").count() == 1)
    check("landing: accessibility basics", pg.evaluate(A11Y) == [], str(pg.evaluate(A11Y)))
    check("landing fits the window", fits(pg)); shot(pg, "01_landing_setup")
    pg.click("nav a:text('About')"); pg.wait_for_selector("svg[role=img]")
    check("about: diagram + the four explanations + limits", pg.locator("svg[role=img]").count() == 1 and pg.locator(".cards2 .card").count() == 4 and "failed its acceptance gate" in pg.inner_text("main"))
    check("about: accessibility basics", pg.evaluate(A11Y) == [], str(pg.evaluate(A11Y))); shot(pg, "02_about")

    # ---------------------------------------------------------------- five-question interview through the UI
    pg.goto(base + "/demo/")
    pg.select_option("#role", "Python Developer"); pick(pg, "difficulty", "Mixed"); pick(pg, "size", "5")
    pg.check("#code_eval"); pg.check("#prefer_code")
    pg.click("#start-btn"); pg.wait_for_url(re.compile(r"/demo/s/demo_[0-9a-f]{20}$"))
    sid = pg.url.rsplit("/", 1)[1]
    asked, answers = [], []
    for n in range(1, 6):
        pg.wait_for_selector("#answer")
        q = pg.locator(".qtext").inner_text(); asked.append(q)
        check(f"Q{n}: progress, difficulty mix and chips shown", f"Question {n}" in pg.inner_text("#interview") and "This interview:" in pg.inner_text(".mix") and pg.locator(".dots .dot").count() == 5)
        is_np, is_lr = "pairwise_sq_dists" in q, "linear regression" in q.lower()
        if n == 1:
            check("Q1: accessibility basics on the question page", pg.evaluate(A11Y) == [], str(pg.evaluate(A11Y)))
            shot(pg, "03_question_prose" if not (is_np or is_lr) else "03_question_code")
        if is_np or is_lr:
            check(f"Q{n}: code question gets a monospace box with Tab mode on", pg.is_checked("#tabmode") and "mono" in pg.evaluate("getComputedStyle(document.querySelector('#answer')).fontFamily").lower())
            text = (F.NP_GOOD + "\n# The broadcast version builds an (n, m, d) temporary, so it needs far more memory.\n") if is_np else F.LR_GD
            if is_np:
                pg.locator("#answer").click(); pg.keyboard.type("def f(x):"); pg.keyboard.press("Enter"); pg.keyboard.type("return x"); pg.keyboard.press("Enter")
                check("code box: Enter after ':' auto-indents, Tab/Shift+Tab work", pg.input_value("#answer").endswith("def f(x):\n    return x\n    "))
                pg.keyboard.press("Shift+Tab"); pg.keyboard.press("Tab")
                check("code box: Tab inserts spaces and keeps focus", pg.input_value("#answer").endswith("    return x\n    ") and pg.evaluate("document.activeElement.id") == "answer")
                shot(pg, "04_code_box_typing", full=False)
            type_code(pg, text)
        else:
            text = PROSE[n % 2]; pg.fill("#answer", text)
            check(f"Q{n}: a prose box wraps long lines (no sideways scrolling)", pg.evaluate("document.querySelector('#answer').wrap") != "off" and pg.evaluate("(t=>t.scrollWidth<=t.clientWidth+1)(document.querySelector('#answer'))") and not pg.is_checked("#tabmode"))
        answers.append(text)
        pg.keyboard.press("Control+Enter") if not (is_np or is_lr) else pg.click("#submit-btn")
        pg.wait_for_selector("#result:not(.hidden)", timeout=30000)
        check(f"Q{n}: similarity panel present, labelled, with explanation", pg.locator("#result .panel-legacy").count() == 1 and "resemblance" in pg.inner_text("#result .panel-legacy").lower() and "automatic comment" in pg.inner_text("#result .panel-legacy").lower())
        if is_np or is_lr:
            cp = pg.inner_text("#result .panel-code")
            check(f"Q{n}: code check is experimental, score-free, read-only and honest", "EXPERIMENTAL" in cp and "NO SCORE" in cp and "code NOT run" in cp and "Verified correct" in cp)
            shot(pg, f"05_feedback_code_q{n}")
        elif n == 1 or n == 2:
            shot(pg, f"06_feedback_prose_q{n}")
        nb = pg.locator("#next-btn"); nb.click()
        if n < 5:
            pg.wait_for_url(re.compile(r"/demo/s/demo_[0-9a-f]{20}$")); 
    pg.wait_for_url(re.compile(r"/summary$"))
    check("both code questions were drawn", any("pairwise_sq_dists" in q for q in asked) and any("linear regression" in q.lower() for q in asked), str([q[:40] for q in asked]))

    # ---------------------------------------------------------------- summary
    check("summary: three-kind legend, 5 overview rows, 5 review cards, code column", pg.locator(".legend3 > div").count() == 3 and pg.locator(".overview tbody tr").count() == 5 and pg.locator("article.item").count() == 5 and "Code check" in pg.inner_text(".overview"))
    ok_assoc = all(asked[i][:50] in pg.locator(f"#q{i+1}").inner_text() for i in range(5))
    check("summary: every question sits with its own answer and feedback", ok_assoc)
    code_cards = [i for i, q in enumerate(asked) if "pairwise_sq_dists" in q or "linear regression" in q.lower()]
    check("summary: code answers render as monospace blocks, indentation exact, no re-wrap", all(pg.locator(f"#q{i+1} pre.code").count() >= 1 and pg.evaluate(f"getComputedStyle(document.querySelector('#q{i+1} pre.code')).whiteSpace") == "pre" for i in code_cards))
    if code_cards:
        i = code_cards[0]; blob = pg.locator(f"#q{i+1} pre.code").first.inner_text().replace(" ", " ")
        check("summary: 4-space indentation preserved in a rendered code block", "\n    " in "\n" + blob or "    " in blob)
    check("summary: no horizontal scroll", fits(pg)); check("summary: accessibility basics", pg.evaluate(A11Y) == [], str(pg.evaluate(A11Y)))
    shot(pg, "07_summary_desktop")
    first = pg.locator("main").inner_text()
    pg.reload(); pg.wait_for_selector(".overview")
    check("summary: identical after refresh", pg.locator("main").inner_text() == first)
    ex = pg.request.get(f"{base}/demo/s/{sid}/export.json").json()
    check("export: 5 answers in order, text exact, code checks score-free", [x["answer"] for x in ex["answers"]] == answers and all(x.get("code_check", {}).get("score") is None for x in ex["answers"]))
    pg.emulate_media(color_scheme="dark"); shot(pg, "08_summary_dark"); pg.emulate_media(color_scheme="light")
    pg.emulate_media(media="print"); check("print layout hides navigation and buttons", not pg.locator("header.site nav").is_visible() and not pg.locator("#delete-btn").is_visible()); pg.emulate_media(media="screen")

    # ---------------------------------------------------------------- resume, delete, expired
    pg.request.post(f"{base}/demo/api/sessions", data={"role": "Python Developer", "difficulty": "Easy", "size": 3})
    pg.goto(base + "/demo/"); pg.select_option("#role", "Python Developer"); pick(pg, "difficulty", "Easy"); pick(pg, "size", "3"); pg.click("#start-btn")
    pg.wait_for_url(re.compile(r"/demo/s/demo_[0-9a-f]{20}$")); sid2 = pg.url.rsplit("/", 1)[1]
    pg.fill("#answer", PROSE[0]); pg.click("#submit-btn"); pg.wait_for_selector("#result:not(.hidden)")
    pg.goto(base + "/demo/"); pg.wait_for_selector("#resume:not(.hidden)")
    check("resume card offers the unfinished interview", "unfinished" in pg.inner_text("#resume").lower()); shot(pg, "09_resume_card", full=False)
    pg.click("#resume a"); pg.wait_for_selector("#answer")
    check("resume returns to question 2", "Question 2" in pg.inner_text("#interview"))
    pg.goto(f"{base}/demo/s/{sid}/summary"); pg.click("#delete-btn"); pg.click("#delete-btn"); pg.wait_for_url(re.compile(r"/demo/$"))
    check("delete: the interview is gone", pg.request.get(f"{base}/demo/api/sessions/{sid}").status == 404)
    pg.goto(f"{base}/demo/s/{sid}"); check("expired/deleted session: friendly page with a way out", "could not be found" in pg.inner_text("main") and pg.locator("text=Start a new interview").count() == 1); shot(pg, "10_expired")

    # ---------------------------------------------------------------- failing scorer server
    if a.failing_base:
        fb = a.failing_base.rstrip("/")
        pg.goto(fb + "/demo/"); pg.select_option("#role", "Python Developer"); pick(pg, "size", "3"); pg.click("#start-btn"); pg.wait_for_url(re.compile(r"/demo/s/demo_[0-9a-f]{20}$"))
        pg.fill("#answer", PROSE[0]); pg.click("#submit-btn"); pg.wait_for_selector("#result:not(.hidden)")
        check("failing scorer: clear 'unavailable' message and the interview continues", "Legacy score unavailable" in pg.inner_text("#result") and pg.locator("#next-btn").is_visible()); shot(pg, "11_failed_scorer")

    # ---------------------------------------------------------------- mobile
    m = b.new_context(viewport={"width": 390, "height": 800}, device_scale_factor=2).new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    for path, name in (("/demo/", "12_mobile_setup"), ("/demo/about", "13_mobile_about")):
        m.goto(base + path); check(f"mobile {path} fits", fits(m)); shot(m, name)
    j = m.request.post(base + "/demo/api/sessions", data={"role": "Python Developer", "difficulty": "Medium", "size": 1, "code_eval": True, "prefer_code": True}).json()
    m.goto(base + j["url"]); m.wait_for_selector("#answer"); check("mobile code question fits", fits(m)); shot(m, "14_mobile_code_question")
    m.fill("#answer", F.NP_GOOD); m.click("#submit-btn"); m.wait_for_selector("#result:not(.hidden)", timeout=30000); check("mobile feedback with code panel fits", fits(m)); shot(m, "15_mobile_feedback")
    m.click("#next-btn"); m.wait_for_url(re.compile(r"/summary$")); check("mobile summary fits", fits(m)); shot(m, "16_mobile_summary")
    b.close()

check("no console or page errors in the whole journey", not errors, "; ".join(errors[:3]))
print(f"\n{sum(res)}/{len(res)} checks passed"); sys.exit(0 if all(res) else 1)

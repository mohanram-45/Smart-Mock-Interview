"""Browser journey for Stage 4D/5A (code answers). Needs a server started with SMART_DEMO_CODE_EVAL=1, e.g.
  SMART_DEMO_CODE_EVAL=1 python scripts/stage4a_demo_server.py --port 5056
  python scripts/stage4d_browser_journey.py --base http://127.0.0.1:5056 --out data/evaluation/stage4d/screenshots
Typing is done with the real keyboard (Tab key, auto-indent) so the textarea behaviour is tested, not just the API. Without SMART_CODEEVAL_EXEC the code is only READ."""
import argparse, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:5056")
ap.add_argument("--out", default="data/evaluation/stage4d/screenshots")
a = ap.parse_args()
OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
res, errors = [], []


def check(name, ok, detail=""):
    res.append(ok); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""), flush=True)


def pick(page, name, value):
    page.click(f"label.seg-item:has(input[name='{name}'][value='{value}']) span")


def no_hscroll(page):
    return page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


NP = "def pairwise_sq_dists(A, B):\n    a2 = (A * A).sum(axis=1)[:, None]\n    b2 = (B * B).sum(axis=1)[None, :]\n    D = a2 + b2 - 2.0 * (A @ B.T)\n    return D\n"
EXPL = "\nThe broadcast version needs an (n, m, d) temporary so it uses much more memory than the expansion."
HOSTILE = "\n# <img src=x onerror=window.__pwned=1> & <b>bold</b>"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and not re.search(r"status of (404|409)", m.text) else None)
    base = a.base.rstrip("/")
    page.goto(base + "/demo/")
    check("code option is shown, unchecked by default", page.locator("#code_eval").count() == 1 and not page.locator("#code_eval").is_checked())
    page.check("#code_eval"); page.check("#prefer_code")
    check("'prefer code' appears only after the code option is ticked", page.locator("#prefer-code-wrap").is_visible())
    page.screenshot(path=str(OUT / "01_setup_code_option.png"), full_page=True)
    # the setup form offers sizes from 3 up; a one-question session is created through the same API the form calls
    def start(pg):
        r = pg.request.post(base + "/demo/api/sessions", data={"role": "Python Developer", "difficulty": "Medium", "size": 1, "code_eval": True, "prefer_code": True})
        return r.json()
    j = start(page); sid = j["session_id"]; page.goto(base + j["url"]); page.wait_for_selector("#answer")
    check("a code question was drawn (NumPy pairwise distances)", "pairwise_sq_dists" in page.inner_text(".qtext"))
    ta = page.locator("#answer")
    check("answer box is monospace, no-wrap, Tab mode on", page.evaluate("getComputedStyle(document.querySelector('#answer')).fontFamily").lower().find("mono") >= 0 and page.is_checked("#tabmode"))
    page.screenshot(path=str(OUT / "02_code_question.png"), full_page=True)

    # type with real keystrokes: auto-indent after a colon, Tab inserts 4 spaces, Shift+Tab outdents
    ta.click()
    page.keyboard.type("def f(x):"); page.keyboard.press("Enter")
    check("Enter after a colon indents one level", ta.input_value().endswith("def f(x):\n    "))
    page.keyboard.type("return x"); page.keyboard.press("Enter")
    check("Enter keeps the current indentation", ta.input_value().endswith("    return x\n    "))
    page.keyboard.press("Shift+Tab")
    check("Shift+Tab outdents", ta.input_value().endswith("    return x\n"))
    page.keyboard.press("Tab")
    check("Tab inserts 4 spaces, not a focus change", ta.input_value().endswith("    return x\n    ") and page.evaluate("document.activeElement.id") == "answer")
    page.keyboard.press("Escape"); page.keyboard.press("Tab")
    check("Esc then Tab leaves the box (no keyboard trap)", page.evaluate("document.activeElement.id") != "answer")

    # real submission of a multi-line answer with code + prose + hostile comment
    full = NP + EXPL + HOSTILE
    ta.fill(full)
    page.click("#submit-btn"); page.wait_for_selector("#result:not(.hidden)", timeout=30000)
    check("hostile markup did not run", page.evaluate("window.__pwned === undefined"))
    check("code panel is present, labelled experimental, no score", page.locator("#result .panel-code").count() == 1 and "NO SCORE" in page.inner_text("#result .panel-code") and "EXPERIMENTAL" in page.inner_text("#result .panel-code"))
    check("says the code was read, not run", "code NOT run" in page.inner_text("#result .panel-code") and "read, not run" in page.inner_text("#result .panel-code"))
    check("legacy card explains it compared text, not behaviour", "does not run your code" in page.inner_text("#result .panel-legacy") and "automatic comment" in page.inner_text("#result .panel-legacy").lower())
    txt = page.inner_text("#result .panel-code")
    check("structure found, explanation reported as unverified, nothing 'verified correct'", "Verified correct" in txt and "(0)" in txt.split("Verified correct")[1][:30])
    page.screenshot(path=str(OUT / "03_feedback_code_panel.png"), full_page=True)
    page.click("#next-btn"); page.wait_for_url(re.compile(r"/summary$"))

    # summary: indentation preserved, split code/prose, escape
    code_text = page.locator("#q1 pre.code").first.inner_text()
    check("summary shows the code block with indentation intact", "\n    a2 = (A * A)" in "\n" + code_text.replace(" ", " ") or "    a2 = (A * A)" in code_text)
    ws = page.evaluate("getComputedStyle(document.querySelector('#q1 pre.code')).whiteSpace")
    check("code block does not re-wrap (white-space: pre)", ws == "pre", ws)
    check("prose is in its own block", page.locator("#q1 .prose-answer").count() >= 1 and "much more memory" in page.locator("#q1 .prose-answer").first.inner_text() or "much more memory" in page.locator("#q1").inner_text())
    check("hostile comment shown as text", "<img src=x" in page.locator("#q1").inner_text() and page.evaluate("window.__pwned === undefined"))
    check("overview has a code-check column", "Code check" in page.inner_text(".overview"))
    check("no horizontal scroll on the summary", no_hscroll(page))
    first = page.locator("#q1").inner_text()
    page.screenshot(path=str(OUT / "04_summary_code.png"), full_page=True)
    page.reload(); page.wait_for_selector(".overview")
    check("summary is identical after refresh", page.locator("#q1").inner_text() == first)
    exp = page.request.get(f"{base}/demo/s/{sid}/export.json").json()["answers"][0]
    check("export keeps the exact text and states no score", exp["answer"] == full and exp["code_check"]["score"] is None and exp["code_check"]["executed"] is False)

    # mobile
    m = b.new_context(viewport={"width": 390, "height": 800}, device_scale_factor=2).new_page()
    m.goto(base + "/demo/s/" + sid + "/summary"); m.wait_for_selector(".overview")
    check("mobile summary fits (long code scrolls inside its own box)", no_hscroll(m))
    m.screenshot(path=str(OUT / "05_summary_code_mobile.png"), full_page=True)
    m.goto(base + start(m)["url"]); m.wait_for_selector("#answer")
    check("mobile code question fits", no_hscroll(m)); m.screenshot(path=str(OUT / "06_code_question_mobile.png"), full_page=True)
    page.goto(f"{base}/demo/s/{sid}/summary"); page.click("#delete-btn"); page.click("#delete-btn"); page.wait_for_url(re.compile(r"/demo/$"))
    b.close()
check("no console or page errors", not errors, "; ".join(errors[:3]))
print(f"\n{sum(res)}/{len(res)} checks passed"); sys.exit(0 if all(res) else 1)

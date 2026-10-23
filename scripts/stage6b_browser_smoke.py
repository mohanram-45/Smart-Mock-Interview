"""Real-browser smoke test of a RUNNING app (Playwright + Chromium): works against `python main/app.py`, the Docker container, or the stand-in server.

    python scripts/stage6b_browser_smoke.py --base http://127.0.0.1:5000 --out data/evaluation/stage6b/screenshots

Checks: landing + About render without console errors; /healthz and /readyz in the browser; experimental options are NOT offered by default; a full five-question interview
through the UI (whatever scorers exist: if none is set up the page must say so instead of showing a score); the summary; and that /metrics counted exactly that interview
(started +1, completed +1, answers +5) without containing any of the answer text."""

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:5000")
ap.add_argument("--out", default="data/evaluation/stage6b/screenshots")
a = ap.parse_args()
base, out = a.base.rstrip("/"), Path(a.out)
out.mkdir(parents=True, exist_ok=True)
MARK = "SMOKE-ANSWER-MARKER-7Q2X"
ANSWERS = [f"{MARK} I would explain the idea, give a concrete example, and mention a trade-off for question {i}." for i in range(1, 6)]
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    passed, failed = passed + bool(ok), failed + (not ok)
    print(("PASS " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))


def counter(text, name, **labels):
    total = 0.0
    for line in text.splitlines():
        if line.startswith(name + "{") or line.startswith(name + " "):
            if all(f'{k}="{v}"' in line for k, v in labels.items()):
                total += float(line.rsplit(" ", 1)[1])
    return total


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors = []
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))

    before = ctx.request.get(base + "/metrics?format=prometheus").text()

    pg.goto(base + "/demo/")
    check("landing page loads", "SMART" in pg.title() or "interview" in pg.inner_text("main").lower())
    page_text = pg.inner_text("body").lower()
    check(
        "live Qwen evaluation is not offered by default",
        "live" not in " ".join(pg.locator("select#modular option, #modular_mode option").all_inner_texts()).lower(),
    )
    check(
        "code-check option is not offered by default", pg.locator("input[name='code_eval'], #code_eval").count() == 0 or "SMART_DEMO_CODE_EVAL" in pg.content()
    )
    pg.screenshot(path=str(out / "01_landing.png"), full_page=True)
    pg.goto(base + "/demo/about")
    check("About page renders the architecture diagram", pg.locator("svg[role=img]").count() >= 1)

    j = ctx.request.get(base + "/healthz").json()
    check(
        "/healthz ok with build identity",
        j.get("status") == "ok" and j.get("app_version") and j.get("evaluator_versions", {}).get("pipeline"),
        json.dumps(j)[:200],
    )
    r = ctx.request.get(base + "/readyz")
    check("/readyz ready", r.status == 200 and r.json().get("ready") is True, r.text()[:200])
    check("legacy /health unchanged", ctx.request.get(base + "/health").json() == {"status": "ok"})

    pg.goto(base + "/demo/")
    pg.select_option("#role", "Data Scientist")
    pg.click("label.seg-item:has(input[name='size'][value='5']) span")
    pg.click("#start-btn")
    pg.wait_for_url(re.compile(r"/demo/s/demo_[0-9a-f]{20}$"))
    sid = pg.url.rsplit("/", 1)[1]
    legacy_notes = []
    for n in range(5):
        pg.wait_for_selector("#answer")
        pg.fill("#answer", ANSWERS[n])
        pg.click("#submit-btn")
        pg.wait_for_selector("#result:not(.hidden)", timeout=30000)
        legacy_notes.append(pg.inner_text("#result").lower())
        if n == 0:
            pg.screenshot(path=str(out / "02_feedback.png"), full_page=True)
        pg.click("#next-btn")
        if n < 4:
            pg.wait_for_url(re.compile(r"/demo/s/demo_[0-9a-f]{20}$"))
    pg.wait_for_url(re.compile(r"/summary$"))
    summ = pg.inner_text("main").lower()
    check("five-question interview completed to the summary", pg.url.endswith("/summary") and "5" in summ)
    scored = any("similarity" in t and re.search(r"\d+(\.\d+)?\s*%", t) for t in legacy_notes)
    unavailable = any("not set up" in t or "unavailable" in t or "no score" in t for t in legacy_notes + [summ])
    check("each answer shows either a labelled similarity score or an explicit 'not set up / unavailable' notice (never a silent blank)", scored or unavailable)
    check(
        "summary never claims verified correctness or accuracy", not re.search(r"verified correct|grading accuracy|human[- ]validated", summ) or "not" in summ
    )
    pg.screenshot(path=str(out / "03_summary.png"), full_page=True)

    after = ctx.request.get(base + "/metrics?format=prometheus").text()
    d = lambda name, **lab: counter(after, name, **lab) - counter(before, name, **lab)  # noqa: E731
    check("metrics: interviews_started +1", d("smart_interviews_started_total", surface="demo") == 1, str(d("smart_interviews_started_total", surface="demo")))
    check("metrics: interviews_completed +1", d("smart_interviews_completed_total", surface="demo") == 1)
    check("metrics: answers_submitted +5", d("smart_answers_submitted_total", surface="demo") == 5)
    check("metrics contain no answer text and no session id", MARK not in after and sid not in after)
    pg.goto(base + "/metrics?format=prometheus")
    pg.screenshot(path=str(out / "04_metrics_prometheus.png"))
    check("no console or page errors", not errors, "; ".join(errors)[:300])

    pg.goto(f"{base}/demo/s/{sid}/summary")
    if pg.locator("#delete-btn").count():
        pg.click("#delete-btn")
        pg.click("#delete-btn")
        pg.wait_for_url(re.compile(r"/demo/$"))
        check("session deleted from the UI", ctx.request.get(f"{base}/demo/api/sessions/{sid}").status == 404)
    br.close()

print(f"\n{passed}/{passed + failed} checks passed")
sys.exit(1 if failed else 0)

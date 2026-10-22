"""Read-only views of modular evaluator output: a side-by-side review report (Markdown + self-contained HTML) and a demonstration (CLI text or HTML) of what an
application could show: concept decisions with the candidate's own words as evidence, rubric breakdown with the rule that produced each level, abstention reason,
feedback. Nothing here scores, calls a model, or is wired into Flask.

Every view carries a source label that cannot be missed: REAL MODEL (qwen via the frozen experiment), MOCK VERIFIER (offline test double), ADVISORY ONLY (no score by
design), and always "NOT human-validated" until the human comparison has been run. The AI-authored expected band / kind appears only in the review report, in its own
clearly marked block, and never in anything a blind reviewer sees."""
from __future__ import annotations

import html
import json
import textwrap
from typing import Any, Dict, List, Optional

from .. import ModularEvaluator, ReferenceMaterial, ScopeStore
from ..feedback import build_feedback, feedback_payload
from ..mock_verifiers import LexicalMockVerifier
from ..requirements import build_requirements
from .diagnostics import abstain_taxonomy, verdict_diagnostics
from .findings import LABELS as FINDING_LABELS, reliability_summary
from .terms import STANDING_CAVEAT, describe_confidence, source_label

DIM_ORDER = ("correctness", "completeness", "relevance", "reasoning")


# ------------------------------------------------------------------------------------------------------------- building views
def requirement_view(store: ScopeStore, question_id: str, question: str) -> Dict[str, Any]:
    try:
        rs = build_requirements(store.get(question_id), question)
    except Exception:
        return {"available": False, "requirements": [], "penalty_mode": "unavailable", "flags": [], "alternatives": []}
    return {"available": True, "penalty_mode": rs.penalty_mode, "flags": list(rs.scope_flags), "alternatives": [t for t, _ in rs.alternatives],
            "requirements": [{"id": r.id, "tier": r.tier.value, "kind": r.kind, "label": r.label, "members": list(r.members), "min_required": r.min_required} for r in rs.requirements]}


def modular_view(result: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None, trace=None, repeat: Optional[int] = None) -> Dict[str, Any]:
    tax = abstain_taxonomy(result)
    return {"repeat": repeat, "source": source_label(result), "status": result["status"], "score": result["score"], "score_range": result["score_range"],
            "consistency": describe_confidence(result.get("confidence"), bool((result.get("provenance") or {}).get("human_validated"))), "confidence_raw": result.get("confidence"),
            "dimensions": [{k: d[k] for k in ("name", "weight", "level", "level_min", "level_max", "derivation")} for d in sorted(result["dimensions"], key=lambda d: DIM_ORDER.index(d["name"]) if d["name"] in DIM_ORDER else 9)],
            "outcomes": result["outcomes"], "verdicts": verdict_diagnostics(result, trace), "claims": result["claims"], "flags": result["flags"], "uncertainty_flags": result["uncertainty_flags"],
            "abstain_reasons": result["abstain_reasons"], "taxonomy": tax, "reliability": reliability_summary(result), "adjustments": result["adjustments"], "feedback": feedback, "engine": (result.get("provenance") or {}).get("engine_version"),
            "variant": (result.get("provenance") or {}).get("engine_variant")}


def legacy_view(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": r["evaluation_status"], "score": r["provisional_score"], "band": r["score_band"], "confidence": r["confidence"],
            "rubric": {k: {"level": v["level"], "why": v["justification"]} for k, v in r["rubric"].items()}, "missing": r["missing_concepts"], "errors": r["factual_errors"],
            "strengths": r["strengths"], "limitations": r["verification_limitations"], "rationale": r["score_rationale"]}


def build_views(doc: Dict[str, Any], sample: Dict[str, Dict[str, Any]], store: ScopeStore, expectations: Optional[Dict[str, Dict[str, Any]]] = None, order: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    mods: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for m in doc.get("modular", []):
        mods.setdefault(m["sample_id"], {})[m["repeat"]] = m
    leg = {l["sample_id"]: l for l in doc.get("legacy", [])}
    out = []
    for sid in (order or list(sample)):
        if sid not in mods:
            continue
        s = sample[sid]
        out.append({"sample_id": sid, "question_id": s["question_id"], "question": s["question"], "answer": s["answer_text"], "requirements": requirement_view(store, s["question_id"], s["question"]),
                    "modular": [modular_view(mods[sid][r]["result"], mods[sid][r].get("feedback"), mods[sid][r].get("verifier_trace"), r) for r in sorted(mods[sid])],
                    "legacy": legacy_view(leg[sid]["result"]) if sid in leg else None,
                    "ai_expectation": (expectations or {}).get(sid)})
    return out


def mock_view(question_id: str, question: str, answer: str, store: ScopeStore, record: Dict[str, Any]) -> Dict[str, Any]:
    """Offline demonstration on ANY question (including the advisory-only majority) through the weak lexical MOCK verifier. Shows the pipeline, not model quality."""
    ev = ModularEvaluator(store, LexicalMockVerifier())
    res = ev.evaluate(question_id, question, answer, ReferenceMaterial.from_corpus_record(record))
    fb = build_feedback(feedback_payload(res)).__dict__
    return {"sample_id": "(demo)", "question_id": question_id, "question": question, "answer": answer, "requirements": requirement_view(store, question_id, question),
            "modular": [modular_view(res.to_dict(), fb)], "legacy": None, "ai_expectation": None}


# ------------------------------------------------------------------------------------------------------------- text rendering
def _fmt_score(m: Dict[str, Any]) -> str:
    if m["score"] is not None:
        return f"{m['score']}/100"
    if m["status"] == "advisory_only":
        return "no score (advisory only)"
    rng = f" (informational range {m['score_range'][0]}-{m['score_range'][1]})" if m["score_range"] else ""
    return "no score: " + m["status"] + rng


def render_cli(view: Dict[str, Any], repeat: int = 0, width: int = 100) -> str:
    m = next((x for x in view["modular"] if x["repeat"] in (repeat, None)), view["modular"][0])
    bar = "=" * width
    L = [bar, f"{m['source']['kind']}  |  {m['source']['human']}  |  engine {m['engine']}{' variant ' + m['variant'] if m['variant'] else ''}", m["source"]["text"], bar, "",
         "QUESTION  " + view["question"][:width * 3], "", "ANSWER"] + ["  " + x for x in textwrap.wrap(view["answer"].replace("\n", " "), width - 2)[:12]] + ["",
         f"RESULT    {_fmt_score(m)}   | {m['consistency']}", f"          {STANDING_CAVEAT}"]
    if m["status"] not in ("scored", "advisory_only"):
        t = m["taxonomy"]
        L.append(f"          why no score: {t['primary']}" + (f"  ({'; '.join(sorted({b['reason'] or b['origin'] for b in t['blockers']}))})" if t["blockers"] else ""))
    L += ["", "CONCEPT DECISIONS (what the model said -> what survived the evidence gate)"]
    tier = {o["requirement_id"]: o["tier"] for o in m["outcomes"]}
    for v in m["verdicts"]:
        chg = "" if v["model_state"] == v["final_state"] else f"  [model: {v['model_state']} -> gate: {v['downgrade_reason']}]"
        L.append(f"  {v['requirement_id']:<3}{tier.get(v['requirement_id'], '?')[:4]:<5}{v['member'][:34]:<36}{v['final_state']}{chg}")
        for c in m["claims"]:
            if c["id"] in v["claim_ids"]:
                L.append(f"        evidence {c['id']}: \"{c['text'][:width - 24]}\"")
        if v.get("explanation") and v["final_state"] == "states_incorrectly":
            L.append(f"        why wrong: {v['explanation'][:width - 20]}")
    L += ["", "RUBRIC (fixed rules over verified findings; nothing here is a model score)"]
    for d in m["dimensions"]:
        lv = d["level"] if d["level"] is not None else (f"undetermined ({d['level_min']}..{d['level_max']})" if d["level_min"] is not None else "not determined")
        L.append(f"  {d['name']:<12}{d['weight']:>3} pts  level {lv}: {d['derivation'][:width - 40]}")
    fb = m.get("feedback")
    if fb:
        L += ["", "FEEDBACK (deterministic, built only from verified findings)"] + ["  " + x for x in fb["text"].split("\n")]
    if m["flags"] or m["uncertainty_flags"]:
        L += ["", "FLAGS  " + ", ".join(m["flags"] + m["uncertainty_flags"])]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------------------- markdown report
def render_markdown(views: List[Dict[str, Any]], title: str) -> str:
    L = [f"# {title}", "", "UNBLINDED review report: it shows model output next to the answer. Do not give this file to a blind reviewer. AI-authored expectations are provisional and are not ground truth.", ""]
    for v in views:
        L += [f"## {v['sample_id']} ({v['question_id']})", "", f"**Question:** {v['question']}", "", "**Candidate answer:**", "", "```text", v["answer"], "```", "", "**Essential requirements (AI-drafted):**", ""]
        L += [f"- {r['id']} [{r['tier']}] {r['label']}" + (f" (any {r['min_required']} of {r['members']})" if r["kind"] == "group" else "") for r in v["requirements"]["requirements"] if r["tier"] == "essential"]
        for m in v["modular"]:
            L += ["", f"### Modular, repeat {m['repeat']}: {_fmt_score(m)} ({m['source']['kind']}; {m['source']['human']}; {m['consistency']})", "",
                  "| req | tier | concept | model said | final | gate reason | evidence |", "|---|---|---|---|---|---|---|"]
            tier = {o["requirement_id"]: o["tier"] for o in m["outcomes"]}
            for x in m["verdicts"]:
                ev = "; ".join(c["text"][:70].replace("\n", " ") for c in m["claims"] if c["id"] in x["claim_ids"])
                L.append(f"| {x['requirement_id']} | {tier.get(x['requirement_id'])} | {x['member']} | {x['model_state']} | {x['final_state']} | {x['downgrade_reason'] or ''} | {ev} |")
            L += ["", "Rubric: " + "; ".join(f"{d['name']} {d['level']} ({d['derivation']})" for d in m["dimensions"])]
            if m["status"] == "abstained":
                L.append(f"Abstained: {m['taxonomy']['primary']}; reasons {m['abstain_reasons']}; range {m['score_range']}")
        if v["legacy"]:
            g = v["legacy"]
            L += ["", f"### Legacy: {g['score']} ({g['status']}, confidence {g['confidence']})", "", f"Missing concepts: {g['missing']}", "", f"Factual errors: {[e['claim_quote'][:80] for e in g['errors']]}"]
        if v["ai_expectation"]:
            a = v["ai_expectation"]
            L += ["", f"> AI-authored provisional expectation (NOT human-reviewed): kind `{a.get('kind')}`, band {a.get('expected_score_min')}-{a.get('expected_score_max')}. {a.get('rationale', '')}"]
        L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------------------- html
_CSS = """:root{--bg:#fff;--fg:#1c1c1e;--mute:#6b6b70;--line:#d8d8de;--card:#f7f7f9;--good:#15803d;--bad:#b91c1c;--warn:#a16207;--acc:#1d4ed8;--gbg:#dcfce7;--bbg:#fee2e2;--ybg:#fef9c3}
@media (prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#ececf0;--mute:#9a9aa3;--line:#33333b;--card:#1e1e24;--good:#4ade80;--bad:#f87171;--warn:#facc15;--acc:#7aa2ff;--gbg:#14351f;--bbg:#3b1717;--ybg:#3a3414}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,Segoe UI,sans-serif}main{max-width:1280px;margin:0 auto;padding:16px}
h1{font-size:20px}h2{font-size:17px;margin:0}h3{font-size:14px;margin:12px 0 4px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 20px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}.col{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px 12px;min-width:0}
pre{white-space:pre-wrap;word-wrap:break-word;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;margin:6px 0;font:13px/1.5 ui-monospace,Consolas,monospace}
table{border-collapse:collapse;width:100%;font-size:12.5px}td,th{border-bottom:1px solid var(--line);padding:3px 6px;text-align:left;vertical-align:top}th{color:var(--mute);font-weight:600}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11.5px;font-weight:600;border:1px solid var(--line);margin-right:4px}
.real{background:#dbeafe;color:#1e3a8a;border-color:#93c5fd}.mock{background:var(--ybg);color:var(--warn)}.adv{background:#e5e7eb;color:#374151}.nohv{color:var(--mute)}
.good{background:var(--gbg)}.bad{background:var(--bbg)}.unv{background:var(--ybg)}.inj{text-decoration:underline wavy var(--bad)}.muted{color:var(--mute)}
.big{font-size:22px;font-weight:700}.ai{border:1px dashed var(--line);padding:8px 10px;border-radius:8px;color:var(--mute);margin-top:12px}
.s-correct{color:var(--good);font-weight:600}.s-incorrect{color:var(--bad);font-weight:600}.s-unverified{color:var(--warn);font-weight:600}
nav a{margin-right:10px}"""
_STATE_CLS = {"states_correctly": "s-correct", "states_incorrectly": "s-incorrect", "unverified": "s-unverified", "not_stated": "muted"}


def _chip(src: Dict[str, Any]) -> str:
    cls = {"REAL MODEL": "real", "MOCK VERIFIER": "mock", "ADVISORY ONLY": "adv"}
    tags = "".join(f'<span class="chip {cls.get(t, "adv")}">{html.escape(t)}</span>' for t in src.get("tags") or [src["kind"]])
    return tags + f'<span class="chip nohv">{html.escape(src["human"])}</span>'


def _highlight(answer: str, m: Dict[str, Any]) -> str:
    role: Dict[str, str] = {}
    for v in m["verdicts"]:
        for cid in v["claim_ids"]:
            role[cid] = "bad" if v["final_state"] == "states_incorrectly" else role.get(cid, "good") if v["final_state"] == "states_correctly" else role.get(cid, "")
        for cid in v.get("model_claim_ids") or []:
            if v["downgrade_reason"] and cid not in role:
                role[cid] = "unv"
    out, pos = [], 0
    for c in sorted(m["claims"], key=lambda c: c["start"]):
        out.append(html.escape(answer[pos:c["start"]]))
        cls = role.get(c["id"], "") + (" inj" if "possible_instruction" in c["flags"] else "")
        out.append(f'<span class="{cls.strip()}" title="claim {c["id"]}">{html.escape(answer[c["start"]:c["end"]])}</span>')
        pos = c["end"]
    out.append(html.escape(answer[pos:]))
    return "".join(out)


def _modular_html(v: Dict[str, Any], m: Dict[str, Any]) -> str:
    tier = {o["requirement_id"]: o["tier"] for o in m["outcomes"]}
    rows = []
    for x in m["verdicts"]:
        ev = "<br>".join(f'<span class="muted">{c["id"]}</span> {html.escape(c["text"][:140])}' for c in m["claims"] if c["id"] in x["claim_ids"])
        gate = "" if x["model_state"] == x["final_state"] else f'<br><span class="muted">model said {x["model_state"]}; gate: {html.escape(x["downgrade_reason"] or "")}</span>'
        sup = f'<br><span class="muted">credit support: {x["credit_support"]}{(" (words also in " + ", ".join(x["found_in_other_claims"]) + ")") if x.get("found_in_other_claims") else ""}</span>' if x.get("credit_support") and x["credit_support"] != "corroborated" else ""
        note = f'<br><span class="muted">{html.escape(x.get("note", ""))}</span>' if x.get("note") else ""
        note += f'<br><span class="muted">finding: {html.escape(FINDING_LABELS.get(x.get("finding_class"), ""))}</span>' if x.get("finding_class") else ""
        rows.append(f'<tr><td>{x["requirement_id"]}<br><span class="muted">{(tier.get(x["requirement_id"]) or "")[:4]}</span></td><td>{html.escape(x["member"])}</td>'
                    f'<td class="{_STATE_CLS.get(x["final_state"], "")}">{x["final_state"]}{gate}{sup}{note}</td><td>{ev}</td></tr>')
    dims = "".join(f'<tr><td>{d["name"]}</td><td>{d["weight"]}</td><td>{d["level"] if d["level"] is not None else "undetermined " + str(d["level_min"]) + ".." + str(d["level_max"])}</td><td class="muted">{html.escape(d["derivation"])}</td></tr>' for d in m["dimensions"])
    why = ""
    if m["status"] not in ("scored", "advisory_only"):
        t = m["taxonomy"]
        why = f'<p><b>Why no score:</b> {t["primary"]}' + (f' <span class="muted">({html.escape("; ".join(sorted({b["reason"] or b["origin"] for b in t["blockers"]})))})</span>' if t["blockers"] else "") + "</p>"
    fb = f'<h3>Feedback (deterministic, verified findings only)</h3><pre>{html.escape(m["feedback"]["text"])}</pre>' if m.get("feedback") else ""
    return (f'<div class="col"><div>{_chip(m["source"])}<span class="chip">repeat {m["repeat"]}</span></div><div class="big">{html.escape(_fmt_score(m))}</div>'
            f'<div class="muted">{html.escape(m["consistency"])}. {STANDING_CAVEAT}</div>{why}<h3>Answer with evidence</h3><pre>{_highlight(v["answer"], m)}</pre>'
            f'<p class="muted"><span class="good">green</span> credited · <span class="bad">red</span> blamed · <span class="unv">yellow</span> cited by the model but rejected by the gate</p>'
            f'<h3>Concept decisions</h3><table><tr><th>req</th><th>concept</th><th>final state</th><th>evidence (candidate\'s words)</th></tr>{"".join(rows)}</table>'
            f'<h3>Rubric</h3><table><tr><th>dimension</th><th>pts</th><th>level</th><th>rule</th></tr>{dims}</table>{fb}</div>')


def _legacy_html(g: Dict[str, Any]) -> str:
    rub = "".join(f'<tr><td>{k}</td><td>{x["level"]}</td><td class="muted">{html.escape(x["why"])}</td></tr>' for k, x in g["rubric"].items())
    errs = "".join(f'<li>{html.escape(e["claim_quote"][:120])} <span class="muted">— {html.escape(e["explanation"][:140])}</span></li>' for e in g["errors"]) or "<li class=muted>none</li>"
    return (f'<div class="col"><div><span class="chip real">LEGACY EVALUATOR</span><span class="chip nohv">NOT human-validated</span></div><div class="big">{g["score"]}/100</div>'
            f'<div class="muted">{g["status"]} · confidence {g["confidence"]} (a model self-report)</div><h3>Rubric (model-assigned)</h3><table><tr><th>dimension</th><th>level</th><th>justification</th></tr>{rub}</table>'
            f'<h3>Missing concepts</h3><p>{html.escape("; ".join(g["missing"])) or "<span class=muted>none</span>"}</p><h3>Factual errors</h3><ul>{errs}</ul></div>')


def render_html(views: List[Dict[str, Any]], title: str, *, unblinded_ai: bool = True) -> str:
    nav = "".join(f'<a href="#{html.escape(v["sample_id"])}">{html.escape(v["sample_id"])}</a>' for v in views)
    cards = []
    for v in views:
        reqs = "".join(f'<li><b>{r["id"]}</b> <span class="muted">[{r["tier"]}]</span> {html.escape(r["label"])}' + (f' <span class="muted">(any {r["min_required"]} of {html.escape("; ".join(r["members"]))})</span>' if r["kind"] == "group" else "") + "</li>"
                       for r in v["requirements"]["requirements"] if r["tier"] == "essential") or "<li class=muted>none drafted</li>"
        cols = "".join(_modular_html(v, m) for m in v["modular"]) + (_legacy_html(v["legacy"]) if v["legacy"] else "")
        ai = ""
        if unblinded_ai and v.get("ai_expectation"):
            a = v["ai_expectation"]
            ai = (f'<div class="ai"><b>AI-authored provisional expectation (not human-reviewed, not ground truth):</b> kind <code>{html.escape(str(a.get("kind")))}</code>, band '
                  f'{a.get("expected_score_min")}–{a.get("expected_score_max")}. {html.escape(a.get("rationale", ""))}</div>')
        mode = v["requirements"]["penalty_mode"]
        cards.append(f'<section class="card" id="{html.escape(v["sample_id"])}"><h2>{html.escape(v["sample_id"])} <span class="muted">{v["question_id"]}</span> '
                     f'{'<span class="chip">scope-eligible: scored</span>' if mode == "full" else '<span class="chip adv">advisory-only question: no score by design</span>'}</h2>'
                     f'<p><b>Question.</b> {html.escape(v["question"])}</p><h3>Essential requirements (AI-drafted, not human-verified)</h3><ul>{reqs}</ul><div class="cols">{cols}</div>{ai}</section>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{_CSS}</style></head>'
            f'<body><main><h1>{html.escape(title)}</h1><p class="muted">Read-only. UNBLINDED: not for a blind reviewer. Results are labelled by source; no number here is human-validated unless it says so.</p><nav>{nav}</nav>{"".join(cards)}</main></body></html>')

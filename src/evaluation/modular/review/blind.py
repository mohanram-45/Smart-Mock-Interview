"""Genuinely blind human-review exports (CSV for a spreadsheet, Markdown, and a self-contained HTML form) for ANY answer set, e.g. the 20 evaluated answers or all
120 bench_v2 answers.

BLINDNESS CONTRACT (enforced by tests): a blind file contains only the question, the candidate answer and the AI-DRAFTED essential requirements (labelled as AI
drafted, possibly wrong). It never contains a model score, a verdict, an abstention, the AI-expected band or answer kind, the source answer id, or which system
produced anything. The review_id -> source id key is a separate file the reviewer is never given.

The CSV header is the one used by the frozen Stage 3C-2 blind sheet, so a sheet produced here and one produced earlier are read by the same importer."""
from __future__ import annotations

import csv
import html
import io
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..requirements import Tier, build_requirements
from ..scope import ScopeStore
from .recovery import atomic_write_text

HEADER = ["review_id", "interview_question", "candidate_answer", "essential_requirements_ai_drafted",
          "technical_correctness (correct / partly_correct / incorrect)", "completeness (complete / partial / minimal)",
          "requirement_judgements (per requirement: stated_correctly / stated_incorrectly / not_stated)", "reviewer_score_0_100", "reviewer_comments", "reviewer_id"]
TECH = ["correct", "partly_correct", "incorrect", "cannot_judge"]
COMP = ["complete", "partial", "minimal", "cannot_judge"]
REQ = ["stated_correctly", "stated_incorrectly", "not_stated"]
INTRO = ("Please judge each answer yourself. Do not look at any model output. The essential requirements below were drafted by an AI and are NOT human-verified: "
         "if you think a requirement is wrong or too coarse, say so in the comments. Fill the blank fields; leave nothing pre-filled.")


def requirement_text(question_id: str, question: str, store: ScopeStore) -> Dict[str, Any]:
    """AI-drafted essential requirements for a question, as the reviewer sees them, and whether the question is scope-eligible for automatic scoring."""
    try:
        rs = build_requirements(store.get(question_id), question)
    except Exception:
        return {"text": "(no requirement list is available for this question: judge the answer overall)", "ids": [], "eligible": False}
    lines, ids = [], []
    for r in rs.essentials():
        if r.is_group:
            lines.append(f"{r.id}: at least {r.min_required} of [{'; '.join(r.members)}]")
        else:
            lines.append(f"{r.id}: {r.label}")
        ids.append(r.id)
    if not lines:
        lines = ["(no essential requirements were drafted for this question: judge the answer overall)"]
    return {"text": "\n".join(lines), "ids": ids, "eligible": rs.penalty_mode == "full"}


def load_bench_v2(root: Path) -> List[Dict[str, Any]]:
    d = Path(root) / "data" / "evaluation" / "bench_v2"
    qs = {r["question_id"]: r for r in map(json.loads, filter(None, (d / "questions.jsonl").read_text(encoding="utf-8").splitlines()))}
    out = []
    for l in (d / "answers.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            a = json.loads(l)
            out.append({"source_id": a["answer_id"], "question_id": a["question_id"], "question": qs[a["question_id"]]["question"], "answer_text": a["answer_text"]})
    return out


def load_sample(root: Path, name: str = "stage3c2") -> List[Dict[str, Any]]:
    p = Path(root) / "data" / "evaluation" / name / "sample.jsonl"
    return [{"source_id": r["sample_id"], "question_id": r["question_id"], "question": r["question"], "answer_text": r["answer_text"]}
            for r in map(json.loads, filter(None, p.read_text(encoding="utf-8").splitlines()))]


def make_rows(items: List[Dict[str, Any]], store: ScopeStore, *, seed: int = 20261015, prefix: str = "r") -> Dict[str, Any]:
    """Shuffle (seeded, so the order carries no information about kind or id) and number the items. Returns {rows, key, meta}."""
    order = list(items)
    random.Random(seed).shuffle(order)
    width = max(2, len(str(len(order))))
    rows, key, meta = [], {}, {}
    for i, it in enumerate(order, 1):
        rid = f"{prefix}{i:0{width}d}"
        req = requirement_text(it["question_id"], it["question"], store)
        rows.append({"review_id": rid, "interview_question": it["question"], "candidate_answer": it["answer_text"], "essential_requirements_ai_drafted": req["text"], "requirement_ids": req["ids"]})
        key[rid] = it["source_id"]
        meta[rid] = {"question_id": it["question_id"], "scope_eligible": req["eligible"]}
    return {"rows": rows, "key": key, "meta": meta, "seed": seed}


def to_csv(rows: Iterable[Dict[str, Any]]) -> str:
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADER)
    for r in rows:
        w.writerow([r["review_id"], r["interview_question"], r["candidate_answer"], r["essential_requirements_ai_drafted"], "", "", "", "", "", ""])
    return buf.getvalue()


def to_markdown(rows: Iterable[Dict[str, Any]], title: str) -> str:
    L = [f"# {title}", "", INTRO, "", "Scale hint (optional): technical_correctness = is what the candidate says right? completeness = does it cover what the question needs? reviewer_score_0_100 = your overall mark.", ""]
    for r in rows:
        L += [f"## {r['review_id']}", "", f"**Question:** {r['interview_question']}", "", "**Candidate answer:**", "", "```text", r["candidate_answer"], "```", "",
              "**Essential requirements (AI-drafted):**", ""] + [f"- {x}" for x in r["essential_requirements_ai_drafted"].split("\n")] + ["",
              "| Field | Your judgement |", "|---|---|", "| Technical correctness (correct / partly_correct / incorrect) | |", "| Completeness (complete / partial / minimal) | |",
              "| Per requirement (stated_correctly / stated_incorrectly / not_stated) | |", "| Score 0-100 | |", "| Comments | |", "| Reviewer id | |", ""]
    return "\n".join(L)


def rows_from_csv(path: Path) -> List[Dict[str, Any]]:
    """Rows of an existing blind sheet (e.g. the frozen Stage 3C-2 sheet), so an HTML form can be built from it without regenerating anything."""
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            out.append({"review_id": r["review_id"], "interview_question": r["interview_question"], "candidate_answer": r["candidate_answer"],
                        "essential_requirements_ai_drafted": r["essential_requirements_ai_drafted"],
                        "requirement_ids": re.findall(r"^([EGS]\d+):", r["essential_requirements_ai_drafted"], flags=re.M)})
    return out


_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{--bg:#fff;--fg:#1c1c1e;--mute:#6b6b70;--line:#d8d8de;--card:#f7f7f9;--acc:#1d4ed8}
@media (prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#ececf0;--mute:#9a9aa3;--line:#33333b;--card:#1e1e24;--acc:#7aa2ff}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;z-index:2;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
main{max-width:860px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 18px}
.card.done{border-left:4px solid #16a34a}
pre{white-space:pre-wrap;word-wrap:break-word;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;margin:6px 0;font:13px/1.45 ui-monospace,Consolas,monospace}
label{display:block;font-size:13px;color:var(--mute);margin:10px 0 3px}select,input,textarea{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:5px 8px}
textarea{width:100%;box-sizing:border-box;min-height:54px}.req{display:flex;gap:8px;align-items:center;margin:4px 0;flex-wrap:wrap}.req span{flex:1 1 260px}
button{font:inherit;padding:6px 14px;border-radius:8px;border:1px solid var(--acc);background:var(--acc);color:#fff;cursor:pointer}
.note{color:var(--mute);font-size:13px}.rid{font-weight:700}
</style></head><body>
<header><b>__TITLE__</b><span id="prog" class="note"></span><label style="margin:0">Reviewer id <input id="reviewer" size="12"></label><button id="dl">Download CSV</button></header>
<main><p class="note">__INTRO__ Answers autosave in this browser; press <b>Download CSV</b> when finished (it can be re-downloaded at any time).</p>
__CARDS__
</main><script>
const DATA=__DATA__;const KEY="blind_review___SETID__";
const TECH=__TECH__,COMP=__COMP__,REQ=__REQ__;
let st={};try{st=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}}
function g(id,f){return (st[id]||{})[f]||""}
function set(id,f,v){st[id]=st[id]||{};st[id][f]=v;save();progress()}
function progress(){let n=0;DATA.forEach(r=>{const done=g(r.id,"score")!=="";document.getElementById("c_"+r.id).classList.toggle("done",done);if(done)n++});document.getElementById("prog").textContent=n+" / "+DATA.length+" scored"}
document.querySelectorAll("[data-id]").forEach(el=>{const id=el.dataset.id,f=el.dataset.f;el.value=g(id,f);el.addEventListener("input",()=>set(id,f,el.value))});
const rv=document.getElementById("reviewer");rv.value=(st.__reviewer||"");rv.addEventListener("input",()=>{st.__reviewer=rv.value;save()});
function q(s){s=String(s==null?"":s);return /[",\\n\\r]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s}
document.getElementById("dl").onclick=()=>{
 const H=__HEADER__;const out=[H.map(q).join(",")];
 DATA.forEach(r=>{const rj=r.req.map(x=>x+": "+g(r.id,"req_"+x)).filter(x=>!x.endsWith(": "));
  out.push([r.id,r.q,r.a,r.reqs,g(r.id,"tech"),g(r.id,"comp"),rj.join("\\n"),g(r.id,"score"),g(r.id,"comments"),rv.value].map(q).join(","))});
 const b=new Blob(["\\ufeff"+out.join("\\n")],{type:"text/csv"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="blind_review_completed.csv";a.click()};
progress();
</script></body></html>"""


def _opts(values, blank="— choose —"):
    return f'<option value="">{blank}</option>' + "".join(f'<option value="{v}">{v}</option>' for v in values)


def to_html(rows: List[Dict[str, Any]], title: str, set_id: str) -> str:
    cards, data = [], []
    for r in rows:
        rid = r["review_id"]
        reqs = "".join(f'<div class="req"><span>{html.escape(x)}</span><select data-id="{rid}" data-f="req_{x.split(":")[0]}">{_opts(REQ)}</select></div>'
                       for x in r["essential_requirements_ai_drafted"].split("\n") if re.match(r"^[EGS]\d+:", x)) or '<div class="note">No per-requirement list: judge overall.</div>'
        cards.append(f'<section class="card" id="c_{rid}"><div class="rid">{rid}</div><p><b>Question.</b> {html.escape(r["interview_question"])}</p>'
                     f'<b>Candidate answer</b><pre>{html.escape(r["candidate_answer"])}</pre>'
                     f'<b>Essential requirements (AI-drafted, may be wrong)</b><pre>{html.escape(r["essential_requirements_ai_drafted"])}</pre>'
                     f'<label>Technical correctness: is what the candidate says right?</label><select data-id="{rid}" data-f="tech">{_opts(TECH)}</select>'
                     f'<label>Completeness: does it cover what the question needs?</label><select data-id="{rid}" data-f="comp">{_opts(COMP)}</select>'
                     f'<label>Per requirement</label>{reqs}'
                     f'<label>Your score 0-100</label><input type="number" min="0" max="100" data-id="{rid}" data-f="score">'
                     f'<label>Comments (also say if a requirement is wrong or too coarse)</label><textarea data-id="{rid}" data-f="comments"></textarea></section>')
        data.append({"id": rid, "q": r["interview_question"], "a": r["candidate_answer"], "reqs": r["essential_requirements_ai_drafted"],
                     "req": [x.split(":")[0] for x in r["essential_requirements_ai_drafted"].split("\n") if re.match(r"^[EGS]\d+:", x)]})
    page = (_HTML.replace("__TITLE__", html.escape(title)).replace("__INTRO__", html.escape(INTRO)).replace("__CARDS__", "\n".join(cards))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")).replace("__SETID__", re.sub(r"\W", "_", set_id))
            .replace("__TECH__", json.dumps(TECH)).replace("__COMP__", json.dumps(COMP)).replace("__REQ__", json.dumps(REQ)).replace("__HEADER__", json.dumps(HEADER)))
    return page


def write_blind_set(rows: List[Dict[str, Any]], out_dir: Path, *, title: str, set_id: str, key: Optional[Dict[str, str]] = None, meta: Optional[Dict[str, Any]] = None,
                    write_csv: bool = True) -> Dict[str, str]:
    out_dir = Path(out_dir)
    paths = {}
    if write_csv:
        atomic_write_text(out_dir / "blind_review_sheet.csv", to_csv(rows)); paths["csv"] = str(out_dir / "blind_review_sheet.csv")
        atomic_write_text(out_dir / "blind_review_sheet.md", to_markdown(rows, title)); paths["md"] = str(out_dir / "blind_review_sheet.md")
    atomic_write_text(out_dir / "blind_review.html", to_html(rows, title, set_id)); paths["html"] = str(out_dir / "blind_review.html")
    if key is not None:
        atomic_write_text(out_dir / "review_key.json", json.dumps(key, indent=1, sort_keys=True)); paths["key"] = str(out_dir / "review_key.json")
        atomic_write_text(out_dir / "review_meta.json", json.dumps(meta or {}, indent=1, sort_keys=True)); paths["meta"] = str(out_dir / "review_meta.json")
    return paths


# --------------------------------------------------------------------------------------------------------------- blindness check
def blindness_violations(text: str, source_ids: Iterable[str]) -> List[str]:
    """Things that must never appear in anything a reviewer sees. Used by tests and by the CLI before it tells you a file is safe to hand over."""
    bad = []
    for sid in source_ids:
        if sid and re.search(rf"(?<![A-Za-z0-9]){re.escape(sid)}(?![A-Za-z0-9])", text):
            bad.append(f"source id {sid}")
    for tok in ("modular", "legacy", "qwen", "abstain", "states_correctly", "states_incorrectly", "expected_score", "provisional", "hallucinated", "concise_sufficient",
                "valid_alternative", "injection_with_correct", "correct_full", "off_topic", "non_substantive", "ai_provisional"):
        if re.search(tok, text, re.I):
            bad.append(f"token {tok}")
    return bad

"""Stage 10M: per-case trace of a real Windows opportunity run, replayed through the CURRENT rules. No model is called.

  python scripts/stage10m_trace.py [--results tmp/stage10_opps_<stamp>/results.json] [--out reports/stage10m_trace] [--cases T01,T02,...]

For every technical case in the run: the candidate answer, the vetted concepts with their depth state (absent | mentioned | explained) and the open ones, the TARGET, each recorded model question with
the rejection codes it got on Windows, and what the current rules say about the SAME question (under both purposes; Windows keeps only question, decision, skip_reason and memory_id, so purpose and
quote are stand-ins). Memory cases are replayed in the mode the recorded attempt used. The replay shows which rules fire now. It is NOT a model run and not a quality verdict: the 'verdict' column is
left for a person ("rejection correct? question useful?") and is never filled in here."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, opportunity_eval as OE  # noqa: E402


def newest_results() -> Path:
    c = sorted((ROOT / "tmp").glob("stage10_opps_*/results.json"))
    if not c:
        raise SystemExit("no tmp/stage10_opps_*/results.json found: pass --results")
    return c[-1]


def replay_attempt(ctx, d, quote):
    mode = d.get("mode") or "standard"
    out = {}
    for purpose in ("deepen", "probe_concept"):
        raw = {"decision": d.get("decision") or "ask", "skip_reason": d.get("skip_reason") or "none", "question": d.get("question") or "", "purpose": purpose, "concept_id": "none", "answer_quote": quote,
               "memory_id": d.get("memory_id") or "none"}
        prop, reasons = FL.validate(raw, ctx, mode if (mode == "memory" and ctx.memory_lead) else "standard")
        out[purpose] = "accepted" + (f" {prop.notes}" if prop is not None and prop.notes else "") if prop is not None else list(reasons)
    return mode, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=None)
    ap.add_argument("--out", default=str(ROOT / "reports" / "stage10m_trace"))
    ap.add_argument("--cases", default="")
    a = ap.parse_args()
    path = Path(a.results) if a.results else newest_results()
    run = json.loads(path.read_text(encoding="utf-8"))["results"][0]
    want = {x.strip() for x in a.cases.split(",") if x.strip()}
    data = OE.load()
    cases = {c["id"]: c for c in data["cases"]}
    eng = OE.offline_engine()
    L = [f"# Stage 10M trace of `{path.name if path.parent.name == '.' else path.parent.name}/{path.name}`", "",
         f"Run: prompt `{run.get('prompt_version')}`, model `{run.get('model') or run.get('models')}`. Replay = current rules on the recorded questions; **not a model run, not a quality verdict.**", ""]
    trace = []
    for r in run["rows"]:
        c = cases.get(r["id"])
        if not c or c["mode"] != "technical" or (want and r["id"] not in want):
            continue
        ctx, offered, s, core = OE.build_case(eng, c)
        st = ctx.states()
        opens = FL.open_concepts(ctx)
        tgt = FL.target_concept(ctx)
        quote = " ".join(c["answer"].split()[:5])
        atts = []
        for d in r.get("debug") or []:
            mode, now = replay_attempt(ctx, d, quote)
            atts.append({"attempt": d.get("attempt"), "mode": mode, "question": d.get("question"), "decision": d.get("decision"), "skip_reason": d.get("skip_reason"), "memory_id": d.get("memory_id"),
                         "recorded_reasons": d.get("reasons"), "now": now})
        row = {"id": r["id"], "class": c["class"], "answer": c["answer"], "why": c["why"], "concepts": {x["id"]: [x["label"], st[x["id"]]] for x in ctx.concepts}, "open": [x["label"] for x in opens],
               "target": tgt["label"] if tgt else None, "opportunity": FL.opportunity_class(ctx), "outcome": r.get("outcome"), "reasons": r.get("reasons"), "memory_stage": r.get("memory_stage"),
               "mode_trace": r.get("mode_trace"), "offered_then": r.get("offered_memory"), "offered_now": len(offered), "accepted_question": r.get("question"), "attempts": atts,
               "human_verdict": {"rejection_correct": None, "question_useful": None, "note": ""}}
        trace.append(row)
        L += [f"## {row['id']} ({row['class']}) outcome `{row['outcome']}` {row['reasons'] or ''}", f"- candidate answer: {row['answer']}", f"- fixture reason: {row['why']}",
              f"- concepts (state): " + "; ".join(f"{k} {v[0]} [{v[1]}]" for k, v in row["concepts"].items()), f"- open: {row['open']}; TARGET: {row['target']}; opportunity: {row['opportunity']}",
              f"- memory: stage `{row['memory_stage']}`, modes {row['mode_trace']}, offered then {row['offered_then']} / now {row['offered_now']}", f"- accepted question: {row['accepted_question'] or '(none)'}"]
        for t in atts:
            L.append(f"  - attempt {t['attempt']} ({t['mode']}): \"{t['question']}\" decision={t['decision']} skip_reason={t['skip_reason']} memory_id={t['memory_id']}; Windows: {t['recorded_reasons'] or 'accepted'}; "
                     f"now deepen: {t['now']['deepen']}; now probe_concept: {t['now']['probe_concept']}")
        L.append("- human verdict (rejection correct? question useful?): _unrated_")
        L.append("")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "trace.md").write_text("\n".join(L), encoding="utf-8")
    (out / "trace.json").write_text(json.dumps({"source": str(path), "rows": trace}, indent=1, default=str), encoding="utf-8")
    print(f"wrote {out / 'trace.md'} ({len(trace)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

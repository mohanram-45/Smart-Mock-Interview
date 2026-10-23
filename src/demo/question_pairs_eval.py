"""Stage 10N: judge hand-written candidate questions with the production validator (no model involved).

Separates the validator's two error kinds: a FALSE REJECTION (a reasonable question refused) and a FALSE ACCEPTANCE (a repeat, a given-away answer, an affirmed misconception, a covered or invented
topic let through). The pairs are author judgements, not human ratings. 'known_gap' pairs are bad questions the rule-based validator cannot detect; they are counted separately and never hidden."""
import json
from pathlib import Path
from typing import Any, Dict, List

from . import followup_llm as FL, opportunity_eval as OE

DATA = Path(__file__).parent / "eval_data" / "stage10n_question_pairs_v1.json"


def load() -> Dict[str, Any]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _context(item: Dict[str, Any], engine, cases: Dict[str, Any]) -> FL.Context:
    if item["src"] == "fixture":
        return OE.build_case(engine, cases[item["id"]])[0]
    concepts = [{"id": i, "label": lab, "tier": "essential", "members": [lab]} for i, lab in item["concepts"]]
    return FL.Context(role="Data Scientist", stage="core", question_id="q", question=item["question"], topic=item["question"], answer=item["answer"], concepts=concepts, reference=item.get("reference", ""), domain=item.get("domain", "d"))


def judge(q: str, ctx: FL.Context) -> tuple:
    tgt = FL.target_concept(ctx)
    payload = {"decision": "ask", "question": q, "purpose": "probe_concept", "concept_id": (tgt or {}).get("id", "none"), "memory_id": "none"}
    p, why = FL.validate(payload, ctx)
    return p is not None, why


def run(engine=None) -> Dict[str, Any]:
    engine = engine or OE.offline_engine()
    cases = {c["id"]: c for c in OE.load()["cases"]}
    FL.set_vocabulary_source(lambda: [])
    rows: List[Dict[str, Any]] = []
    try:
        for it in load()["items"]:
            ctx = _context(it, engine, cases)
            for q in it["good"]:
                ok, why = judge(q, ctx)
                rows.append({"id": it["id"], "src": it["src"], "kind": "good", "question": q, "accepted": ok, "reasons": why, "correct": ok})
            for b in it["bad"]:
                ok, why = judge(b["q"], ctx)
                rows.append({"id": it["id"], "src": it["src"], "kind": "bad", "question": b["q"], "why": b["why"], "known_gap": bool(b.get("known_gap")), "accepted": ok, "reasons": why, "correct": not ok})
    finally:
        FL.set_vocabulary_source(None)

    def part(src):
        r = [x for x in rows if src is None or x["src"] == src]
        good = [x for x in r if x["kind"] == "good"]
        bad = [x for x in r if x["kind"] == "bad"]
        det = [x for x in bad if not x["known_gap"]]
        return {"n_good": len(good), "false_rejections": sum(1 for x in good if not x["accepted"]),
                "n_bad": len(bad), "false_acceptances": sum(1 for x in bad if x["accepted"]),
                "n_bad_detectable": len(det), "false_acceptances_detectable": sum(1 for x in det if x["accepted"]),
                "known_gap_accepted": sum(1 for x in bad if x["known_gap"] and x["accepted"]), "known_gap_total": sum(1 for x in bad if x["known_gap"])}
    return {"rows": rows, "fixture": part("fixture"), "holdout": part("holdout"), "holdout2": part("holdout2"), "all": part(None)}

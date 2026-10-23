"""Stage 11: compare Stage 10 benchmark runs side by side (baseline engine vs objective engine, and any models you ran), apply the pre-registered adoption gates, and build ONE blinded human-review pack.

  .bot\\Scripts\\python.exe scripts\\stage11_compare.py --runs tmp\\A\\results.json tmp\\B\\results.json [--baseline tmp\\A\\results.json] --out tmp\\stage11_compare

Every run is labelled with its evidence kind (`real_model`, or `selftest_fake_server` which is never a measurement). Nothing here ranks a model: the table reports, the gates decide only whether the OBJECTIVE ENGINE
may replace the Stage 10N engine for the SAME model, on the SAME frozen fixture. Human ratings are never filled in by this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GATES = [   # pre-registered before any real objective-engine run; (id, description)
    ("G1", "technical expected follow-ups >= baseline"),
    ("G2", "grounded memory use >= baseline and >= 4 of the memory-use cases"),
    ("G3", "fabricated memory references == 0"),
    ("G4", "strict skips all correct (no regression)"),
    ("G5", "rows with inconsistent payloads == 0"),
    ("G6", "fallbacks <= baseline"),
    ("G7", "overall eligible rate >= baseline"),
    ("G8", "median warm latency <= 1.5 x baseline"),
    ("G9", "blinded human review: technical accuracy and naturalness not worse than baseline (requires RATED sheets; unrated = NOT MET)"),
]


def digest(run: dict, source: str) -> dict:
    E = run.get("eligible") or {}
    bc = run.get("by_class") or {}
    mem = bc.get("memory_use") or {}
    return {"source": source, "engine": run.get("engine", "stage10n"), "model": run.get("model"), "prompt": run.get("prompt_version"), "evidence": run.get("evidence_kind"),
            "eligible": E.get("n"), "success": E.get("success"), "rate": E.get("rate"), "technical": E.get("technical_expected"), "behavioural_scripted": E.get("behavioural_scripted_probes"),
            "memory_grounded": E.get("memory_use_grounded"), "memory_offered": mem.get("offered_memory"), "fabricated": (run.get("quality_gates") or {}).get("fabricated_memory_references"),
            "strict_skip": [(bc.get("skip") or {}).get("success"), (bc.get("skip") or {}).get("n_strict")], "fallbacks": sum(d.get("fell_back", 0) for d in bc.values()),
            "inconsistent_payload_rows": (run.get("payload_consistency") or {}).get("rows_with_inconsistent_payload"), "median_warm_ms": (run.get("warm_latency_ms") or {}).get("median"),
            "p95_warm_ms": (run.get("warm_latency_ms") or {}).get("p95"), "model_calls": run.get("model_calls"), "ollama": run.get("ollama_version")}


def gates(base: dict, new: dict, rated: dict | None) -> list:
    def ge(a, b):
        return a is not None and b is not None and a >= b
    out = []
    out.append(("G1", ge((new["technical"] or [None])[0], (base["technical"] or [None])[0])))
    out.append(("G2", ge((new["memory_grounded"] or [None])[0], (base["memory_grounded"] or [None])[0]) and ((new["memory_grounded"] or [0])[0] or 0) >= 4))
    out.append(("G3", new["fabricated"] == 0))
    out.append(("G4", new["strict_skip"][0] is not None and new["strict_skip"][0] == new["strict_skip"][1]))
    out.append(("G5", new["inconsistent_payload_rows"] == 0))
    out.append(("G6", ge(base["fallbacks"], new["fallbacks"])))
    out.append(("G7", ge(new["success"], base["success"])))
    out.append(("G8", new["median_warm_ms"] is not None and base["median_warm_ms"] is not None and new["median_warm_ms"] <= 1.5 * base["median_warm_ms"]))
    out.append(("G9", bool(rated and rated.get("not_worse"))))
    return out


def human_pack(runs: list, out: Path, seed: int = 11) -> dict:
    """One blinded sheet: for every case, the question each run showed (identical questions collapse into one row). The key (case, engine, model) is in key.json."""
    by_case: dict = {}
    for label, run in runs:
        for r in run.get("rows") or []:
            ctxd = r.get("review_context")
            shown = ((ctxd or {}).get("followup_shown") or "").strip()
            if not ctxd or not shown:
                continue
            by_case.setdefault(r["id"], {"ctx": ctxd, "q": {}})["q"].setdefault(shown, []).append(label)
    items = [(cid, d["ctx"], q, labels) for cid, d in by_case.items() for q, labels in d["q"].items()]
    rng = random.Random(seed)
    rng.shuffle(items)
    ids = rng.sample(range(100, 100 + max(len(items), 1) * 7), len(items))
    out.mkdir(parents=True, exist_ok=True)
    cols = ["item_id", "original_question", "candidate_answer", "earlier_statements_available", "followup_shown", "technically_accurate_1to5", "unsupported_or_wrong_claim_yes_no", "natural_interview_wording_1to5", "relevant_to_the_gap_1to5", "uses_earlier_statement_appropriately_yes_no_na", "comment"]
    key = {}
    with (out / "review_sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for (cid, ctxd, q, labels), n in zip(items, ids):
            earlier = " | ".join(f"turn {e.get('turn')}: {e.get('text') or e.get('quote') or ''}" for e in (ctxd.get("earlier") or [])) if isinstance(ctxd.get("earlier"), list) else str(ctxd.get("earlier") or "")
            w.writerow({"item_id": f"R{n}", "original_question": ctxd.get("original_question"), "candidate_answer": ctxd.get("candidate_answer"), "earlier_statements_available": earlier, "followup_shown": q})
            key[f"R{n}"] = {"case": cid, "produced_by": labels}
    (out / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (out / "README.txt").write_text("Rate each row independently. Do not open key.json until every row is rated. The candidate answers and earlier statements are SYNTHETIC benchmark text. Ratings are yours; no script fills them.\n", encoding="utf-8")
    return {"items": len(items), "dir": out.name, "rated": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="results.json files from stage10_verify_real_stack.py --opportunities")
    ap.add_argument("--baseline", default=None, help="the Stage 10N results.json to gate against (default: the first run whose engine is stage10n)")
    ap.add_argument("--rated", default=None, help="optional JSON {\"not_worse\": true|false, \"n_rated\": N} written by a person after rating the sheet")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out or ROOT / "tmp" / f"stage11_compare_{time.strftime('%Y%m%d_%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    runs, digs = [], []
    for p in a.runs:
        doc = json.loads(Path(p).read_text(encoding="utf-8"))
        for r in doc["results"]:
            if r.get("status") != "ran":
                continue
            r.setdefault("engine", doc.get("engine") or "stage10n")
            d = digest(r, str(p))
            digs.append(d)
            runs.append((f"{d['engine']}|{d['model']}|{d['prompt']}", r))
    rated = json.loads(Path(a.rated).read_text(encoding="utf-8")) if a.rated else None
    L = ["# Stage 11: benchmark runs side by side", "", "Evidence kinds are shown per row. `selftest_fake_server` rows are plumbing checks, never measurements. No model is ranked; the gates only decide whether the objective engine may replace Stage 10N for the same model.", "",
         "| engine | model | prompt | evidence | eligible ok | technical | memory grounded | mem offered | fabricated | strict skip | fallbacks | bad payload rows | warm median ms | p95 ms |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in digs:
        L.append(f"| {d['engine']} | {d['model']} | {d['prompt']} | {d['evidence']} | {d['success']}/{d['eligible']} | {d['technical']} | {d['memory_grounded']} | {d['memory_offered']} | {d['fabricated']} | {d['strict_skip']} | {d['fallbacks']} | {d['inconsistent_payload_rows']} | {d['median_warm_ms']} | {d['p95_warm_ms']} |")
    verdicts = []
    base_candidates = [d for d in digs if d["engine"] == "stage10n" and d["evidence"] == "real_model"]
    if a.baseline:
        bdoc = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
        base_candidates = [digest(r, a.baseline) for r in bdoc["results"] if r.get("status") == "ran"]
    for new in [d for d in digs if d["engine"] == "objective"]:
        base = next((b for b in base_candidates if b["model"] == new["model"]), None)
        if new["evidence"] != "real_model":
            verdicts.append({"run": f"{new['engine']}|{new['model']}", "decision": "NOT EVALUABLE: selftest/fake data is not evidence"}); continue
        if base is None:
            verdicts.append({"run": f"{new['engine']}|{new['model']}", "decision": "NOT EVALUABLE: no real Stage 10N run of the same model to gate against"}); continue
        g = gates(base, new, rated)
        ok = all(v for _, v in g)
        verdicts.append({"run": f"{new['engine']}|{new['model']}", "baseline": f"{base['engine']}|{base['model']}|{base['prompt']}", "gates": {k: ("MET" if v else "NOT MET") for k, v in g},
                         "decision": "objective engine MAY replace stage10n as the default" if ok else "KEEP stage10n as the default (at least one gate not met)"})
    L += ["", "## Pre-registered adoption gates", ""] + [f"- {i}: {t}" for i, t in GATES] + ["", "## Decisions", "", "```json", json.dumps(verdicts, indent=1), "```"]
    pack = human_pack(runs, out / "human_review_pack")
    L += ["", f"Blinded human-review pack: `{pack['dir']}/review_sheet.csv` ({pack['items']} distinct questions, UNRATED). G9 stays NOT MET until a person rates it and supplies --rated.", ""]
    (out / "comparison.md").write_text("\n".join(L), encoding="utf-8")
    (out / "comparison.json").write_text(json.dumps({"digests": digs, "decisions": verdicts, "human_pack": pack}, indent=1), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Stage 11R: the validators before and after the repair, on the same questions (offline, no model).

  .bot\\Scripts\\python.exe scripts\\stage11r_validator_compare.py --out tmp\\stage11r_validator_compare.json

'legacy' = the Stage 11 rules without the 11R additions (a shim switches the new rules off; nothing else differs). 'repaired' = the code as installed. Pools:
  recorded_accepted   questions the real llama3.2:3b wrote that the rules ACCEPTED in the real Windows runs (Stage 10N and Stage 11 objective): who is newly refused, and why, for a person to judge
  recorded_rejected   questions the real model wrote that the rules REFUSED: who is newly accepted (should be only the documented T11 fix)
  pairs               hand-written good/bad pairs (fixture, holdout, holdout2, holdout3): false rejections and false acceptances
  references          unsupported-reference controls: unsupported references that pass (must be 0) and genuine references refused
Author-judged data; replay of recorded text is a diagnostic of code behaviour, never a measurement of a model.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import followup_llm as FL, intel, opportunity_eval as OE, question_pairs_eval as Q  # noqa: E402

EVAL = ROOT / "src" / "demo" / "eval_data"
REPORTS = ROOT / "reports" / "stage11_eval"
NEVER = re.compile(r"(?!x)x")


@contextlib.contextmanager
def stage11s_off():
    """Switch the 11S additions off, leaving the code as Stage 11R installed it: no correctness rules on the written question, the pooled value probe, no rubric-anchored coverage, the old
    presupposition test (blind to a conditional frame), a lead that is copied back into the question rejected instead of dropped, and personal references backed only by the one statement the model
    happened to cite."""
    saved = {}

    def patch(mod, name, val):
        saved[(mod, name)] = getattr(mod, name)
        setattr(mod, name, val)
    patch(intel, "contradictory_premise", lambda *a, **k: None)
    patch(intel, "circular_contrast", lambda *a, **k: False)
    patch(intel, "repeats_answer_phrase", lambda *a, **k: None)
    patch(intel, "duplicated_subject", lambda *a, **k: None)
    patch(intel, "two_questions", lambda *a, **k: False)
    patch(intel, "invented_qualifier", lambda *a, **k: [])
    patch(intel, "value_stated", lambda *a, **k: False)
    patch(intel, "equated_with_explained", lambda *a, **k: None)
    patch(intel, "implies_unclaimed_use", lambda *a, **k: False)
    patch(intel, "asserted_in_work", lambda *a, **k: set())             # 11T: grammatical placement of a technique inside their work
    patch(intel, "names_the_work", lambda *a, **k: False)               # 11T: lead dropped when the question already names the work in their words
    patch(intel, "explained_as_owned", lambda *a, **k: False)           # 11T: an explained concept presented as their own work
    patch(intel, "relates_equated_pair", lambda *a, **k: None)          # 11T: two names the rubric equates, related to each other
    patch(intel, "target_premise", lambda *a, **k: None)
    patch(intel, "_HYPOTHETICAL", NEVER)                      # the 11R presupposition test did not look for a conditional frame
    patch(intel, "LEAD_DROP_INSTEAD_OF_REJECT", False)
    patch(FL, "offered_support", lambda ctx, own_work_only=False: "")
    try:
        yield
    finally:
        for (mod, name), v in saved.items():
            setattr(mod, name, v)


@contextlib.contextmanager
def pre_11r():
    """Switch the 11R additions off too (everything this stage and the last one added)."""
    saved = {}

    def patch(mod, name, val):
        saved[(mod, name)] = getattr(mod, name)
        setattr(mod, name, val)
    old_ids = re.compile(r"\b(?:[ESGKesgk]\d{1,2}|m\d{1,3})\b")

    def old_sanitise(q, ctx):
        labels = {c["id"]: c["label"] for c in ctx.concepts}
        return old_ids.sub(lambda m: labels.get(m.group(0).upper(), m.group(0)) if m.group(0)[0] != "m" else m.group(0), q)
    patch(FL, "unsupported_reference", lambda *a, **k: [])
    patch(FL, "adjacent_repeat", lambda q: None)
    patch(FL, "sanitise_ids", old_sanitise)
    patch(intel, "sidesteps_stated_value", lambda *a, **k: False)
    patch(intel, "premise_restates_answer", lambda *a, **k: False)
    patch(intel, "_LIST_OF_WORDS", NEVER)
    patch(intel, "MAX_WORDS", 10 ** 6)
    patch(intel, "longest_shared_run", lambda *a, **k: 0)
    patch(intel, "_PRESUPPOSES", NEVER)
    patch(intel, "_PAST_ACTION", NEVER)
    try:
        with stage11s_off():
            yield
    finally:
        for (mod, name), v in saved.items():
            setattr(mod, name, v)


@contextlib.contextmanager
def stage11t_off():
    """Switch off only the 11T additions, leaving the unfinished 11S pass: technique placed inside their work by grammar, the lead dropped when the question names the work in their words, an explained
    concept presented as their own work, and 'both A and B' said of one thing."""
    saved = {}

    def patch(mod, name, val):
        saved[(mod, name)] = getattr(mod, name)
        setattr(mod, name, val)
    real_contra = intel.contradictory_premise
    patch(intel, "asserted_in_work", lambda *a, **k: set())
    patch(intel, "names_the_work", lambda *a, **k: False)
    patch(intel, "explained_as_owned", lambda *a, **k: False)
    patch(intel, "relates_equated_pair", lambda *a, **k: None)
    patch(intel, "contradictory_premise", lambda q: (lambda r: None if r and r.endswith(":both") else r)(real_contra(q)))
    try:
        yield
    finally:
        for (mod, name), v in saved.items():
            setattr(mod, name, v)


def _implies_unclaimed_use_11t(question, ctx, m):
    """The 11T rule, verbatim: any word of this turn's question or answer next to 'your' counted as a claim about their work."""
    if not intel._SECOND_PERSON.search(question):
        return False
    stored = FL.content_stems(" ".join([m.get("quote") or "", m.get("text") or "", m.get("subject") or ""]))
    ignore = {FL._stem(w) for w in FL._GENERIC} | {FL._stem(w) for w in intel._ABSTRACT}
    if intel.asserted_in_work(question) - stored - ignore:
        return True
    if intel._HYPOTHETICAL.search(question):
        return False
    technique = (FL.content_stems(ctx.answer) | FL.content_stems(ctx.question)) - stored - ignore
    return bool(FL.content_stems(question) & technique)


@contextlib.contextmanager
def stage11u_off():
    """Switch off only the 11U additions, leaving the code as Stage 11T installed it."""
    saved = {}

    def patch(mod, name, val):
        saved[(mod, name)] = getattr(mod, name)
        setattr(mod, name, val)
    patch(intel, "implies_unclaimed_use", _implies_unclaimed_use_11t)
    patch(intel, "claim_handle", lambda *a, **k: None)                  # no handle-based attribution (and no handle line in the prompt, which the comparison never sends)
    patch(intel, "_QUALIFIER", re.compile(r"\b(lowest|highest|largest|smallest|biggest|greatest|fewest|cheapest|costliest|strongest|weakest|longest|shortest|slowest|fastest)\b", re.I))
    for name in ("asserts_interpretation", "unsupported_target_event", "misattributed_target", "unsupported_effect", "narrows_collection"):
        patch(intel, name, (lambda *a, **k: None) if name != "asserts_interpretation" else (lambda *a, **k: False))
    try:
        yield
    finally:
        for (mod, name), v in saved.items():
            setattr(mod, name, v)


BASELINES = {"stage11r": stage11s_off, "pre11r": pre_11r, "stage11s": stage11t_off, "stage11t": stage11u_off}
legacy = stage11s_off                       # replaced by --baseline in main()


def judge_objective(q, ctx):
    obj = intel.plan_objective(ctx)
    if obj is None:
        return False, ["no_open_concept"]
    v = intel.evaluate_question(q, ctx, obj)
    return v.prop is not None, v.reasons


def recorded(path: Path, engine_label: str):
    doc = json.loads(path.read_text(encoding="utf-8"))
    run = doc["results"][0]
    eng = OE.offline_engine()
    cases = {c["id"]: c for c in OE.load()["cases"]}
    out = []
    for r in run["rows"]:
        if r.get("mode") != "technical":
            continue
        ctx = OE.build_case(eng, copy.deepcopy(cases[r["id"]]))[0]           # 11S: build_case consumes the case dict, so the same case read from a second recorded run must start from a fresh copy
        for d in r.get("debug") or []:
            q = (d.get("question") or "").strip()
            if q:
                out.append({"run": engine_label, "id": r["id"], "attempt": d["attempt"], "q": q, "recorded_reasons": d.get("reasons") or [], "ctx": ctx})
    return out


def _holdout5_ctx(it):
    m = dict(it["memory"], id="m1", text=it["memory"]["quote"], turn=1, confidence="high", reason="shared_words", score=0.5)
    q = m["quote"]
    m["lead"] = ("Earlier you said you " + q[2:].rstrip(".") + ".") if q.startswith("I ") else ("Earlier you said \u201c" + q.rstrip(".") + "\u201d.")
    return FL.Context(role="Engineer", stage="core", question_id="q", question=it["question"], topic=it["topic"], answer=it["answer"], domain="d", reference=it["reference"], memory=[m],
                      concepts=[{"id": i, "label": lab, "tier": "essential", "members": [lab]} for i, lab in it["concepts"]])


def _outcome(q, ctx):
    obj = intel.plan_objective(ctx)
    v = intel.evaluate_question(q, ctx, obj)
    return ("refuse" if v.prop is None else "mem" if v.prop.memory_id else "plain"), v.reasons


def memory_holdout() -> dict:
    """holdout5: memory attribution on cases outside the benchmark. A good question counts as a false rejection when the outcome differs from the one written beforehand (including 'plain' where the
    work was meant to be attributed); a bad one counts as a false acceptance whenever it would be shown."""
    d = json.loads((EVAL / "stage11t_memory_pairs_v1.json").read_text(encoding="utf-8"))
    out = {"n_good": 0, "FR_legacy": 0, "FR_repaired": 0, "n_bad": 0, "FA_legacy": 0, "FA_repaired": 0, "rows": []}
    for it in d["items"]:
        ctx = _holdout5_ctx(it)
        for kind, qs in (("good", it["good"]), ("bad", it["bad"])):
            for g in qs:
                with legacy():
                    lo, _ = _outcome(g["q"], ctx)
                no, why = _outcome(g["q"], ctx)
                want = g.get("expect", "refuse")
                out["n_" + kind] += 1
                key = "FR" if kind == "good" else "FA"
                out[key + "_legacy"] += lo != want
                out[key + "_repaired"] += no != want
                out["rows"].append({"id": it["id"], "kind": kind, "q": g["q"], "expected": want, "legacy": lo, "repaired": no, "reasons": why, "known_gap": bool(g.get("known_gap"))})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--baseline", choices=sorted(BASELINES), default="stage11r", help="what 'legacy' means: the code as Stage 11R installed it (default), before Stage 11R, or the unfinished 11S pass (this repair switched off)")
    a = ap.parse_args()
    global legacy
    legacy = BASELINES[a.baseline]
    FL.set_vocabulary_source(lambda: [])
    res = {"evidence": "offline replay and author-judged sets; no model was called", "baseline": a.baseline, "repaired": "the code as installed"}
    try:
        pool = []
        for f, lab in (("stage10n_real_llama3.2_3b_20261021_205846.json", "stage10n"), ("stage11_objective_real_llama3.2_3b_20261021_221628.json", "objective_11.obj1"),
                       ("stage11r_objective_real_llama3.2_3b_20261022_162322.json", "objective_11.obj2"),
                       ("stage11_objective_real_llama3.2_3b_20261022_194032.json", "objective_11.obj4")):
            if (REPORTS / f).exists():
                pool += recorded(REPORTS / f, lab)
        acc_rows, rej_rows = [], []
        for it in pool:
            with legacy():
                old_ok, old_why = judge_objective(it["q"], it["ctx"])
            new_ok, new_why = judge_objective(it["q"], it["ctx"])
            was_accepted = not it["recorded_reasons"]
            row = {"run": it["run"], "id": it["id"], "attempt": it["attempt"], "question": it["q"], "legacy_accepts": old_ok, "repaired_accepts": new_ok, "repaired_reasons": new_why}
            (acc_rows if was_accepted else rej_rows).append(row)
        res["recorded_accepted"] = {"n": len(acc_rows), "legacy_accepts": sum(r["legacy_accepts"] for r in acc_rows), "repaired_accepts": sum(r["repaired_accepts"] for r in acc_rows),
                                    "newly_refused": [r for r in acc_rows if r["legacy_accepts"] and not r["repaired_accepts"]]}
        res["recorded_rejected"] = {"n": len(rej_rows), "legacy_accepts": sum(r["legacy_accepts"] for r in rej_rows), "repaired_accepts": sum(r["repaired_accepts"] for r in rej_rows),
                                    "newly_accepted": [r for r in rej_rows if not r["legacy_accepts"] and r["repaired_accepts"]]}
        eng = OE.offline_engine()
        cases = {c["id"]: c for c in OE.load()["cases"]}
        sets = {}
        for path in (EVAL / "stage10n_question_pairs_v1.json", EVAL / "stage11r_question_pairs_v1.json", EVAL / "stage11s_correctness_pairs_v1.json"):
            for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
                # holdout4 carries whole cases of its own (full concept records and a reference); the older sets are read by the shared helper
                ctx = (FL.Context(role="Software Engineer", stage="core", question_id=it["id"], question=it["question"], topic=it["topic"], answer=it["answer"], concepts=it["concepts"], reference=it["reference"])
                       if it["src"] == "holdout4" else Q._context(it, eng, cases))
                for kind, qs in (("good", [g for g in it["good"]]), ("bad", [b["q"] for b in it["bad"]])):
                    for q in qs:
                        with legacy():
                            lo, _ = judge_objective(q, ctx)
                        no, why = judge_objective(q, ctx)
                        s = sets.setdefault(it["src"], {"n_good": 0, "FR_legacy": 0, "FR_repaired": 0, "n_bad": 0, "FA_legacy": 0, "FA_repaired": 0, "false_acceptances_repaired": [], "false_rejections_repaired": []})
                        if kind == "good":
                            s["n_good"] += 1
                            s["FR_legacy"] += not lo
                            s["FR_repaired"] += not no
                            if not no:
                                s["false_rejections_repaired"].append({"id": it["id"], "q": q, "reasons": why})
                        else:
                            s["n_bad"] += 1
                            s["FA_legacy"] += lo
                            s["FA_repaired"] += no
                            if no:
                                s["false_acceptances_repaired"].append({"id": it["id"], "q": q})
        res["pairs"] = sets
        res["memory_holdout"] = memory_holdout()
        ref = json.loads((EVAL / "stage11r_reference_pairs_v1.json").read_text(encoding="utf-8"))
        base = ref["base"]
        ctx = FL.Context(role="Data Scientist", stage="core", question_id="q", question=base["question"], topic=base["topic"], answer=base["answer"], concepts=[{"id": "E1", "label": "evaluation without labels", "tier": "essential", "members": []}], reference="")
        bad_pass, good_refused, n_bad, n_good = [], [], 0, 0
        for c in ref["cases"]:
            found = FL.unsupported_reference(c["q"], ctx, base["memory"] if c.get("memory") else "")
            if c["supported"]:
                n_good += 1
                if found:
                    good_refused.append({"q": c["q"], "found": found})
            else:
                n_bad += 1
                if not found:
                    bad_pass.append({"q": c["q"], "kind": c["kind"]})
        res["references"] = {"unsupported_controls": n_bad, "unsupported_that_pass_repaired": bad_pass, "unsupported_that_pass_legacy": n_bad, "genuine_controls": n_good, "genuine_refused_repaired": good_refused,
                             "note": "the legacy checker had no reference detector beyond 'earlier ...' cues, so 0 of the unsupported controls were refused by the reference rule"}
    finally:
        FL.set_vocabulary_source(None)
    print(json.dumps({k: (v if k != "pairs" else {s: {kk: vv for kk, vv in d.items() if not kk.startswith("false_")} for s, d in v.items()}) for k, v in res.items()}, indent=1)[:6000])
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

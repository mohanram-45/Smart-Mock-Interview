"""Stage 3C-1 Phase 5: controlled BEHAVIOURAL comparison, legacy evaluator vs modular pipeline, on the 8 scope-eligible benchmark questions.

Everything here is MOCK: scripted providers/verifiers inject controlled faults (fabricated evidence, garbage output, contradictions, ...)
and we observe how each architecture reacts. There is NO real model, and the benchmark's AI-authored score expectations are never read.
Nothing here measures grading accuracy and must not be quoted as such.

  python scripts/stage3c1_compare.py [--out results/stage3c1_comparison.json]
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.evaluator import AnswerEvaluator                                  # noqa: E402
from src.evaluation.grounding import reference_from_record                            # noqa: E402
from src.evaluation.errors import ProviderError                               # noqa: E402
from src.evaluation.providers.mock import MockProvider                                # noqa: E402
from src.evaluation.schema import EvaluationRequest                                   # noqa: E402
from src.evaluation.modular import ModularEvaluator, ReferenceMaterial, ScopeStore    # noqa: E402
from src.evaluation.modular.verification import RawVerdict, RawVerification, ConceptVerifier, VerifierProviderError  # noqa: E402
from src.retrieval.corpus import load_corpus                                          # noqa: E402

SCENARIOS = ["valid_evidence", "fabricated_evidence", "provider_garbage", "provider_error", "nothing_stated", "contradictory", "all_unsure"]


class Behave(ConceptVerifier):
    is_mock = True
    name = "scenario-mock"

    def __init__(self, scenario): self.s = scenario

    def verify(self, request):
        if self.s == "provider_error":
            raise VerifierProviderError("scripted outage", retryable=False)
        out = []
        for rid, member in request.expected_keys():
            if self.s == "valid_evidence":
                out.append(RawVerdict(rid, member, "states_correctly", ("c1",)))
            elif self.s == "fabricated_evidence":
                out.append(RawVerdict(rid, member, "states_correctly", ("c99",)))
            elif self.s == "nothing_stated":
                out.append(RawVerdict(rid, member, "not_stated", ()))
            elif self.s == "contradictory":
                out.append(RawVerdict(rid, member, "states_correctly", ("c1",)))
                out.append(RawVerdict(rid, member, "states_incorrectly", ("c1",), "wrong", "x", "major"))
            else:
                out.append(RawVerdict(rid, member, "unverified", ()))
        return RawVerification(tuple(out), "on_topic", None if self.s == "all_unsure" else ("c1",), ())


def legacy_script(scenario, rec, answer):
    first = answer.split(".")[0].strip() or answer[:40]
    lv = {"rubric": None}
    def j(levels, **kw):
        d = {"gradable": True, "not_gradable_reason": "", "rubric": {k: {"level": l, "justification": "x"} for k, l in zip(("correctness", "completeness", "relevance", "reasoning"), levels)},
             "score_rationale": "scripted", "correct_concepts": [], "missing_concepts": [], "factual_errors": [], "strengths": [], "improvement_suggestions": [],
             "improved_example_answer": "", "follow_up_question": "", "supporting_evidence": [], "confidence": "high", "verification_limitations": []}
        d.update(kw); return d
    kc = list(rec.get("key_concepts") or [])[:3]
    if scenario == "valid_evidence":
        return j((4, 4, 4, 4), correct_concepts=[{"concept": c, "candidate_quote": first} for c in kc])
    if scenario == "fabricated_evidence":
        return j((4, 4, 4, 4), correct_concepts=[{"concept": c, "candidate_quote": "words the candidate never wrote"} for c in kc])
    if scenario == "provider_garbage":
        return "not json at all {"
    if scenario == "provider_error":
        return ProviderError("scripted outage")
    if scenario == "nothing_stated":
        return j((0, 0, 4, 0), missing_concepts=kc)
    if scenario == "contradictory":
        return j((2, 2, 4, 2), correct_concepts=[{"concept": c, "candidate_quote": first} for c in kc], factual_errors=[{"claim_quote": first, "explanation": "wrong", "correction": "x", "severity": "major"}])
    return j((4, 4, 4, 4))     # all_unsure: model grades without citing any concept evidence


def run_legacy(rec, scenario, answer):
    script = legacy_script(scenario, rec, answer)
    ev = AnswerEvaluator(MockProvider([script]), sleep=lambda s: None, nonce_factory=lambda: "n0")
    req = EvaluationRequest(question_id=rec["question_id"], question=rec["question"], domain=rec["domain"], topic=rec["topic"], difficulty=rec["difficulty"],
                            candidate_answer=answer, reference=reference_from_record(rec), support=[])
    r = ev.evaluate(req)
    credited = {c.concept for c in r.correct_concepts}
    blamed_claims = {e.claim_quote for e in r.factual_errors}
    credited_quotes = {c.candidate_quote for c in r.correct_concepts}
    return {"status": r.evaluation_status.value, "score": r.provisional_score, "adjustments": len(r.score_adjustments),
            "same_text_credited_and_blamed": bool(blamed_claims & credited_quotes),
            "accepted_unverifiable_credit": any(c.candidate_quote and c.candidate_quote not in answer for c in r.correct_concepts),
            "dimension_justifications_are_model_text": True}


def _stable(r):
    d = r.to_dict(); d["provenance"] = {k: v for k, v in d["provenance"].items() if k != "verifier_ms"}   # wall-clock timing is the only non-deterministic field
    return d


def run_modular(store, rec, scenario, answer):
    v = Behave(scenario)
    if scenario == "provider_garbage":
        class G(Behave):
            def verify(self, request):
                from src.evaluation.modular.verification import VerifierInvalidResponse
                raise VerifierInvalidResponse("not json")
        v = G(scenario)
    ev = ModularEvaluator(store, v)
    r = ev.evaluate(rec["question_id"], rec["question"], answer, ReferenceMaterial.from_corpus_record(rec))
    r2 = ev.evaluate(rec["question_id"], rec["question"], answer, ReferenceMaterial.from_corpus_record(rec))
    both = {(x.requirement_id, x.member) for x in r.verdicts if x.state.value == "states_correctly"} & {(x.requirement_id, x.member) for x in r.verdicts if x.state.value == "states_incorrectly"}
    return {"status": r.status.value, "score": r.score, "adjustments": len(r.adjustments), "same_text_credited_and_blamed": bool(both),
            "accepted_unverifiable_credit": any(x.state.value == "states_correctly" and any(e.claim_id not in {c["id"] for c in r.claims} for e in x.evidence) for x in r.verdicts),
            "deterministic_repeat": _stable(r) == _stable(r2),
            "every_dimension_has_derivation": all(d.derivation for d in r.dimensions) if r.dimensions else None,
            "confidence": r.confidence}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "results" / "stage3c1_comparison.json")); a = ap.parse_args()
    store = ScopeStore.load()
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    qs = {q["question_id"]: q for q in map(json.loads, (ROOT / "data/evaluation/bench_v2/questions.jsonl").read_text(encoding="utf-8").splitlines())}
    answers = [x for x in map(json.loads, (ROOT / "data/evaluation/bench_v2/answers.jsonl").read_text(encoding="utf-8").splitlines())]   # TEXT ONLY; labels never opened
    elig = set(store.eligible_ids())
    cases = [(x["question_id"], x["answer_text"]) for x in answers if x["question_id"] in elig and x["question_id"] in qs]
    table = {}
    for sc in SCENARIOS:
        L, M = [], []
        for qid, ans in cases:
            L.append(run_legacy(recs[qid], sc, ans)); M.append(run_modular(store, recs[qid], sc, ans))
        def agg(rows, key=None):
            n = len(rows)
            return {"n": n, "numeric_score_issued": sum(1 for r in rows if r["score"] is not None), "score_lt_50": sum(1 for r in rows if r["score"] is not None and r["score"] < 50),
                    "statuses": {s: sum(1 for r in rows if r["status"] == s) for s in sorted({r["status"] for r in rows})},
                    "credited_and_blamed_same_text": sum(r["same_text_credited_and_blamed"] for r in rows), "unverifiable_credit_accepted": sum(r["accepted_unverifiable_credit"] for r in rows)}
        table[sc] = {"legacy": agg(L), "modular": agg(M), "modular_deterministic_repeat": all(r["deterministic_repeat"] for r in M),
                     "modular_dimension_derivations_recorded": all(r["every_dimension_has_derivation"] in (True, None) for r in M)}
    out = {"disclaimer": "MOCK-ONLY behavioural comparison under injected faults. No real model, no accuracy, no use of AI-authored score expectations.",
           "eligible_questions_used": sorted({q for q, _ in cases}), "answers_used": len(cases), "scenarios": table}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    for sc, t in table.items():
        print(f"{sc:20s} legacy scores={t['legacy']['numeric_score_issued']:2d} (<50: {t['legacy']['score_lt_50']:2d}) {t['legacy']['statuses']} | modular scores={t['modular']['numeric_score_issued']:2d} {t['modular']['statuses']}")


if __name__ == "__main__":
    main()

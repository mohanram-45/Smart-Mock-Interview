"""Stage 12: before/after evaluation of technical-answer assessment on representative answers. Bounded: 10 answers, one evaluator run each.

  Windows, real model (needs Ollama with qwen2.5:7b; about 1-3 minutes per answer):
    set SMART_DEMO_LIVE_MODULAR=1
    .bot\\Scripts\\python.exe scripts\\stage12_assess_answers.py --live --out tmp\\stage12_live

  Anywhere, no model (pipeline check only):
    python scripts/stage12_assess_answers.py --scripted --out tmp/stage12_scripted

BEFORE = what /demo showed until Stage 12: the Sentence-BERT similarity as a percentage plus the comment chosen from its band. Taken from the recorded 22 Oct interview
where the answer is real; otherwise computed with the real scorer when it is installed (Windows), else "not computed".
AFTER  = the Stage 12 assessment (src/demo/assessment.py) built from the concept evaluator and the contradiction pass.

Evidence kinds are never mixed: --live rows are a REAL local-model run; --scripted rows use ScriptedVerifier answers written by the author of this stage (a stand-in that only
proves the code path, NOT model quality). `expected` is the author's own judgement, not a human-rated label set.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import assessment as A, experimental as X, opportunity_eval as OE  # noqa: E402

REAL = "real answer from the 22 Oct 2026 interview (results/demo_sessions)"
CASES = [
    {"id": "autoencoder_misconception", "qid": "smi-0054", "kind": "factual error (real)", "source": REAL, "expected": "partially_correct",
     "answer": "An autoencoder is a neural network that compresses data and then reconstructs it. It always needs labelled training data to learn the correct output.",
     "before": {"similarity_pct": 90.68, "comment": "Excellent work — this answer is clear, accurate, and complete."},
     "script": {"autoencoder": ("states_correctly", "text:compresses"), "artificial neural network": ("states_correctly", "text:neural network"), "representation learning": ("not_stated", [])},
     "contradictions": {"contradictions": [{"claim_id": "c2", "reference_quote": "It can learn representation for a set of data without any supervision", "why": "Autoencoders learn from the input itself; they need no labels."}]}},
    {"id": "autoencoder_paraphrase", "qid": "smi-0054", "kind": "correct paraphrase", "source": "written for Stage 12", "expected": "correct",
     "answer": "It is a network trained to reproduce its own input through a narrow bottleneck layer. Because the target is the input itself it needs no labels, and the bottleneck forces it to learn a compact code of the data.",
     "script": {"autoencoder": ("states_correctly", "text:reproduce its own input"), "artificial neural network": ("states_correctly", "text:network trained"), "representation learning": ("states_correctly", "text:compact code")},
     "contradictions": {"contradictions": []}},
    {"id": "unsupervised_short", "qid": "smi-0153", "kind": "partial (real)", "source": REAL, "expected": "partially_correct",
     "answer": "Unsupervised learning is a type of machine learning where the model finds patterns and structures in data without labelled outputs.",
     "before": {"similarity_pct": 65.73, "comment": "You're showing good understanding of the topic here."},
     "script": {"unlabelled data": ("states_correctly", "text:without labelled"), "clustering": ("not_stated", []), "dimensionality reduction": ("not_stated", []), "anomaly detection": ("not_stated", [])},
     "contradictions": {"contradictions": []}},
    {"id": "unsupervised_complete", "qid": "smi-0153", "kind": "correct, own words", "source": "written for Stage 12", "expected": "correct",
     "answer": "It works on data that has no target labels and looks for structure in it: for example grouping customers with k-means clustering or compressing features with PCA. Because there is no ground truth you judge it with internal measures such as the silhouette score.",
     "script": {"unlabelled data": ("states_correctly", "text:no target labels"), "clustering": ("states_correctly", "text:k-means"), "dimensionality reduction": ("states_correctly", "text:PCA"),
                "evaluation without labels": ("states_correctly", "text:silhouette")},
     "contradictions": {"contradictions": []}},
    {"id": "fourier_no_attempt", "qid": "smi-0199", "kind": "no attempt (real)", "source": REAL, "expected": "incorrect",
     "answer": "I'm not sure about this concept. Could we move on to the next question?",
     "before": {"similarity_pct": 0.0, "comment": "There's a gap in understanding here — take some time to review this."}, "script": {}, "contradictions": {"contradictions": []}},
    {"id": "hypothesis_real", "qid": "smi-0170", "kind": "correct, brief (real)", "source": REAL, "expected": "correct",
     "answer": "Hypothesis testing is a statistical method used to test a claim about a population using sample data. We start with a null hypothesis and an alternative hypothesis, then use the data to decide whether there is enough evidence against the null hypothesis.",
     "before": {"similarity_pct": 72.34, "comment": "That's a clear, well-formed response."},
     "script": {"hypothesis testing": ("states_correctly", "text:statistical method"), "null hypothesis": ("states_correctly", "text:null hypothesis and"), "alternative hypothesis": ("states_correctly", "text:alternative hypothesis")},
     "contradictions": {"contradictions": []}},
    {"id": "hypothesis_false", "qid": "smi-0170", "kind": "factual error, reference vocabulary", "source": "written for Stage 12", "expected": "incorrect",
     "answer": "Hypothesis testing uses sample data to prove whether the null hypothesis is true. If the p-value is above the significance level, the null hypothesis is proven true and the alternative hypothesis is false.",
     "script": {"hypothesis testing": ("states_correctly", "text:uses sample data"), "null hypothesis": ("states_incorrectly", "text:proven true", "H0 is never proven by a p-value above alpha; the evidence is only insufficient.", "which is not proof that H0 is true", "major"),
                "alternative hypothesis": ("states_incorrectly", "text:alternative hypothesis is false", "A failure to reject H0 is not a refutation of H1.", "otherwise fail to reject H0", "major")},
     "contradictions": {"contradictions": [{"claim_id": "c1", "reference_quote": "which is not proof that H0 is true", "why": "A test can fail to reject H0; it never proves H0 true."}]}},
    {"id": "unrelated", "qid": "smi-0153", "kind": "unrelated", "source": "written for Stage 12", "expected": "incorrect",
     "answer": "I usually cook pasta on Sundays and I enjoy hiking with my friends in the mountains.", "script": {}, "on_topic": "off_topic", "contradictions": {"contradictions": []}},
    {"id": "empty", "qid": "smi-0153", "kind": "empty", "source": "written for Stage 12", "expected": "incorrect", "answer": "", "script": {}, "contradictions": {"contradictions": []}},
    {"id": "mocking_real", "qid": "smi-0463", "kind": "right idea, no pytest mechanism named (real)", "source": REAL, "expected": "partially_correct",
     "answer": "Mocking is used to replace real dependencies with fake objects during unit testing. For example, we can mock an external API call so the test doesn't depend on the actual service.",
     "before": {"similarity_pct": 49.74, "comment": "There's a solid foundation in this answer."},
     "script": {"unittest.mock.patch": ("not_stated", []), "monkeypatch fixture": ("not_stated", []), "test isolation": ("states_correctly", "text:doesn't depend")},
     "contradictions": {"contradictions": []}},
]


# A small INDEPENDENT set (Stage 12 live correction): answers written after the three failures were analysed, other wording, never used to tune a rule. They are LIVE-ONLY:
# a scripted stand-in would only echo what its author wrote. `expected` is again the author's judgement, not a human-rated label.
INDEPENDENT = [
    {"id": "ind_ae_paraphrase", "qid": "smi-0054", "kind": "independent: correct paraphrase", "source": "written for the Stage 12 correction", "expected": "correct",
     "answer": "A neural net that learns to rebuild its own inputs. An encoder squeezes each input into a small latent vector and a decoder reconstructs it, so no labelled data is needed."},
    {"id": "ind_ae_wrong", "qid": "smi-0054", "kind": "independent: wrong answer", "source": "written for the Stage 12 correction", "expected": "incorrect",
     "answer": "An autoencoder is a supervised classifier that predicts class labels for images using labelled examples."},
    {"id": "ind_unsup_correct", "qid": "smi-0153", "kind": "independent: correct, own words", "source": "written for the Stage 12 correction", "expected": "correct",
     "answer": "Learning from data that has no labels, for instance grouping customers with k-means or reducing dimensions with PCA. With no ground truth you judge it with internal measures such as the silhouette score."},
    {"id": "ind_unsup_wrong", "qid": "smi-0153", "kind": "independent: wrong answer", "source": "written for the Stage 12 correction", "expected": "incorrect",
     "answer": "Unsupervised learning trains on labelled examples so the model can predict a label for new inputs, for instance spam detection."},
    {"id": "ind_hyp_paraphrase", "qid": "smi-0170", "kind": "independent: correct paraphrase", "source": "written for the Stage 12 correction", "expected": "correct",
     "answer": "You assume a default claim, the null, and check whether the sample gives enough evidence to reject it. If the p-value is below the significance level alpha you reject H0, otherwise you only fail to reject it."},
    {"id": "ind_hyp_partial", "qid": "smi-0170", "kind": "independent: one wrong rule", "source": "written for the Stage 12 correction", "expected": "partially_correct",
     "answer": "Hypothesis testing uses sample data to decide about a claim. You state a null and an alternative hypothesis, then you reject the null if the p-value is larger than alpha."},
]
for _c in INDEPENDENT:
    _c.update(script={}, contradictions={"contradictions": []}, live_only=True)
CASES += INDEPENDENT


class _Scripted:
    """A contradiction 'provider' that returns the reply written in the case. Stand-in only."""
    model, is_mock, paid, response_schema = "scripted", True, False, None

    def __init__(self, reply):
        self.reply = reply

    def generate(self, system, user):
        from src.evaluation.providers.base import ProviderResponse
        from src.evaluation.modular import contradictions as CX
        if system == CX.CONFIRM_SYSTEM:                                       # the second-opinion call: a stand-in that confirms whatever the case script proposed
            return ProviderResponse(json.dumps({"verdict": "contradicts"}), self.model, 1.0, {})
        return ProviderResponse(json.dumps(self.reply), self.model, 1.0, {})


def _before(case, rec):
    if case.get("before"):
        return {**case["before"], "source": "recorded (22 Oct interview)"}
    try:
        from src.demo.engine import _legacy_feedback, _legacy_scorer
        sc = _legacy_scorer("bert", [rec["canonical_answer"]])
        pct = round(float(sc.score(rec["canonical_answer"], case["answer"])) * 100, 2) if case["answer"].strip() else 0.0
        return {"similarity_pct": pct, "comment": _legacy_feedback(pct, rec["question"], case["answer"], "bert"), "source": "computed now (Sentence-BERT)"}
    except Exception as e:
        return {"similarity_pct": None, "comment": None, "source": f"not computed ({type(e).__name__}: Sentence-BERT not available here)"}


def run(live: bool, only=None) -> dict:
    eng = OE.offline_engine()
    rows = []
    for case in CASES:
        if only and case["id"] not in only:
            continue
        if case.get("live_only") and not live:
            continue
        rec = eng.record(case["qid"])
        before = _before(case, rec)
        sim = {"status": "scored", "score": before["similarity_pct"]} if before.get("similarity_pct") is not None else {"status": "unavailable"}
        t0 = time.perf_counter()
        terms = {"found": [], "missing": [c for c in (rec.get("key_concepts") or [])]}
        if A.no_attempt(case["answer"], None):
            view, mode = None, ("live" if live else "mock")
        elif live:
            view, mode = X.evaluate("live", rec, case["answer"]), "live"
        else:
            from src.evaluation.modular.mock_verifiers import ScriptedVerifier, scripted
            ver = ScriptedVerifier(scripted(case["script"], default="not_stated", on_topic=case.get("on_topic", "on_topic")))
            view, mode = X.evaluate("mock", rec, case["answer"], verifier=ver, contradiction_provider=_Scripted(case["contradictions"])), "scripted"
            if view.get("source"):
                view["source"]["tags"] = [t for t in view["source"].get("tags", []) if t != "MOCK VERIFIER"]   # scripted verdicts are judged like a model's, and labelled 'scripted' below
        ms = round((time.perf_counter() - t0) * 1000, 1)
        a = {"answer": case["answer"], "skipped": False, "legacy": sim, "terms": terms,
             "modular": {"mode": "live" if mode in ("live", "scripted") else mode, "status": "done", "view": view}}
        r = A.assess(a, {"stage": "core", "question": rec["question"]})
        rows.append({"id": case["id"], "question": rec["question"], "kind": case["kind"], "source": case["source"], "expected_by_author": case["expected"],
                     "before": before, "after": {k: r[k] for k in ("verdict", "label", "reason", "basis", "correct_concepts", "missing_concepts", "misconceptions", "unverified_concepts",
                                                                     "feedback", "contradiction_check")},
                     "similarity_shown_now": r["similarity"]["display"], "match_expected": r["verdict"] == case["expected"], "outcome": ("match" if r["verdict"] == case["expected"] else "uncertain" if r["verdict"] == "uncertain" else "mismatch"), "latency_ms": ms,
                     "evaluator_status": (view or {}).get("status"), "evidence": "real_local_model" if live else "scripted_stand_in"})
    return {"evidence": "REAL local-model run (qwen2.5:7b via Ollama)" if live else "SCRIPTED stand-in: proves the code path only, says nothing about model quality",
            "expected_labels": "author judgement, not human-rated", "n": len(rows), "matches": sum(r["match_expected"] for r in rows),
            "uncertain": sum(r["outcome"] == "uncertain" for r in rows), "mismatches": sum(r["outcome"] == "mismatch" for r in rows), "rows": rows}


def markdown(res: dict) -> str:
    out = [f"# Stage 12 answer assessment: {res['evidence']}", "", f"Expected verdicts are the author's judgement ({res['expected_labels']}). Exact matches: {res['matches']}/{res['n']}; honest 'Uncertain' (NOT a match): {res['uncertain']}; wrong verdicts: {res['mismatches']}.", "",
           "| case | kind | BEFORE (similarity % + band comment) | AFTER verdict | misconceptions found | missing | expected |", "|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        b = r["before"]
        before = f"{b['similarity_pct']:.1f}% — “{b['comment']}”" if b.get("similarity_pct") is not None else b["source"]
        mis = "; ".join(f"“{m['claim']}”" for m in r["after"]["misconceptions"]) or "—"
        out.append(f"| {r['id']} | {r['kind']} | {before} | **{r['after']['label']}** ({r['after']['reason']}); similarity now shown as {r['similarity_shown_now']} | {mis} | "
                   f"{'; '.join(r['after']['missing_concepts']) or '—'} | {r['expected_by_author']}{' ✓' if r['match_expected'] else (' (uncertain)' if r['outcome'] == 'uncertain' else ' ✗')} |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--live", action="store_true")
    g.add_argument("--scripted", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cases", nargs="*")
    a = ap.parse_args()
    if a.live and not X.live_enabled():
        print("set SMART_DEMO_LIVE_MODULAR=1 and start Ollama (qwen2.5:7b) first")
        return 2
    res = run(a.live, a.cases)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "summary.md").write_text(markdown(res), encoding="utf-8")
    print(markdown(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

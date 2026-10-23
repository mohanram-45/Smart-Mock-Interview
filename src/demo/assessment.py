"""Stage 12: the technical CORRECTNESS assessment of one answer, kept strictly apart from semantic similarity.

    verdict  correct | partially_correct | incorrect | uncertain | unavailable | pending | not_applicable

Where the verdict comes from (and where it never comes from):
  * the experimental concept evaluator's requirement outcomes (src/evaluation/modular, run by the local model) and its verified factual errors;
  * the Stage 12 contradiction pass (src/evaluation/modular/contradictions.py), which catches false statements that are not themselves a curated requirement;
  * one deterministic rule: an answer with no attempt at the question ("I'm not sure, can we move on?", an empty answer) is incorrect.
  * NEVER the Sentence-BERT similarity. Similarity is reported next to the verdict as a 0-1 resemblance value with its own caveat: a correct paraphrase can resemble the
    reference little, and a false answer that reuses the reference's words can resemble it a lot (the 22 Oct interview: "an autoencoder ... always needs labelled training
    data" had similarity 0.91).

Honesty rules, in order of precedence:
  * no evaluator result (off, failed, timed out, interrupted)        -> unavailable, nothing is invented;
  * evaluator ran but the evidence is incomplete or suspect           -> uncertain, with what WAS found listed;
  * "correct" needs every essential requirement demonstrated AND a contradiction pass that actually ran and found nothing;
  * a verified misconception caps the verdict at partially_correct (incorrect if nothing essential was demonstrated, or if the wrong statements outnumber the right ideas);
  * Stage 12 live correction (22 Oct 2026): (a) a requirement that only restates the question's own subject ("What is an autoencoder?" -> "autoencoder") cannot block a
    verdict when the answer is worded differently; it still counts when satisfied. (b) A group credit ("any of clustering / dimensionality reduction / ...") stands only if a
    credited member is actually named in the answer; otherwise it is undetermined, never satisfied. Abstract single concepts are left to the model: a paraphrase must not lose
    credit for different wording;
  * the mock verifier is a word-overlap test double: its results are labelled as such and can never produce "correct".
Pure function, no model call, no I/O: it is computed from what the session already stores, so older sessions get it too.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from . import interview as I

SCHEMA = "smi.assessment/1"
VERDICTS = ("correct", "partially_correct", "incorrect", "uncertain", "unavailable", "pending", "not_applicable")
LABELS = {"correct": "Correct", "partially_correct": "Partially correct", "incorrect": "Incorrect", "uncertain": "Uncertain", "unavailable": "Not assessed",
          "pending": "Checking…", "not_applicable": "Not assessed"}
SIMILARITY_MEANING = ("Resemblance to one reference answer (0 = unrelated, 1 = near-identical wording and meaning). It is not a grade and not a percentage correct: "
                      "a correct answer in other words can score low, and a wrong answer that reuses the reference's words can score high.")
NO_ATTEMPT_MAX_WORDS = 25
_UNSURE = re.compile(r"\b(?:i\s*(?:'m|am)\s+not\s+sure|i\s+(?:do\s+not|don'?t)\s+know|no\s+idea|not\s+familiar|can\s+we\s+move\s+on|could\s+we\s+move\s+on|move\s+on\s+to\s+the\s+next|skip\s+this|pass)\b", re.I)
_FILLER = frozenset("""i im i'm am not sure about this that the a an concept question topic it could can we move on to next please sorry dont don't do know no idea really
familiar with have never heard of skip pass rest is are so yet one""".split())


def similarity_view(legacy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The stored similarity (0-100 in the session for backwards compatibility) as a 0-1 value. Never a percentage, never a verdict."""
    leg = legacy or {}
    if leg.get("status") == "scored" and isinstance(leg.get("score"), (int, float)):
        v = max(0.0, min(1.0, float(leg["score"]) / 100.0))
        return {"available": True, "value": round(v, 2), "display": f"{v:.2f}", "meaning": SIMILARITY_MEANING, "used_for_verdict": False}
    return {"available": False, "value": None, "display": "—", "meaning": SIMILARITY_MEANING, "used_for_verdict": False}


def no_attempt(answer: str, terms: Optional[Dict[str, Any]] = None) -> bool:
    """Empty, or a short 'I don't know / can we move on' reply that carries no technical content of its own (no curated key term, nothing but filler words)."""
    text = (answer or "").strip()
    if not text:
        return True
    if I.word_count(text) > NO_ATTEMPT_MAX_WORDS or not _UNSURE.search(text):
        return False
    if (terms or {}).get("found"):
        return False
    content = [w for w in re.findall(r"[a-z][a-z'\-]+", text.lower()) if w not in _FILLER and len(w) > 2]
    return len(content) <= 1


_W = re.compile(r"[a-z0-9]+")
_STOPW = frozenset("a an the and or but of to in on at for with by from as is are was were be it its this that these those there their can could would should may might will do does did not no "
                   "into about between through what how why where which who when if also only just very more most each any all some other another same one two".split())


def _stems(text: str) -> set:
    """Content-word stems (first six letters) of a text. Local on purpose: the default /demo path must not import the optional evaluator package."""
    return {w[:6] for w in _W.findall((text or "").lower()) if len(w) > 2 and w not in _STOPW}


def _grounded(member: str, answer: str) -> bool:
    ms = _stems(member)
    if not ms:
        return False
    have = _stems(answer)
    need = len(ms) if len(ms) < 3 else -(-4 * len(ms) // 5)
    return len(ms & have) >= need


def _adjust_outcomes(outcomes: List[Dict[str, Any]], question: str, answer: str) -> List[Dict[str, Any]]:
    """Two evidence rules applied to the evaluator's outcomes (see the module docstring). Returns copies; nothing stored is modified."""
    qs, out = _stems(question), []
    for o in outcomes:
        o = dict(o)
        det = o.get("detail") or {}
        if o.get("kind") == "group" and o.get("status") == "satisfied" and "correct_members" in det:
            if not any(_grounded(m, answer) for m in det.get("correct_members") or []):
                o["status"], o["downgrade"] = "undetermined", "group_member_not_named_in_answer"
        if o.get("tier") == "essential" and o.get("kind") != "group" and o.get("status") != "satisfied":
            ls = _stems(o.get("label") or "")
            if ls and ls <= qs:
                o["topic_only"] = True
        out.append(o)
    return out


def _base(verdict: str, reason: str, basis: str, similarity: Dict[str, Any], **extra) -> Dict[str, Any]:
    out = {"schema": SCHEMA, "verdict": verdict, "label": LABELS[verdict], "reason": reason, "basis": basis, "correct_concepts": [], "missing_concepts": [],
           "optional_missing": [], "unverified_concepts": [], "misconceptions": [], "feedback": [], "similarity": similarity, "human_validated": False,
           "contradiction_check": None}
    out.update(extra)
    return out


def _contradiction_misconceptions(view: Dict[str, Any]) -> tuple:
    cx = view.get("contradictions") or {}
    items = [{"claim": i.get("claim"), "why": i.get("why"), "reference_says": i.get("reference_quote"), "concept": None, "source": "contradiction_check"}
             for i in (cx.get("items") or [])]
    return items, cx.get("status") or "not_checked"


def assess(a: Optional[Dict[str, Any]], q: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The assessment of one stored answer `a` (an entry of session['answers']) to question `q`. Never raises."""
    try:
        return _assess(a, q)
    except Exception as e:                                                    # presentation must survive any malformed stored data
        return _base("unavailable", f"assessment_error:{type(e).__name__}", "none", similarity_view((a or {}).get("legacy")))


def _assess(a: Optional[Dict[str, Any]], q: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sim = similarity_view((a or {}).get("legacy"))
    if q is not None and not I.is_question(q):
        return _base("not_applicable", "not_a_technical_question", "none", sim)
    if not a:
        return _base("not_applicable", "not_reached", "none", sim)
    if a.get("skipped"):
        return _base("not_applicable", "skipped", "none", sim)
    terms = a.get("terms") or {}
    if no_attempt(a.get("answer", ""), terms):
        hint = [f"Review the core idea: {', '.join(terms['missing'][:3])}." if terms.get("missing") else "Review the core idea behind this question."]
        return _base("incorrect", "no_attempt", "rules", sim, missing_concepts=list(terms.get("missing") or [])[:5],
                     feedback=["No answer to the question was given, so there is nothing to credit."] + hint)
    m = a.get("modular") or {}
    mode, status, view = m.get("mode") or "off", m.get("status"), m.get("view")
    if mode == "off" or status == "not_requested":
        return _base("unavailable", "evaluator_off", "none", sim,
                     feedback=["Correctness was not checked: the concept check (local model) is off for this interview. The similarity value is not a substitute."])
    if status == "pending":
        return _base("pending", "evaluator_running", "none", sim)
    if status in ("interrupted", "failed") or not view:
        return _base("unavailable", "evaluator_unavailable", "none", sim, feedback=["The correctness check did not return a result for this answer. Nothing was assumed."])
    vst = view.get("status")
    if vst in ("provider_error", "invalid_response", "scope_unavailable"):
        return _base("unavailable", f"evaluator_{vst}", "none", sim, feedback=["The correctness check failed for this answer (model unavailable or unusable reply). Nothing was assumed."])
    tags = (view.get("source") or {}).get("tags") or []
    basis = "mock_verifier" if (mode == "mock" or "MOCK VERIFIER" in tags) else "local_model_concept_check"
    if vst == "not_gradable":
        return _base("uncertain", "answer_not_gradable", basis, sim, feedback=["The answer could not be assessed automatically."])
    applied = (view.get("safeguards") or {}).get("applied") or []
    if applied:
        return _base("uncertain", "safeguard:" + applied[0], basis, sim, feedback=["The answer was not fully assessed (it was truncated or contained text aimed at the evaluator)."])
    if ((view.get("taxonomy") or {}).get("primary")) == "off_topic_confirmed":
        return _base("incorrect", "off_topic", basis, sim, feedback=["The answer does not address the question that was asked."])

    outcomes = _adjust_outcomes(view.get("outcomes") or [], (q or {}).get("question") or "", a.get("answer") or "")
    fb = view.get("feedback") or {}
    ess = [o for o in outcomes if o.get("tier") == "essential" and not o.get("topic_only")]
    sup = [o for o in outcomes if o.get("tier") != "essential"]
    sat = [o["label"] for o in ess if o.get("status") == "satisfied"]
    miss = [o["label"] for o in ess if o.get("status") == "missing"]
    known = ("satisfied", "missing", "not_demonstrated", "incorrect")
    und = [o.get("label", "?") for o in outcomes if o.get("status") not in known and not o.get("topic_only")]            # an unknown or absent status counts as undetermined, never as missing
    correct = sat + [o["label"] for o in sup if o.get("status") == "satisfied"]
    optional_missing = [o["label"] for o in sup if o.get("status") == "not_demonstrated"]
    errs = [{"claim": (e.get("your_words") or [None])[0], "why": e.get("why_wrong"), "reference_says": e.get("reference_says"), "concept": e.get("concept"), "source": "concept_check"}
            for e in (fb.get("factual_errors") or [])]
    cx_items, cx_status = _contradiction_misconceptions(view)
    misconceptions, seen = [], set()
    for m in errs + cx_items:                                                                  # one wrong statement is one misconception, however many checks found it
        if m["claim"] not in seen:
            seen.add(m["claim"])
            misconceptions.append(m)
    extra = dict(correct_concepts=correct, missing_concepts=miss, optional_missing=optional_missing, unverified_concepts=und, misconceptions=misconceptions,
                 contradiction_check=cx_status)

    if not ess:
        verdict, reason = "uncertain", "no_curated_requirements"
    elif misconceptions:
        # A verified wrong statement caps the verdict. Only when the wrong statements outnumber the essential ideas demonstrated is the answer mostly wrong (one false claim
        # next to a right core definition is a partly right answer).
        verdict, reason = ("incorrect", "misconceptions_outweigh_correct_content") if len(misconceptions) > len(sat) else ("partially_correct", "misconception")
    elif len(sat) == len(ess):
        if cx_status != "checked":
            verdict, reason = "uncertain", "requirements_met_but_errors_not_checked"
        else:
            verdict, reason = "correct", "all_essential_demonstrated"
    elif not sat and not [o for o in ess if o.get("status") not in known]:
        sup_sat = [o for o in sup if o.get("status") == "satisfied"]
        # Nothing essential, but a supporting idea is right (a correct description that names none of the required mechanisms): partly right, not wrong.
        verdict, reason = ("partially_correct", "only_supporting_demonstrated") if sup_sat else ("incorrect", "no_essential_demonstrated")
    elif sat and miss:
        verdict, reason = "partially_correct", "some_essential_missing"
    else:
        verdict, reason = "uncertain", "evidence_incomplete"                                     # includes essentials with an unknown status
    if basis == "mock_verifier" and verdict == "correct":
        verdict, reason = "uncertain", "mock_verifier_cannot_confirm"
    return _base(verdict, reason, basis, sim, feedback=_feedback(verdict, correct, miss, misconceptions, und, cx_status, basis), **extra)


def _feedback(verdict: str, correct: List[str], miss: List[str], misc: List[Dict[str, Any]], und: List[str], cx_status: str, basis: str) -> List[str]:
    """At most three short, actionable lines, built only from verified findings."""
    out: List[str] = []
    if misc:
        out.append("Correct the statement" + ("s" if len(misc) > 1 else "") + " listed above first; " + ("it is" if len(misc) == 1 else "they are") + " the main problem with this answer.")
    if miss and len(out) < 3:
        out.append("Add: " + "; ".join(miss[:3]) + ".")
    if verdict == "correct" and len(out) < 3:
        out.append("The essential ideas are there" + (f" ({'; '.join(correct[:3])})" if correct else "") + ". To strengthen it, add an example or a trade-off.")
    if verdict == "uncertain" and len(out) < 3:
        out.append("The automatic check could not decide" + (f" on: {'; '.join(und[:3])}" if und else "") + ". This is not a judgement that the answer is wrong.")
    if cx_status in ("error", "not_checked") and verdict != "unavailable" and basis != "mock_verifier" and len(out) < 3:
        out.append("The check for wrong statements did not run for this answer.")
    if basis == "mock_verifier":
        out.append("Mock verifier (word-overlap stand-in): this demonstrates the pipeline only and is not an assessment of your answer.")
    return out[:4]


def _clip(text: Optional[str], n: int = 140) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def session_overview(session: Dict[str, Any]) -> Dict[str, Any]:
    """Counts of verdicts over the technical questions of one interview, for the summary page. Similarity is never mixed in."""
    counts = {k: 0 for k in VERDICTS}
    rows = []
    for i, (q, a) in enumerate(zip(session.get("questions") or [], session.get("answers") or [])):
        if not I.is_question(q):
            continue
        r = assess(a, q)
        counts[r["verdict"]] += 1
        rows.append({"n": i + 1, "topic": q.get("topic") or q.get("domain"), "assessment": r})
    assessed = sum(counts[k] for k in ("correct", "partially_correct", "incorrect", "uncertain"))
    return {"counts": counts, "assessed": assessed, "rows": rows, "misconceptions": [{"n": r["n"], "topic": r["topic"], **m} for r in rows for m in r["assessment"]["misconceptions"]]}

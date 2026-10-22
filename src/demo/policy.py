"""Stage 10C: the controlled, evidence-aware interview policy (replaces the fixed Easy -> Medium -> Hard ladder for technical slots).

Architecture (hybrid, and the order matters):
  1. DETERMINISTIC policy (this file): what kind of move comes next, within fixed structure and limits (time budget, one follow-up per answer, restraint on memory references).
  2. RETRIEVAL: the next technical question is chosen from the VETTED bank (existing search function: Sentence-BERT/FAISS when installed, BM25 otherwise).
  3. A local LLM (optional, followup_llm) may only WORD a follow-up from the answer; this module never needs it.
  4. A VERIFICATION layer (`verify_question`) rejects repeated, unsupported ("you said X" with no stored X) or instruction-like text, whoever wrote it.

Signals are deliberately modest and honest: exact-word concept coverage (a hint, not correctness), answer length, uncertainty/refusal phrases. Semantic similarity is NOT used to decide that an answer was
good or bad, and nothing here grades an answer. Every decision is logged as CODES (no candidate text) in `plan["policy_log"]`.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Tuple, Any, Callable, Dict, List, Optional, Sequence

from . import behavioural as B
from . import interview as I
from . import memory as M

DECISIONS = ("deeper", "clarify", "explore_related", "revisit", "new_competency", "practical", "wrapup", "continue")
DEFAULT_TIME_BUDGET_S = 45 * 60
WRAP_FRACTION = 0.85
MEMORY_MAX_REFS = 4
_STEP = {"Easy": 0, "Medium": 1, "Hard": 2}
_DIFF = ("Easy", "Medium", "Hard")
_REF_CUE = re.compile(r"\b(earlier|previously|you (?:mentioned|said|described|explained|noted)|as you said|your (?:earlier|previous))\b", re.I)


# ------------------------------------------------------------------------------------------------ verification layer
def asked_questions(session: Dict[str, Any], upto: Optional[int] = None) -> List[str]:
    qs = session.get("questions", [])
    return [q["question"] for q in (qs if upto is None else qs[:upto + 1]) if q.get("question") and I.stage_of(q) != I.INTRO]


def _jac(a: str, b: str) -> float:
    ta, tb = set(M._tokens(a)), set(M._tokens(b))
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def verify_question(session: Dict[str, Any], text: str, *, memory_ids: Sequence[str] = (), upto: Optional[int] = None, max_jaccard: float = 0.55) -> List[str]:
    """Reasons to REJECT a candidate question text (empty list = acceptable). Never trusts the author of the text."""
    reasons = []
    t = re.sub(r"\s+", " ", text or "").strip()
    if not 12 <= len(t) <= 420:
        reasons.append("length")
    if M.looks_like_instruction(t):
        reasons.append("instruction_like")
    if re.search(r"https?://|www\.|```", t):
        reasons.append("link_or_code")
    for prev in asked_questions(session, upto):
        if prev.strip().lower() == t.lower() or _jac(prev, t) >= max_jaccard:
            reasons.append("repeats_earlier_question")
            break
    if _REF_CUE.search(t) and not memory_ids:
        reasons.append("unsupported_memory_reference")
    mem = M.ensure(session)
    for mid in memory_ids:
        if M.get(mem, mid) is None:
            reasons.append("unknown_memory_id")
    return reasons


# ------------------------------------------------------------------------------------------------ signals and the decision
def signals(rec: Optional[Dict[str, Any]], answer: str) -> Dict[str, Any]:
    words = I.word_count(answer)
    tc = I.term_check(rec, answer) if rec else {"found": [], "missing": []}
    total = len(tc["found"]) + len(tc["missing"])
    cov = (len(tc["found"]) / total) if total else None
    return {"words": words, "coverage": cov, "uncertain": bool(M.uncertainty_cues(answer)), "refused": M.is_refusal(answer), "short": words < I.SHORT_ANSWER_WORDS,
            "found": len(tc["found"]), "total": total}


def band(sig: Dict[str, Any]) -> str:
    """strong | partial | weak | refused | unknown. A band of the evidence IN THE TEXT, never a judgement of correctness."""
    if sig["refused"]:
        return "refused"
    if sig["uncertain"] or sig["short"]:
        return "weak"
    c = sig["coverage"]
    if c is None:
        return "unknown"
    if c >= 0.6 and sig["words"] >= 20:
        return "strong"
    if c < 0.25:
        return "weak"
    return "partial"


def elapsed_s(session: Dict[str, Any], now: Optional[datetime] = None) -> float:
    try:
        t0 = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
        return ((now or datetime.now(timezone.utc)) - t0).total_seconds()
    except Exception:
        return 0.0


def time_state(session: Dict[str, Any], now: Optional[datetime] = None) -> str:
    budget = float((session.get("plan") or {}).get("time_budget_s", DEFAULT_TIME_BUDGET_S))
    e = elapsed_s(session, now)
    return "over" if e >= budget else "wrapping" if e >= WRAP_FRACTION * budget else "ok"


def decide(session: Dict[str, Any], i: int, sig: Dict[str, Any], *, has_open_contradiction: bool, revisit_available: bool, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Pick the move. Returns {'decision', 'target_difficulty_step', 'reasons': [codes]}; the order below is the priority."""
    q = session["questions"][i]
    ts = time_state(session, now)
    b = band(sig)
    reasons = [f"band:{b}", f"time:{ts}"]
    base = _STEP.get(q.get("difficulty") or "Medium", 1)
    remaining = [k for k in range(i + 1, len(session["questions"])) if session["answers"][k] is None and I.stage_of(session["questions"][k]) in (I.CORE, I.BEHAVIOURAL)]
    nxt = next((k for k in range(i + 1, len(session["questions"])) if session["answers"][k] is None), None)
    if ts in ("over", "wrapping") and remaining:
        return {"decision": "wrapup", "step": base, "reasons": reasons + ["time_budget"], "keep_next": ts == "wrapping"}
    if has_open_contradiction:
        return {"decision": "clarify", "step": base, "reasons": reasons + ["contradiction_open"]}
    if b == "refused":
        return {"decision": "new_competency", "step": max(0, base - 1), "reasons": reasons + ["candidate_declined"]}
    if b == "weak":
        return {"decision": "new_competency", "step": max(0, base - 1), "reasons": reasons + ["little_evidence_in_text"]}
    if revisit_available:
        return {"decision": "revisit", "step": base, "reasons": reasons + ["relevant_earlier_statement"]}
    if b == "strong":
        return {"decision": "deeper", "step": min(2, base + 1), "reasons": reasons + ["key_concepts_stated"]}
    if nxt is not None and I.stage_of(session["questions"][nxt]) == I.PRACTICAL and not remaining:
        return {"decision": "practical", "step": base, "reasons": reasons + ["core_questions_done"]}
    return {"decision": "explore_related", "step": base, "reasons": reasons + ["partial_or_unknown"]}


def log(session: Dict[str, Any], entry: Dict[str, Any]) -> None:
    session.setdefault("plan", {}).setdefault("policy_log", []).append(entry)


# ------------------------------------------------------------------------------------------------ memory-linked wording (deterministic, original, attribution-safe)
def _clean(t: str, n: int = 90) -> str:
    return re.sub(r"[\"“”\n\r]+", " ", re.sub(r"\s+", " ", t or "")).strip()[:n].rstrip(" ,;:.")


# Stage 10D/E: a small, readable theme table. It decides one thing only: "this question is about evaluating / training / preparing data for a model", so that a candidate's own stated
# model-building project is a RELEVANT thing to ask about. It is a text rule, not a judgement of the candidate; it never creates a memory, it only lets an existing one be mentioned.
THEMES = {
    "evaluation": ("validation", "evaluation", "evaluate", "evaluating", "metric", "metrics", "accuracy", "precision", "recall", "f1", "auc", "roc", "overfit", "overfitting", "generalis", "generaliz",
                   "generalisation", "generalization", "held", "test set", "split", "leakage", "confusion", "calibration", "bias", "variance", "cross"),
    "training": ("training", "optimiser", "optimizer", "optimisation", "optimization", "gradient", "backprop", "backpropagation", "loss", "epoch", "epochs", "learning rate", "regularis", "regulariz",
                 "regularisation", "regularization", "dropout", "batch", "normalis", "normaliz", "normalisation", "normalization", "initialis", "initializ", "neural", "deep learning", "transformer", "fine-tun"),
    "data": ("imbalance", "imbalanced", "missing", "outlier", "outliers", "feature", "features", "preprocess", "preprocessing", "cleaning", "sampling", "label", "labels", "augmentation"),
}
_ML_WORDS = frozenset("model models classifier classification regression predict prediction predictor train trained training neural network pipeline dataset detection segmentation forecasting recommender "
                      "learning pytorch tensorflow keras sklearn scikit".split())


_SEMANTIC_KINDS = ("project", "achievement", "challenge", "explanation", "experience", "technology")


def themes_of(text: str) -> List[str]:
    t = " " + re.sub(r"[^a-z0-9+#/\- ]", " ", (text or "").lower()) + " "
    return [name for name, words in THEMES.items() if any((" " + w) in t for w in words)]


def ml_project(item: Dict[str, Any]) -> bool:
    """The candidate's stored statement is about building or measuring a model (so evaluation / training / data questions about it make sense)."""
    return item.get("kind") in ("project", "achievement", "challenge") and bool(set(M._tokens(" ".join(filter(None, [item.get("subject"), item["text"], item["quote"]])))) & _ML_WORDS)


_THEME_ASK = {
    "evaluation": "How did you split the data and evaluate it there, and what did you do to keep information from the training data leaking into the test data?",
    "training": "How did you train it: which loss, optimiser and settings did you settle on, and why?",
    "data": "What was the main problem with the data there, and how did you deal with it?",
}


_CHAL_LEAD = re.compile(r"^(?:the|my|our)\s+(?:hardest|biggest|main|toughest|major|greatest|key|first)\s+(?:challenge|problem|issue|difficulty|obstacle)\s*(?:was|is|were)?\s*(?:that\s+)?", re.I)


def _challenge_core(text: str, n: int = 80) -> str:
    c = _clean(text, n + 40)
    c = _CHAL_LEAD.sub("", c).strip() or c
    return _clean(c, n)


def memory_followup_text(item: Dict[str, Any], theme: Optional[str] = None) -> Optional[str]:
    """A question that refers to ONE earlier candidate statement, always as their own words. None when the kind has no safe template. `theme` (evaluation | training | data) picks a question
    that fits what was just being discussed, when the stored statement is about building a model."""
    subj = _clean(item.get("subject") or item["text"])
    k = item["kind"]
    if not subj or M.looks_like_instruction(subj):
        return None
    if k == "project":
        ask = _THEME_ASK.get(theme or "") if ml_project(item) else None
        return f"Earlier you said you {_clean(item['text'])}. " + (ask or "What was the hardest technical decision in that work, and why did you make it that way?")
    if k == "achievement":
        return f"You mentioned a result earlier: {_clean(item['text'])}. How did you check that result held up beyond the data you measured it on?"
    if k == "challenge":
        return f"Earlier you described a challenge: {_challenge_core(item['text'])}. How did you decide to deal with it, and what would you try differently now?"
    if k in ("technology", "tool"):
        return f"You said you used {subj} earlier. Why did you choose it over the alternatives?"
    if k == "role" and (item["text"].split() or [""])[0] in ("led", "managed", "mentored", "supervised", "coordinated", "organised", "organized", "owned"):
        return f"Earlier you said you {_clean(item['text'])}. How did you decide what to focus on there?"
    return None


def _first_clause(t: str, n: int = 100) -> str:
    t = _clean(re.split(r"(?<=[.!?])\s+", (t or "").strip())[0], n + 40)
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0]
    return t.rstrip(" ,;:.")


def revisit_lead(item: Dict[str, Any], topic: str) -> str:
    if item["kind"] == "explanation":
        what = (item.get("subject") or topic or "this").lower()
        q = _first_clause(item["quote"])
        if q[:1].isupper() and 5 <= len(q.split()) <= 16:                           # a quote only when it starts like a sentence (the stored span can begin mid-sentence)
            return f"Earlier you explained {what}, in your words: \"{q}\". This one goes a step further."
        return f"Earlier you explained {what}. This one goes a step further."
    if item["kind"] in ("project", "technology", "tool") or (item["kind"] == "role" and (item["text"].split() or [""])[0] in ("led", "managed", "mentored", "owned")):
        return f"Earlier you said you {_clean(item['text'], 90)}. Keep that in mind for this question."
    if item["kind"] == "challenge":
        return f"Earlier you described a challenge: {_challenge_core(item['text'])}. Keep that in mind for this question."
    return f"Earlier you mentioned {_clean(item.get('subject') or item['text'], 70)}. Keep that in mind for this question."


def query_parts(question: str, topic: str = "", answer: str = "") -> List[str]:
    """Several short queries (the question+topic, then each substantial sentence of the answer) so a long answer does not dilute a specific mention."""
    parts = [" ".join(filter(None, [question, topic]))]
    for _, _, sent in M._sentences(answer or "")[:8]:
        if I.word_count(sent) >= 4 and not M.looks_like_instruction(sent):
            parts.append(sent)
    return parts


SEMANTIC_FLOOR = 0.45          # 10J: Sentence-BERT cosine (raw, before any boost) at which a stored project / claim counts as related on MEANING alone. UNCALIBRATED: every call records its numbers (diag) so the first real run can set it.


def semantic_floor() -> float:
    import os
    try:
        return float(os.environ.get("SMART_DEMO_MEMORY_SEMANTIC_FLOOR", SEMANTIC_FLOOR))
    except ValueError:
        return SEMANTIC_FLOOR


def memory_relevance(session: Dict[str, Any], query: Any, turn_now: int, *, kinds: Optional[Sequence[str]] = None, embedder=None, k: int = 1, force: bool = False,
                     target_topic: Optional[Sequence[str]] = None, themed: bool = True, answered_turn: Optional[int] = None, diag: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Select memory items worth mentioning for `query`. 10D: a reference needs a REAL reason: a shared content word with the query, or (for a stored model-building project, achievement or
    challenge) a matching theme (evaluation / training / data). A bare topic-label link is only a preference for choosing questions; it is never a reason to mention what the candidate said
    (it attached "Earlier you explained logistic regression" to a Fourier-transform question). Each hit carries `reason`."""
    mem = M.ensure(session)
    excl = [turn_now if answered_turn is None else answered_turn]                  # `turn_now` is where the NEW question will appear; the statement being answered right now is never recalled
    ms = 0.2 if not force else 0.08
    if len(mem.get("refs", [])) == 0 and turn_now >= 4:
        ms = min(ms, 0.1)                                                          # nothing was recalled yet and the interview is well under way: allow a weaker match once
    tt = tuple(target_topic) if target_topic else None
    cand = M.select(session, query, turn_now=turn_now, k=6, min_score=ms, kinds=kinds, embedder=embedder, exclude_turns=excl, max_total_refs=MEMORY_MAX_REFS, target_topic=tt, diag=diag)
    qtext = " ".join([query] if isinstance(query, str) else query)
    qt = set(M._tokens(qtext))
    out = []
    qtok = set(M._tokens(qtext))
    for c in cand:
        if M.specific_overlap(c["item"], qtok):
            out.append({**c, "reason": "shared_words"})
    have0 = {c["item"]["id"] for c in out}
    for c in cand:                                                              # 10J: related on MEANING (Sentence-BERT only; the lexical embedder's number is not semantic evidence)
        if c["item"]["id"] not in have0 and c.get("embedder") == "sentence-bert" and c.get("sim_raw", 0) >= semantic_floor() and c["item"]["kind"] in _SEMANTIC_KINDS:
            out.append({**c, "reason": "semantic"})
    if themed:
        th = themes_of(query if isinstance(query, str) else (query[0] if query else ""))        # the QUESTION and its topic decide the theme, never the answer text
        if th:
            extra = M.select(session, query, turn_now=turn_now, k=6, min_score=0.0, kinds=tuple(x for x in ("project", "achievement", "challenge") if kinds is None or x in kinds) or ("project",),
                             embedder=embedder, exclude_turns=excl, max_total_refs=MEMORY_MAX_REFS, target_topic=tt)
            have = {c["item"]["id"] for c in out}
            for c in extra:
                if c["item"]["id"] not in have and ml_project(c["item"]) and c["item"].get("referenced", 0) == 0:
                    out.append({**c, "reason": "theme:" + th[0], "theme": th[0]})
    rank = {"project": 0, "challenge": 1, "achievement": 2}
    out.sort(key=lambda r: (r["reason"].startswith("theme"), -round(r["score"], 1) if not r["reason"].startswith("theme") else 0, rank.get(r["item"]["kind"], 3), -r["score"]))
    pre_dedupe = {r["item"]["id"]: r["reason"] for r in out}
    seen_claims, uniq = set(), []                                                # one stored SENTENCE yields several items (project + technology): offer it once, best-ranked first
    for r in out:
        key = (r["item"]["turn"], r["item"]["quote"])
        if key not in seen_claims:
            seen_claims.add(key)
            uniq.append(r)
    out = uniq
    if diag is not None:
        why = {r["item"]["id"]: r["reason"] for r in out}
        kept = {r["item"]["id"] for r in out[:k]}
        for d in diag:
            if d.get("stage") == "select":
                d["gate"] = why.get(d["id"]) or ("deduplicated_same_claim" if d["id"] in pre_dedupe else None) or ("rejected:below_min_score" if not d["passed_min_score"] else "rejected:no_shared_word_theme_or_semantic_link")
                d["offered"] = d["id"] in kept
    return out[:k]


# ------------------------------------------------------------------------------------------------ choosing the next technical question
def _qtoks(r: Dict[str, Any]) -> set:
    return I._qtoks(r)


def pick_next_core(engine, session: Dict[str, Any], slot_index: int, *, answered_index: int, answer: str, target_step: int, decision: str, records: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Re-select the content of the next unasked technical slot from the vetted bank. Returns the replacement item (not yet inserted) or None to keep the planned one."""
    qs = session["questions"]
    slot = qs[slot_index]
    cfg = session.get("config") or {}
    domains = set(cfg.get("domains") or [slot["domain"]])
    done_ids = {q.get("question_id") for q in qs[:slot_index] if q.get("question_id")}
    asked_txt = [q["question"] for q in qs[:slot_index] if q.get("question")]
    planned_later = {q.get("question_id") for k, q in enumerate(qs) if k > slot_index and q.get("question_id")}
    from ..codeeval.extract import question_expects_code
    pool = [r for r in records if r["domain"] == slot["domain"] and r["question_id"] not in done_ids and r["question_id"] not in planned_later
            and (r.get("question_type") or "") not in I.PRACTICAL_TYPES and not question_expects_code(r.get("question", ""), r.get("question_type") or "")]
    pool = [r for r in pool if not any(_jac(r["question"], t) >= 0.55 for t in asked_txt)]
    if not pool:
        return None
    parent = qs[answered_index]
    query = " ".join(filter(None, [parent.get("topic"), parent.get("domain"), " ".join(M._tokens(answer))[:200]]))
    ranks: Dict[str, int] = {}
    fn = getattr(engine, "_search_fn", None)
    if fn is not None:
        try:
            res = fn(query, slot["domain"])
            ranks = {h["question_id"]: n for n, h in enumerate(res.get("results") or [])}
        except Exception:
            ranks = {}
    used_topics = {(q.get("domain"), q.get("topic")) for q in qs[:slot_index] if I.is_question(q)}
    same_topic = (parent.get("domain"), parent.get("topic"))

    mem = M.ensure(session)
    refs = mem.get("refs", [])
    can_link = len(refs) < MEMORY_MAX_REFS and not (refs and slot_index + 1 - refs[-1]["turn"] < 2)
    linked_topics = {(t[0], t[1]) for it in M.active_items(mem) if can_link and it["kind"] in ("project", "technology", "achievement", "challenge") and it["confidence"] != "low"
                     and it.get("referenced", 0) == 0 and it["turn"] <= answered_index + 1 for t in (it.get("topics") or [])}

    def key(r: Dict[str, Any]):
        d = abs(_STEP.get(r.get("difficulty"), 1) - target_step)
        topic = (r["domain"], r["topic"])
        link = 0 if topic in linked_topics else 1
        topic_pref = 0 if (decision == "deeper" and topic == same_topic) else (1 if topic in used_topics else 0) if decision != "deeper" else 1
        if decision == "new_competency":
            topic_pref = 1 if topic in used_topics else 0
        return (d, link, topic_pref, ranks.get(r["question_id"], 999), r["question_id"])
    best = sorted(pool, key=key)[0]
    it = I._item(best, I.CORE, selected_by=f"adaptive policy ({decision})", matched=[], retrieval_mode=((session.get("plan") or {}).get("retrieval") or {}).get("mode") or "none" if ranks else "none", rank=ranks.get(best["question_id"]) and ranks[best["question_id"]] + 1,
                 slot=f"{best['domain']} / {best['topic']} ({_DIFF[target_step]} target)")
    it["origin"] = "adaptive_bank"
    it["provenance"]["selected_by"] = f"adaptive policy ({decision}); vetted bank question; difficulty target {_DIFF[target_step]}"
    return it


def _finish_replacement(session: Dict[str, Any], new: Dict[str, Any], nxt: int) -> None:
    qs = session["questions"]
    lead_idx = sum(1 for q in qs[:nxt] if I.stage_of(q) == I.CORE)
    new["lead"] = I.lead_in(new, lead_idx, first_core=lead_idx == 0)
    try:
        from . import experimental as MA
        mode = (session.get("config") or {}).get("modular_mode", "off")
        new["scorable"] = MA.is_scorable(new["question_id"]) if mode != "off" else None
    except Exception:
        new["scorable"] = None
    try:
        from . import codeassess as CA
        new["code_spec"] = CA.has_spec(new["question_id"]) if (session.get("config") or {}).get("code_eval") else None
    except Exception:
        new["code_spec"] = None


CONTINUITY_MIN_GAP = 2        # positions between the introductory explanation and the harder question that builds on it (a follow-up in between counts)


def continuity_pick(engine, session: Dict[str, Any], slot_index: int, *, n: int, records: Sequence[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """(replacement question, the memory item it builds on) or None. Scenario: the candidate explained a topic at an introductory level; a few turns later, a HARDER vetted question on the same
    topic is asked and its lead quotes their earlier explanation. Never repeats the earlier question, honours the memory restraint rules, builds only on an unreferenced explanation."""
    mem = M.ensure(session)
    refs = mem.get("refs", [])
    if len(refs) >= MEMORY_MAX_REFS or (refs and slot_index + 1 - refs[-1]["turn"] < 2):     # turns are DISPLAYED positions, the same unit the candidate sees
        return None
    qs = session["questions"]
    done_ids = {q.get("question_id") for q in qs[:slot_index] if q.get("question_id")}
    planned_later = {q.get("question_id") for k, q in enumerate(qs) if k > slot_index and q.get("question_id")}
    asked_txt = [q["question"] for q in qs[:slot_index] if q.get("question")]
    for it in sorted(M.active_items(mem), key=lambda x: x["turn"]):
        if it["kind"] != "explanation" or it["confidence"] == "low" or it.get("referenced", 0) or slot_index + 1 - it["turn"] < CONTINUITY_MIN_GAP or not 1 <= it["turn"] <= len(qs):
            continue
        src = qs[it["turn"] - 1]
        if not I.is_question(src) or not src.get("question_id") or src.get("difficulty") not in _STEP:
            continue
        base = _STEP[src["difficulty"]]
        pool = [r for r in records if r["domain"] == src["domain"] and r["topic"] == src["topic"] and _STEP.get(r.get("difficulty"), 1) > base and r["question_id"] not in done_ids
                and r["question_id"] not in planned_later and (r.get("question_type") or "") not in I.PRACTICAL_TYPES and not any(_jac(r["question"], t) >= 0.55 for t in asked_txt)]
        if not pool:
            continue
        best = sorted(pool, key=lambda r: (_STEP[r["difficulty"]], r["question_id"]))[0]
        new = I._item(best, I.CORE, selected_by="continuity", matched=[], retrieval_mode=((session.get("plan") or {}).get("retrieval") or {}).get("mode") or "none", rank=None,
                      slot=f"{best['domain']} / {best['topic']} (builds on your earlier explanation)")
        new["origin"] = "adaptive_bank"
        new["provenance"]["selected_by"] = "adaptive policy (revisit): a harder vetted question on the same topic as an explanation you gave earlier"
        lead = revisit_lead(it, best["topic"])
        if [r for r in verify_question(session, lead, memory_ids=[it["id"]], upto=n) if r != "repeats_earlier_question"]:
            continue
        return new, it
    return None


def apply_adaptation(engine, session: Dict[str, Any], i: int, rec: Optional[Dict[str, Any]], answer: str, n: int, decision: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate the plan according to the decision. Caller holds the store lock. Returns a small report of what changed (codes only)."""
    qs, ans = session["questions"], session["answers"]
    out: Dict[str, Any] = {"replaced": None, "memory_ref": None, "truncated": 0}
    d = decision["decision"]
    if d == "wrapup":
        keep = next((k for k in range(i + 1, len(qs)) if ans[k] is None), None) if decision.get("keep_next", True) else None
        if keep is None:
            keep = i
        for k in range(len(qs) - 1, keep, -1):
            if ans[k] is None and I.stage_of(qs[k]) in (I.CORE, I.PRACTICAL, I.BEHAVIOURAL):
                qs.pop(k); ans.pop(k); out["truncated"] += 1
        session.setdefault("plan", {})["ended_reason"] = "time_budget" if out["truncated"] else session.get("plan", {}).get("ended_reason")
        return out
    nxt = next((k for k in range(i + 1, len(qs)) if ans[k] is None and I.stage_of(qs[k]) == I.CORE), None)
    if nxt is None or (session.get("plan") or {}).get("adaptive") is False:
        return out
    # technical slot: re-select from the vetted bank
    if d in ("deeper", "explore_related", "new_competency", "revisit", "clarify"):
        step = decision["step"]
        if d in ("deeper", "explore_related", "revisit"):                           # a weak answer is never answered with a harder question on the same thing
            cp = continuity_pick(engine, session, nxt, n=n, records=engine.records())
            if cp is not None:
                new, it = cp
                _finish_replacement(session, new, nxt)
                new["lead"] = revisit_lead(it, new.get("topic") or "")
                new.setdefault("provenance", {})["memory_ref"] = {"id": it["id"], "turn": it["turn"], "kind": it["kind"], "claim_status": "candidate claim (not verified)", "reason": "continuity"}
                qs[nxt] = new
                M.mark_referenced(session, [it["id"]], nxt + 1)
                out.update(replaced=new["question_id"], memory_ref=it["id"], continuity=True)
                return out
        new = pick_next_core(engine, session, nxt, answered_index=i, answer=answer, target_step=step, decision=d, records=engine.records())
        if new is not None and new["question_id"] != qs[nxt].get("question_id"):
            _finish_replacement(session, new, nxt)
            qs[nxt] = new
            out["replaced"] = new["question_id"]
        # an earlier statement that matters for this question -> say so in the lead (never inside the bank question text)
        target = qs[nxt]
        q_text = " ".join(filter(None, [target["question"], target.get("topic")]))             # not the domain label: "Deep Learning" would match any deep-learning memory
        hit = memory_relevance(session, q_text, nxt + 1, answered_turn=n, kinds=("project", "explanation", "achievement", "challenge", "technology"), target_topic=(target.get("domain"), target.get("topic")))
        if hit:
            it = hit[0]["item"]
            bad = verify_question(session, revisit_lead(it, target.get("topic") or ""), memory_ids=[it["id"]], upto=i)
            if not [r for r in bad if r != "repeats_earlier_question"]:
                target["lead"] = (revisit_lead(it, target.get("topic") or "") + " " + (target.get("lead") or "")).strip()
                target.setdefault("provenance", {})["memory_ref"] = {"id": it["id"], "turn": it["turn"], "kind": it["kind"], "claim_status": "candidate claim (not verified)", "reason": hit[0].get("reason")}
                M.mark_referenced(session, [it["id"]], nxt + 1)
                out["memory_ref"] = it["id"]
    return out


def followup_query(question: str, topic: str, answer: str, record: Optional[Dict[str, Any]] = None) -> List[str]:
    """What an earlier statement is compared with when a follow-up is being written: the question+topic, each substantial sentence of the answer, and (10J) the VETTED concepts of the question
    (their labels), so 'I trained a spam classifier on labelled emails' meets 'What is supervised learning?' through 'labelled training data' and 'classification'. The curated reference answer is a
    separate part, used the same way. Never the candidate's text alone; never a score of the answer."""
    parts = query_parts(question, topic, answer)
    if record:
        from . import followup_llm as FL
        cons = FL.concepts_for(record)
        labels = " ".join(" ".join([c["label"]] + list(c.get("members", []))) for c in cons)
        if labels.strip():
            parts.append(labels)
        ref = str(record.get("canonical_answer") or "")
        if ref.strip():
            parts.append(" ".join(ref.split()[:60]))
    return parts


def retrieve_for_followup(session: Dict[str, Any], qi: Dict[str, Any], answer: str, n: int, record: Optional[Dict[str, Any]] = None, k: int = 2, embedder=None,
                          diag: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """The ONE place that decides which earlier statements a live follow-up may build on (the engine and the benchmark harness both call it, so the benchmark measures the real thing).
    `n` is the 1-based number of the question being answered; the new question will appear at n+1."""
    return memory_relevance(session, followup_query(qi["question"], qi.get("topic") or "", answer, record), n + 1, answered_turn=n, k=k, target_topic=(qi.get("domain"), qi.get("topic")), embedder=embedder, diag=diag)

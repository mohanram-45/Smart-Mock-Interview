"""Stage 10B: the behavioural / HR interview engine.

Content: `behavioural_data/` (original, versioned, reviewable; see POLICY.md there). Method: STAR-inspired EVIDENCE reading. For an answer we look for text that carries a situation, a task, the
candidate's own action and a result, and we quote it exactly. "Not found" means "not in the text as written": it never means "did not happen". There are no scores or percentages, no hire/reject
output, and nothing about protected characteristics, appearance, accent or emotions. Everything here is deterministic; a local model may only reword a probe elsewhere (followup_llm).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import interview as I
from . import memory as M

DATA = Path(__file__).with_name("behavioural_data")
INTERVIEW_TYPES = ("technical", "behavioural", "mixed")
N_BEHAVIOURAL = 5                      # behavioural questions after the introduction in a behavioural interview
N_MIXED_TECH, N_MIXED_BEH = 3, 3
MAX_BEH_PROBES = 2


@lru_cache(maxsize=1)
def competencies() -> Dict[str, Any]:
    return json.loads((DATA / "competencies_v1.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def bank() -> Dict[str, Any]:
    return json.loads((DATA / "questions_v1.json").read_text(encoding="utf-8"))


def versions() -> Dict[str, str]:
    return {"rubric": competencies()["version"], "questions": bank()["version"]}


def competency(cid: str) -> Optional[Dict[str, Any]]:
    return next((c for c in competencies()["competencies"] if c["id"] == cid), None)


def intro_text(role: Optional[str]) -> str:
    return bank()["intro"].replace("{role}", role or "this kind of")


# ------------------------------------------------------------------------------------------------ planning
def _kw_score(text: str, comp: Dict[str, Any]) -> float:
    low = (text or "").lower()
    return sum(1.0 for k in comp["keywords"] if k in low)


def plan_behavioural(role: Optional[str], jd_text: Optional[str], n: int, rng) -> List[Dict[str, Any]]:
    """n behavioural items, each a different competency, ordered by role/JD keyword relevance with a seeded shuffle for ties. Original bank text only."""
    comps = list(competencies()["competencies"])
    order = {c["id"]: _kw_score(" ".join(filter(None, [jd_text, role])), c) + rng.random() * 0.5 for c in comps}
    pick = sorted(comps, key=lambda c: -order[c["id"]])[:n]
    # a stable, natural arc: teamwork/problem-solving first, failure/motivation later
    arc = {"teamwork": 0, "problem_solving": 1, "communication": 2, "conflict": 3, "leadership": 3, "adaptability": 4, "pressure": 4, "failure": 5, "motivation": 6}
    pick.sort(key=lambda c: arc.get(c["id"], 4))
    items = []
    for c in pick:
        cands = [q for q in bank()["questions"] if q["competency"] == c["id"]]
        q = cands[int(rng.random() * len(cands)) % len(cands)]
        items.append(beh_item(q, c))
    return items


def beh_item(q: Dict[str, Any], comp: Dict[str, Any], *, selected_by: str = "competency rotation") -> Dict[str, Any]:
    return {"question_id": q["id"], "domain": "Behavioural", "difficulty": "", "topic": comp["title"], "question": q["text"], "question_type": "behavioural", "stage": I.BEHAVIOURAL,
            "origin": "behavioural_bank", "parent_n": None, "scored": False, "scorable": None, "code_spec": None, "competency": comp["id"],
            "provenance": {"record_id": q["id"], "source": "original behavioural bank (not scraped, not human-validated)", "selected_by": selected_by,
                           "rubric_version": competencies()["version"], "bank_version": bank()["version"]}}


def transition_text(kind: str, role: Optional[str] = None) -> str:
    if kind == "to_behavioural":
        return ("Thank you, that completes the technical part. I would now like to understand how you work with people and handle situations, so the next questions are about your experience. "
                "Concrete examples work best.")
    if kind == "first":
        return "Thanks for that introduction. I will ask you about a few real situations from your experience; concrete examples work best."
    return "Thanks. Let us move to a different area."


def competency_lead(comp: Dict[str, Any], index: int) -> str:
    leads = ("Let us talk about {t}.", "Moving on, this one is about {t}.", "Now I am interested in {t}.", "Next, {t}.")
    return leads[index % len(leads)].format(t=comp["title"].lower())


# ------------------------------------------------------------------------------------------------ STAR evidence extraction
_PAST_SIT = re.compile(r"\b(when|while|during|at (?:my|the|a) (?:\w+ )?(?:job|company|internship|university|college|school|lab|startup|team|work)|in (?:my|our|the) (?:last|previous|first|final) \w+|last (?:year|semester|summer|month)|(?:a|one|two|three) (?:year|month|week)s? ago|was (?:working|facing|dealing)|we were|there was|back in|in 20\d\d|during my|in my (?:capstone|thesis|project|internship))\b", re.I)
_TASK = re.compile(r"\b(my (?:job|role|task|goal|responsibility|part)|i was (?:responsible|asked|tasked|assigned|in charge|supposed|expected)|i (?:needed|had|have) to|(?:the )?(?:goal|objective|aim|deadline) (?:was|is)|was asked to|my aim)\b", re.I)
_STATIVE = frozenset("was were am are is had have has felt wanted needed hoped liked loved knew thought wished believed realised realized hated feared expected wondered seemed became appeared remained cared meant".split())
_IRREGULAR = frozenset("wrote rewrote led ran took made built chose sent spoke met taught found fixed gave held kept began set put got saw read drew told brought split spent paid left lost won hired".split())
_ADV = r"(?:then |first |also |immediately |personally |quickly |finally |later |again |carefully |myself )*"
_ACTION = re.compile(r"\bI\s+" + _ADV + r"(?P<v>[a-z][a-z-]+)\b", re.I)
_WE_ACTION = re.compile(r"\bwe\s+" + _ADV + r"(?P<v>[a-z][a-z-]+)\b", re.I)


_NEG = re.compile(r"\b(nothing|never|didn'?t|did not|couldn'?t|could not|wouldn'?t|no one|nobody)\b", re.I)


def _acts(rx, sent: str) -> bool:
    if _NEG.search(sent):
        return False                                                                       # "I did nothing" / "I never ..." is not an action to quote
    for m in rx.finditer(sent):
        v = m.group("v").lower()
        if v in _STATIVE or v in ("will", "would", "can", "could", "should", "may", "might", "must", "do", "don", "dont", "am", "m", "ve", "d", "ll", "not", "never"):
            continue
        if v in _IRREGULAR or (v.endswith("ed") and len(v) > 3):
            return True
    return False


_RESULT = re.compile(r"\b(as a result|resulted in|ended up|in the end|the outcome|the result|turned out|led to|which meant|so (?:the|we|it|that)|eventually|afterwards?|we (?:delivered|shipped|launched|finished|won|reached|solved)|was able to|it worked|worked well|succeeded|improved|reduced|increased|saved|delivered on|finished (?:on|ahead)|got (?:approved|accepted|promoted)|feedback (?:was|from)|approved|accepted|praised|adopted|signed off|submitted|launched|released|was delivered|were delivered|were able to|managed to|passed)\b", re.I)
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|percent|x\b|hours?|days?|weeks?|months?|users?|customers?|points?|ms|seconds?|minutes?|k\b)|\b(?:by|to|from|of)\s+\d+(?:\.\d+)?\b", re.I)
_REFLECT = re.compile(r"\b(i learned|i learnt|lesson|next time|in hindsight|looking back|would do (?:it )?differently|i would now|since then|i now|what i took|taught me|i realised|i realized|i have changed|going forward)\b", re.I)
_I = re.compile(r"\bI(?:'m|'ve|'d|'ll)?\b|\bmy\b|\bmyself\b")
_WE = re.compile(r"\b(?:we|we're|we've|our|us|the team)\b", re.I)
ELEMENTS = ("situation", "task", "action", "result")
_NEED_COMP = {"failure": "reflection"}


def _sent_spans(text: str):
    return M._sentences(text)


def star_evidence(answer: str, competency_id: Optional[str] = None) -> Dict[str, Any]:
    """Exact-quote evidence for S/T/A/R in ONE answer (or several answers joined with a space by the caller). Quotes are `answer[start:end]`."""
    text = answer or ""
    ev: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ELEMENTS}
    refl: List[Dict[str, Any]] = []
    quant: List[Dict[str, Any]] = []
    for s, e, sent in _sent_spans(text):
        if sent.endswith("?") or M.looks_like_instruction(sent):
            continue
        rec = {"quote": sent[:M.MAX_QUOTE], "start": s, "end": min(e, s + M.MAX_QUOTE)}
        if _acts(_ACTION, sent):
            ev["action"].append(rec)
        elif _acts(_WE_ACTION, sent):
            ev.setdefault("team_action", []).append(rec)
        if _TASK.search(sent):
            ev["task"].append(rec)
        if _RESULT.search(sent) or _NUMBER.search(sent):
            ev["result"].append(rec)
        if _NUMBER.search(sent):
            quant.append(rec)
        if _PAST_SIT.search(sent) and not _acts(_ACTION, sent):
            ev["situation"].append(rec)
        elif _PAST_SIT.search(sent) and len(ev["situation"]) == 0 and s == 0:
            ev["situation"].append(rec)
        if _REFLECT.search(sent):
            refl.append(rec)
    i_n, we_n = len(_I.findall(text)), len(_WE.findall(text))
    own = "unclear" if i_n + we_n < 2 else "personal" if i_n >= 2 * max(1, we_n) else "team" if we_n >= 2 * max(1, i_n) and not ev["action"] else "mixed"
    present = {k: bool(ev[k]) for k in ELEMENTS}
    gaps = []
    if not present["action"]:
        gaps.append("action" if own != "team" else "personal_action")
    if not present["result"]:
        gaps.append("result")
    elif not quant:
        gaps.append("measure")
    if competency_id in _NEED_COMP and not refl:
        if "measure" in gaps:
            gaps.insert(gaps.index("measure"), "reflection")                               # for a setback the lesson matters more than a number
        else:
            gaps.append("reflection")
    if not present["situation"] and not present["task"]:
        gaps.append("situation")
    return {"elements": {k: {"present": present[k], "evidence": ev[k][:3]} for k in ELEMENTS}, "ownership": own, "quantified_result": bool(quant), "quantified_evidence": quant[:2],
            "reflection": {"present": bool(refl), "evidence": refl[:2]}, "gaps": gaps, "words": I.word_count(text),
            "note": "Evidence means text found in the answer as written. A gap means it was not in the text, not that it did not happen."}


def combine(answers: Sequence[str]) -> str:
    return " ".join(a.strip() for a in answers if a and a.strip())


# ------------------------------------------------------------------------------------------------ probe policy (what, if anything, to ask next about THIS example)
def probe_for(evidence: Dict[str, Any], *, competency_id: Optional[str], probes_used: int, asked: Sequence[str] = (), answer: str = "", prior_answers_words: int = 0, rotation: int = 0) -> Optional[Dict[str, Any]]:
    """The single most useful natural follow-up for this example, or None. Order: personal action -> result -> measure -> (failure) reflection -> situation. Uses fixed, reviewable wording."""
    if probes_used >= MAX_BEH_PROBES:
        return None
    if I.word_count(answer) < 4 or M.is_refusal(answer):
        return None
    P = competencies()["probes"]
    kind_for = {"personal_action": "action", "action": "action", "result": "result", "measure": "measure", "reflection": "reflection", "situation": "situation"}
    for gap in evidence["gaps"]:
        k = kind_for.get(gap)
        if not k or k in asked:
            continue
        if probes_used >= 1 and k not in ("action", "result", "reflection"):
            continue                                                                       # a second question is only worth asking about the candidate's own action, the outcome or what they learned
        if k == "situation" and I.word_count(answer) >= 25:
            continue                                                                       # a long answer has set its own scene
        if gap == "measure" and probes_used >= 1:
            continue                                                                       # do not interrogate: at most one measure question and only early
        return {"kind": k, "gap": gap, "text": P[k][(rotation + (0 if probes_used == 0 else 1)) % len(P[k])], "reason": f"no '{gap}' evidence was found in the answer text"}
    return None


def project_prompt(comp: Dict[str, Any], project_subject: str) -> str:
    return comp["project_prompt"].replace("{project}", f"your {project_subject}" if not project_subject.lower().startswith(("the ", "my ", "our ")) else project_subject)


def probe_item(parent_n: int, parent: Dict[str, Any], probe: Dict[str, Any], *, origin: str = "behavioural_probe") -> Dict[str, Any]:
    return {"question_id": parent.get("question_id"), "domain": "Behavioural", "difficulty": "", "topic": parent.get("topic"), "question": probe["text"], "question_type": "", "stage": I.FOLLOW_UP,
            "origin": origin, "parent_n": parent_n, "scored": False, "scorable": None, "code_spec": None, "competency": parent.get("competency"), "followup_kind": f"behavioural_{probe['kind']}",
            "lead": "Thanks. One more thing on that example.",
            "provenance": {"record_id": parent.get("question_id"), "source": "fixed, reviewable behavioural probes", "method": f"deterministic: {probe['reason']}", "llm": False,
                           "rubric_version": competencies()["version"]}}


# ------------------------------------------------------------------------------------------------ qualitative feedback (no scores, no percentages, no decisions)
_PROTECTED = re.compile(r"\b(age|gender|race|ethnic\w*|religio\w*|disabilit\w*|accent|appearance|looks?|attractive|nationality|married|pregnan\w*|sexual\w*|emotion\w*|confiden(?:ce|t)\s+level)\b", re.I)
FEEDBACK_NOTICE = ("This is a reading of the examples you gave, based only on your words. It is not a score, not a prediction of how an employer would decide, and it has not been reviewed by a human interviewer.")


def feedback(session: Dict[str, Any]) -> Dict[str, Any]:
    """Separate behavioural feedback built from the session's answers. Returns {'available', 'notice', 'rubric_version', 'competencies': [...], 'practice': [...]}."""
    qs, ans = session.get("questions", []), session.get("answers", [])
    groups: Dict[int, Dict[str, Any]] = {}
    for i, q in enumerate(qs):
        st = I.stage_of(q)
        if st == I.BEHAVIOURAL:
            groups[i + 1] = {"q": q, "answers": []}
        elif st == I.FOLLOW_UP and q.get("origin") in ("behavioural_probe", "behavioural_memory", "behavioural_llm") and q.get("parent_n") in groups:
            pass
    for i, q in enumerate(qs):
        if I.stage_of(q) == I.FOLLOW_UP and q.get("parent_n") in groups and q.get("competency"):
            groups[q["parent_n"]]["answers"].append(i)
    out = []
    for n, g in groups.items():
        q, idxs = g["q"], [n - 1] + g["answers"]
        texts = [ans[k]["answer"] for k in idxs if k < len(ans) and ans[k] and not ans[k]["skipped"]]
        comp = competency(q.get("competency")) or {"id": q.get("competency"), "title": q.get("topic"), "improvement": {}, "indicators": []}
        if not texts:
            out.append({"competency": comp["title"], "question_n": n, "answered": False, "observations": [], "not_found": [], "suggestion": None, "evidence": {}})
            continue
        joined = combine(texts)
        ev = star_evidence(joined, comp.get("id"))
        obs, nf = [], []
        for k in ELEMENTS:
            e = ev["elements"][k]
            if e["present"]:
                obs.append({"element": k, "quote": e["evidence"][0]["quote"]})
            else:
                nf.append(k)
        if ev["reflection"]["present"]:
            obs.append({"element": "reflection", "quote": ev["reflection"]["evidence"][0]["quote"]})
        if ev["quantified_result"]:
            obs.append({"element": "measure", "quote": ev["quantified_evidence"][0]["quote"]})
        first_gap = next((g_ for g_ in ev["gaps"] if g_ in comp.get("improvement", {}) or g_ in ("personal_action", "measure", "reflection")), None)
        imp = comp.get("improvement", {})
        key = {"personal_action": "action", "measure": "result", "reflection": "result"}.get(first_gap, first_gap)
        sugg = imp.get(key) if key else None
        if first_gap == "measure":
            sugg = "Add how you knew it worked: a number, a decision, or feedback someone gave you."
        elif first_gap == "reflection":
            sugg = "End by saying what you learned or would do differently; for a setback this matters most."
        out.append({"competency": comp["title"], "question_n": n, "answered": True, "observations": obs, "not_found": nf, "ownership": ev["ownership"], "suggestion": sugg,
                    "indicators": comp.get("indicators", [])[:3], "evidence": {"words": ev["words"]}})
    answered = [c for c in out if c["answered"]]
    practice = list(dict.fromkeys(c["suggestion"] for c in answered if c["suggestion"]))[:3]
    return {"available": bool(out), "notice": FEEDBACK_NOTICE, "rubric_version": competencies()["version"], "competencies": out, "practice": practice,
            "method": "STAR-inspired reading of your own words; quotes are exact; absent evidence means not stated in the text."}


def mentions_protected(text: str) -> bool:
    """Guard used by tests: generated feedback must not contain protected-characteristic vocabulary."""
    return bool(_PROTECTED.search(text or ""))


# ------------------------------------------------------------------------------------------------ plan helpers used by the engine
def intro_item(role: Optional[str], jd_used: bool = False) -> Dict[str, Any]:
    return {"question_id": None, "domain": "Introduction", "difficulty": "", "topic": "Introduction", "question": intro_text(role), "question_type": "", "stage": I.INTRO, "origin": "intro",
            "parent_n": None, "scored": False, "provenance": {"record_id": None, "source": "standard introduction (behavioural wording)", "selected_by": "fixed first step"}}


def jd_terms(jd_text: Optional[str]) -> List[str]:
    """Competency keywords found in a (sanitised) job description: the only thing kept from it. Never the text itself."""
    low = (jd_text or "").lower()
    return sorted({k for c in competencies()["competencies"] for k in c["keywords"] if k in low})[:12]


PROJECT_COMPETENCIES = ("teamwork", "problem_solving", "failure", "conflict", "pressure", "adaptability", "leadership")


def adapt_next_behavioural(session: Dict[str, Any], i: int, n: int) -> Optional[Dict[str, Any]]:
    """Memory-driven behavioural question: if the candidate named a project earlier, the next unasked behavioural question may ask about THAT project (their words, attributed). Restrained: at most
    two per interview and never twice in a row. Returns a small report or None. Caller holds the store lock."""
    qs, ans = session["questions"], session["answers"]
    plan = session.setdefault("plan", {})
    if int(plan.get("beh_project_prompts", 0)) >= 2:
        return None
    nb = next((k for k in range(i + 1, len(qs)) if ans[k] is None and I.stage_of(qs[k]) == I.BEHAVIOURAL), None)
    if nb is None or qs[nb].get("competency") not in PROJECT_COMPETENCIES or qs[nb].get("origin") == "behavioural_memory":
        return None
    mem = M.ensure(session)
    refs = mem.get("refs", [])
    if refs and nb + 1 - refs[-1]["turn"] < 2:                                          # displayed positions
        return None
    projects = [it for it in M.active_items(mem) if it["kind"] == "project" and it["confidence"] != "low" and it.get("subject") and it["turn"] < n and it.get("referenced", 0) == 0
                and not M.looks_like_instruction(it["subject"])]
    if not projects:
        return None
    it = sorted(projects, key=lambda x: (x["confidence"] != "high", x["turn"]))[0]
    comp = competency(qs[nb]["competency"])
    text = project_prompt(comp, re.sub(r"\s+", " ", it["subject"]).strip()[:80])
    from . import policy as P
    bad = [r for r in P.verify_question(session, text, memory_ids=[it["id"]], upto=i) if r != "unsupported_memory_reference"]
    if bad:
        return None
    qs[nb] = {**qs[nb], "question": text, "origin": "behavioural_memory",
              "provenance": {**qs[nb].get("provenance", {}), "memory_ref": {"id": it["id"], "turn": it["turn"], "kind": "project", "claim_status": "candidate claim (not verified)"},
                             "selected_by": "memory-driven behavioural prompt (rubric project_prompt template)"}}
    M.mark_referenced(session, [it["id"]], nb + 1)
    plan["beh_project_prompts"] = int(plan.get("beh_project_prompts", 0)) + 1
    return {"memory_id": it["id"], "competency": qs[nb]["competency"]}

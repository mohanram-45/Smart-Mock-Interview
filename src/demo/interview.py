"""Interview planning and conversation logic for the demo. Pure functions: no I/O, no model calls, nothing here scores an answer.

What this module does (and what it deliberately does not do):
  * builds a ROLE-BASED PLAN from the curated question bank: an introduction, a fixed number of technical questions that cover distinct competencies (domain + topic) in a fixed
    Easy -> Medium -> Hard progression, and one practical exercise when the bank has one for the role
  * an optional job description only RE-RANKS candidates inside the role's own domains (keyword and concept matching against the bank). It is task data: it is never executed,
    never sent to a model and never stored; instruction-like text in it is flagged and ignored
  * retrieval scores (MiniLM / FAISS, or the BM25 fallback) only ORDER candidate questions. They are never a judgement of the candidate
  * follow-ups are deterministic and bank-backed: the prompt is built from a curated `key_concepts` entry of the question that was just asked, or is a fixed "please expand" prompt
    for a very short answer. There is NO answer-aware reasoning and NO generated text here; every item says where it came from (`origin`, `provenance`)
  * the stage order is a small explicit state machine (`TRANSITIONS`) and every planned or inserted item is checked against it
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..retrieval.lexical import tokenize

# ------------------------------------------------------------------------------------------------ constants
INTRO, CORE, FOLLOW_UP, PRACTICAL = "introduction", "core", "follow_up", "practical"
BEHAVIOURAL = "behavioural"
WRAP_UP = "wrap_up"                                    # not an item: the interview is finished and the closing message is shown
STAGE_LABELS = {INTRO: "Introduction", CORE: "Technical question", FOLLOW_UP: "Follow-up", PRACTICAL: "Practical exercise", BEHAVIOURAL: "Behavioural question", WRAP_UP: "Wrap-up"}
ORIGIN_LABELS = {"intro": "Standard introduction (not scored)",
                 "bank": "Planned question from the curated bank",
                 "follow_up": "Deterministic follow-up from the curated key concepts",
                 "llm": "Experimental follow-up written by the local model (rule-checked, not human-reviewed)",
                 "mock": "Mock follow-up (word rules, not a model)",
                 "behavioural_bank": "Original behavioural question (not scored, not human-validated)",
                 "behavioural_probe": "Behavioural follow-up from fixed, reviewable probes",
                 "memory_followup": "Follow-up that refers to something you said earlier (your own words, from this interview)",
                 "adaptive_bank": "Vetted bank question chosen by the interview policy"}

CORE_COUNT = 5                                         # technical questions in a standard interview (internal setting, not a candidate choice)
CORE_MIN, CORE_MAX = 1, 8                               # the web UI never offers a choice; the bounds only protect the API and tests
MAX_FOLLOWUPS = 2
MAX_CONSECUTIVE_SKIPS = 3                              # the interview ends politely after this many skipped questions in a row
SHORT_ANSWER_WORDS = 8
JD_MAX_CHARS = 4000
DIFFICULTIES = ("Easy", "Medium", "Hard")
PRACTICAL_TYPES = ("coding", "debugging", "sql_exercise", "scenario", "business_case")
PRACTICAL_PREF = {"Python Developer": ("coding", "debugging", "scenario"),
                  "Data Analyst": ("sql_exercise", "business_case", "scenario", "coding"),
                  "Data Scientist": ("scenario", "coding", "business_case", "debugging"),
                  "Machine Learning Engineer": ("coding", "scenario", "debugging"),
                  "NLP Engineer": ("coding", "scenario", "debugging")}
DEFAULT_PRACTICAL_PREF = ("coding", "scenario", "debugging", "business_case", "sql_exercise")

# The stage machine: which stage may directly follow which. WRAP_UP is reached when the plan is exhausted, the stop rule fires or the candidate ends the interview.
TRANSITIONS = {None: (INTRO,), INTRO: (CORE, BEHAVIOURAL), CORE: (CORE, FOLLOW_UP, PRACTICAL, BEHAVIOURAL, WRAP_UP), FOLLOW_UP: (CORE, FOLLOW_UP, PRACTICAL, BEHAVIOURAL, WRAP_UP),
               PRACTICAL: (BEHAVIOURAL, WRAP_UP), BEHAVIOURAL: (BEHAVIOURAL, FOLLOW_UP, WRAP_UP), WRAP_UP: ()}


class InputError(ValueError):
    """Bad candidate input (for example an over-long job description). The message is safe to show."""


# ------------------------------------------------------------------------------------------------ item helpers
def stage_of(q: Dict[str, Any]) -> str:
    return q.get("stage") or CORE                      # sessions saved before Stage 9B have no stage: they were plain technical questions


def is_question(q: Dict[str, Any]) -> bool:
    """A technical question (core or practical) as opposed to an introduction or a follow-up turn."""
    return stage_of(q) in (CORE, PRACTICAL)


def is_behavioural(q: Dict[str, Any]) -> bool:
    return stage_of(q) == BEHAVIOURAL


def is_scored(q: Dict[str, Any]) -> bool:
    return bool(q.get("scored", True))


def valid_transition(prev: Optional[str], nxt: str) -> bool:
    return nxt in TRANSITIONS.get(prev, ())


def check_sequence(items: Sequence[Dict[str, Any]]) -> List[str]:
    """Problems found in an item sequence (empty list = valid). Used when a plan is built and whenever a follow-up is inserted."""
    problems: List[str] = []
    prev: Optional[str] = None
    for i, q in enumerate(items):
        st = stage_of(q)
        if not valid_transition(prev, st):
            problems.append(f"item {i + 1}: {st} cannot follow {prev}")
        if st == FOLLOW_UP:
            p = q.get("parent_n")
            if not isinstance(p, int) or not 1 <= p < i + 1 or stage_of(items[p - 1]) not in (CORE, BEHAVIOURAL):
                problems.append(f"item {i + 1}: a follow-up must point to an earlier technical question")
        prev = st
    if prev is not None and not valid_transition(prev, WRAP_UP):
        problems.append(f"the interview cannot end after a {prev} item")
    return problems


# ------------------------------------------------------------------------------------------------ job description (task data, never instructions)
_INJECTION = [re.compile(p, re.I) for p in (
    r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|preceding)\s+(instructions?|prompts?|rules?|messages?)",
    r"disregard\s+(the\s+|all\s+|any\s+)?(previous|prior|above|system|earlier)",
    r"(system|developer)\s+(prompt|message|instruction)", r"you\s+are\s+(now\s+)?(an?\s+)?(ai|assistant|chatgpt|dan|language model)\b",
    r"\bact\s+as\s+(an?\s+|the\s+)", r"reveal\s+(your|the)\s+(prompt|instructions?|rules?)", r"</?\s*(system|assistant|script|instructions?)\s*>",
    r"\bjailbreak\b", r"\bpretend\s+(to\s+be|that\s+you)", r"new\s+instructions?\s*:", r"override\s+(the\s+)?(rules|instructions|scoring|score)")]
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d(?!\w)")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_jd(raw: Any) -> Optional[Dict[str, Any]]:
    """Validate and clean an optional job description. Returns None when nothing was given. Raises InputError when it is not acceptable.

    Cleaning: control characters removed, Unicode normalised, e-mail addresses / phone numbers / links replaced by a placeholder (they carry no topic information and are
    personal data), whitespace collapsed. `injection_flagged` records instruction-like text, which is ignored: the text is only ever matched against the question bank's own
    vocabulary, so nothing in it can change the interview's rules, the scoring or any prompt."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise InputError("The job description must be text.")
    s = unicodedata.normalize("NFKC", _CTRL.sub("", raw)).replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    if not s:
        return None
    if len(s) > JD_MAX_CHARS:
        raise InputError(f"The job description is too long ({len(s)} characters; the limit is {JD_MAX_CHARS}). Paste just the responsibilities and requirements.")
    letters = sum(c.isalpha() or c.isspace() or c in ".,;:-/()+#&'%" or c.isdigit() for c in s)
    if letters / len(s) < 0.7:
        raise InputError("That does not look like a job description (mostly symbols). Paste plain text.")
    redactions = len(_EMAIL.findall(s)) + len(_PHONE.findall(s)) + len(_URL.findall(s))
    s = _URL.sub(" ", _EMAIL.sub(" ", _PHONE.sub(" ", s)))
    return {"text": s, "chars": len(raw.strip()), "redactions": redactions, "injection_flagged": any(p.search(raw) for p in _INJECTION)}


def _phrase_rx(phrase: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?:s|es)?(?![a-z0-9])")


def jd_vocabulary(records: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    """Phrases of the question bank (topic names and curated key concepts) with a weight: multi-word phrases are stronger evidence than single words."""
    vocab: Dict[str, float] = {}
    for r in records:
        for ph in [r.get("topic") or ""] + [str(c) for c in (r.get("key_concepts") or [])]:
            p = re.sub(r"\s+", " ", ph.strip().lower())
            if 3 <= len(p) <= 60:
                vocab[p] = 1.0 if " " in p else 0.8
    return vocab


def jd_match(jd_text: str, records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Which bank phrases occur in the job description, and a relevance score per record. Deterministic, local, nothing is generated."""
    low = jd_text.lower()
    hit = {p: w for p, w in jd_vocabulary(records).items() if _phrase_rx(p).search(low)}
    jd_tokens = set(tokenize(jd_text))
    df: Dict[str, int] = {}
    rec_tokens: Dict[str, set] = {}
    for r in records:
        toks = set(tokenize(f"{r.get('question', '')} {r.get('topic', '')} {' '.join(map(str, r.get('key_concepts') or []))}"))
        rec_tokens[r["question_id"]] = toks
        for t in toks:
            df[t] = df.get(t, 0) + 1
    n = max(1, len(records))
    scores: Dict[str, float] = {}
    matched: Dict[str, List[str]] = {}
    for r in records:
        own = [str(c).lower().strip() for c in (r.get("key_concepts") or [])] + [(r.get("topic") or "").lower()]
        ph = [p for p in dict.fromkeys(own) if p in hit]
        overlap = sum(math.log(1 + n / df[t]) for t in rec_tokens[r["question_id"]] & jd_tokens if t in df) * 0.15
        s = sum(hit[p] for p in ph) + min(overlap, 1.5)
        if s > 0:
            scores[r["question_id"]] = s
            matched[r["question_id"]] = ph
    top = sorted(hit, key=lambda p: (-hit[p], p))
    return {"scores": scores, "matched": matched, "terms": top[:12], "n_terms": len(hit)}


# ------------------------------------------------------------------------------------------------ answer term check (evidence for feedback and for follow-ups)
def _toks(text: str) -> List[str]:
    return [t for t in tokenize(text) if len(t) > 1]


def concept_found(concept: str, answer: str, answer_tokens: Optional[set] = None) -> bool:
    """Is a curated key concept present in the answer as written? An exact-words check: 'not found' never means 'wrong', and 'found' never means 'understood'."""
    c = str(concept).strip().lower()
    if not c:
        return False
    low = (answer or "").lower()
    toks = answer_tokens if answer_tokens is not None else set(_toks(answer))
    for alt in [a.strip() for a in re.split(r"\s*/\s*|\s+or\s+", c) if a.strip()] or [c]:
        if len(alt) > 3 and alt in low:
            return True
        ct = _toks(alt)
        if not ct:
            ct = [alt]
        need = len(ct) if len(ct) <= 2 else math.ceil(len(ct) * 0.67)
        if sum(t in toks for t in ct) >= need:
            return True
    return False


_CONNECT = frozenset("vs versus and or the a an of in to for with between using use on by as at from it its".split())
_OPS = re.compile(r"==|!=|<=|>=|->|\*\*|//")
_WORD = re.compile(r"[a-z0-9_]+")


def _stem(w: str) -> str:
    w = w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w
    return w[:6]


def concept_covered_loosely(concept: str, answer: str) -> bool:
    """Does the answer already DISCUSS this curated key concept, even if it never writes the concept's exact phrase? Lenient on purpose (at least 60 % of the concept's significant words, matched by stem,
    and its code operators such as '==')  because it is only used to AVOID a redundant follow-up and to avoid calling an idea 'missing' in the feedback. A concept with
    nothing significant to match counts as covered: with no evidence either way the interview moves on. 'Covered' never means correct."""
    low = (answer or "").lower()
    have = {_stem(w) for w in _WORD.findall(low)}
    alts = [a.strip() for a in re.split(r"\s*/\s*|\s+or\s+", str(concept).lower()) if a.strip()] or [str(concept).lower()]
    for alt in alts:
        if len(alt) > 3 and alt in low:
            return True
        words = [w for w in _WORD.findall(alt) if w not in _CONNECT and (len(w) > 1 or w.isdigit())]
        ops = _OPS.findall(alt)
        total = len(words) + len(ops)
        if total == 0:
            return True
        present = sum(_stem(w) in have for w in words) + sum(o in low for o in ops)
        if present * 5 >= total * 3:
            return True
    return False


def term_check(record: Optional[Dict[str, Any]], answer: str) -> Dict[str, Any]:
    """{'found': [...], 'missing': [...]} over the record's curated key concepts. Empty lists when the record has none."""
    concepts = [str(c) for c in ((record or {}).get("key_concepts") or [])]
    toks = set(_toks(answer))
    found = [c for c in concepts if concept_found(c, answer, toks)]
    return {"found": found, "missing": [c for c in concepts if c not in found]}


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


# ------------------------------------------------------------------------------------------------ planning
def ladder(n: int) -> List[str]:
    """Fixed difficulty progression for n technical questions. NOT adaptive: it never depends on how the candidate answers."""
    if n <= 1:
        return ["Medium"]
    e = max(1, round(n * 0.2))
    h = max(1, round(n * 0.2)) if n >= 4 else 0
    return ["Easy"] * e + ["Medium"] * (n - e - h) + ["Hard"] * h


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _qtoks(r: Dict[str, Any]) -> set:
    return set(tokenize(r.get("question", "")))


def _dist(a: str, b: str) -> int:
    return abs(DIFFICULTIES.index(a) - DIFFICULTIES.index(b)) if a in DIFFICULTIES and b in DIFFICULTIES else 3


def _item(r: Dict[str, Any], stage: str, *, selected_by: str, matched: Sequence[str], retrieval_mode: str, rank: Optional[int], slot: str) -> Dict[str, Any]:
    return {"question_id": r["question_id"], "domain": r["domain"], "difficulty": r["difficulty"], "topic": r["topic"], "question": r["question"],
            "question_type": r.get("question_type") or "", "stage": stage, "origin": "bank", "parent_n": None, "scored": True,
            "provenance": {"record_id": r["question_id"], "source": "curated question bank", "slot": slot, "selected_by": selected_by, "matched_terms": list(matched)[:6],
                           "retrieval_mode": retrieval_mode, "retrieval_rank": rank}}


def plan_items(records: Sequence[Dict[str, Any]], domains: Sequence[str], role: Optional[str], *, rng, n_core: int = CORE_COUNT, jd: Optional[Dict[str, Any]] = None,
               hints: Optional[Dict[str, Tuple[float, int]]] = None, retrieval_mode: str = "none", boost_ids: Sequence[str] = (), practical_boost_ids: Sequence[str] = (),
               want_practical: bool = True) -> Dict[str, Any]:
    """Build the item list for one interview. Returns {items, notes, jd_info, pool_size}. Raises InputError when the bank cannot support an interview for these domains."""
    n_core = max(CORE_MIN, min(CORE_MAX, int(n_core)))
    dom = [d for d in dict.fromkeys(domains)]
    pool = [r for r in records if r["domain"] in set(dom)]
    if not pool:
        raise InputError("The question bank has no questions for this role.")
    hints = hints or {}
    notes: List[str] = []
    jd_scores: Dict[str, float] = {}
    jd_matched: Dict[str, List[str]] = {}
    jd_info: Optional[Dict[str, Any]] = None
    if jd:
        m = jd_match(jd["text"], pool)
        jd_scores, jd_matched = m["scores"], m["matched"]
        jd_info = {"provided": True, "chars": jd["chars"], "matched_terms": m["terms"], "text_stored": False, "redactions": jd["redactions"], "injection_flagged": jd["injection_flagged"]}
        if jd["injection_flagged"]:
            notes.append("The job description contained instruction-like text. It was ignored: job descriptions are only used to match topic keywords.")
        if not jd_scores:
            notes.append("No terms in the job description matched this role's questions, so the interview follows the role's standard coverage.")
    boost = set(boost_ids)
    # Technical questions are spoken-style questions; applied / code-writing ones are kept for the practical exercise. A thin pool relaxes that, tier by tier.
    from ..codeeval.extract import question_expects_code
    core_pool = [r for r in pool if (r.get("question_type") or "") not in PRACTICAL_TYPES and not question_expects_code(r.get("question", ""), r.get("question_type") or "")]
    if len({r["domain"] for r in core_pool}) < len(dom) or len(core_pool) < n_core * 2:
        core_pool = [r for r in pool if (r.get("question_type") or "") not in PRACTICAL_TYPES]
    if len({r["domain"] for r in core_pool}) < len(dom) or len(core_pool) < n_core * 2:
        core_pool = list(pool)
    max_jd = max(jd_scores.values()) if jd_scores else 0.0

    def relevance(r: Dict[str, Any]) -> float:
        h = hints.get(r["question_id"])
        s = (2.0 * jd_scores.get(r["question_id"], 0.0) / max_jd) if max_jd else 0.0
        s += (h[0] * (1.0 if jd_scores else 0.5)) if h else 0.0
        s += 0.3 if r.get("key_concepts") else 0.0
        s += 1.0 if r["question_id"] in boost else 0.0
        return s + rng.random() * 0.6

    chosen: List[Dict[str, Any]] = []
    used_topics: set = set()
    used_ids: set = set()
    slots = [dom[i % len(dom)] for i in range(n_core)]
    for target, d in zip(ladder(n_core), slots):
        cands = [r for r in core_pool if r["domain"] == d and r["question_id"] not in used_ids]
        if not cands:
            cands = [r for r in core_pool if r["question_id"] not in used_ids]
        if not cands:
            break
        taken = [_qtoks(c) for c in chosen]
        near = {r["question_id"]: any(_jaccard(_qtoks(r), t) >= 0.55 for t in taken) for r in cands}
        ranked = sorted(cands, key=lambda r: (near[r["question_id"]], _dist(r["difficulty"], target), (r["domain"], r["topic"]) in used_topics, -relevance(r)))
        r = ranked[0]
        used_ids.add(r["question_id"]); used_topics.add((r["domain"], r["topic"]))
        by = "role coverage" + (" + job description match" if jd_scores.get(r["question_id"]) else "")
        rk = hints.get(r["question_id"])
        chosen.append(_item(r, CORE, selected_by=by, matched=jd_matched.get(r["question_id"], []), retrieval_mode=retrieval_mode if rk else "none", rank=rk[1] if rk else None,
                            slot=f"{d} / {r['topic']} ({target} target)"))
    if len(chosen) < n_core:
        notes.append(f"The bank has only {len(chosen)} suitable technical question(s) for this role, so the interview is shorter.")
    if not chosen:
        raise InputError("The question bank has no technical questions for this role.")
    items = list(chosen)
    if want_practical:
        pref = PRACTICAL_PREF.get(role or "", DEFAULT_PRACTICAL_PREF)
        pboost = set(practical_boost_ids)
        taken = [_qtoks(r) for r in items]
        cands = [r for r in pool if (r.get("question_type") or "") in PRACTICAL_TYPES and r["question_id"] not in used_ids
                 and not any(_jaccard(_qtoks(r), t) >= 0.55 for t in taken)]
        if cands:
            def pkey(r):
                t = r.get("question_type") or ""
                return (r["question_id"] not in pboost, pref.index(t) if t in pref else len(pref), _dist(r["difficulty"], "Medium"), (r["domain"], r["topic"]) in used_topics, -relevance(r))
            r = sorted(cands, key=pkey)[0]
            rk = hints.get(r["question_id"])
            it = _item(r, PRACTICAL, selected_by="role coverage (practical exercise)" + (" + job description match" if jd_scores.get(r["question_id"]) else ""),
                       matched=jd_matched.get(r["question_id"], []), retrieval_mode=retrieval_mode if rk else "none", rank=rk[1] if rk else None,
                       slot=f"{r['domain']} / {r['topic']} ({r.get('question_type')})")
            items.append(it)
        else:
            notes.append("The bank has no practical exercise for this role, so the interview has technical questions only.")
    intro = {"question_id": None, "domain": "Introduction", "difficulty": "", "topic": "Introduction", "question": intro_question(role, bool(jd_info)), "question_type": "",
             "stage": INTRO, "origin": "intro", "parent_n": None, "scored": False, "provenance": {"record_id": None, "source": "standard introduction", "selected_by": "fixed first step"}}
    items.insert(0, intro)
    problems = check_sequence(items)
    if problems:                                                                         # a planner bug must never reach a candidate
        raise RuntimeError("invalid interview plan: " + "; ".join(problems))
    return {"items": items, "notes": notes, "jd_info": jd_info, "pool_size": len(pool)}


# ------------------------------------------------------------------------------------------------ the interviewer's words (fixed templates; they claim nothing about the answers)
def intro_question(role: Optional[str], jd_used: bool) -> str:
    if not role:
        return "To begin, could you tell me a little about yourself: your background and what draws you to this kind of work?"
    if jd_used:
        return f"To begin, could you tell me a little about yourself: your background and what draws you to the {role} role you are preparing for?"
    return f"To begin, could you tell me a little about yourself: your background and what draws you to {role} work?"


def welcome_text(role: Optional[str], domains: Sequence[str], n_core: int, has_practical: bool, interview_type: str = "technical", n_beh: int = 0) -> str:
    if interview_type == "behavioural":
        return (f"Hello, and welcome to your {role or ''} behavioural mock interview. ".replace("your  ", "your ") + f"Here is how it works: a short introduction, then about {n_beh} questions about real situations from your experience. "
                "I may ask a short follow-up to understand your own part in an example. At the end you get feedback based on your own words. Answer with concrete examples; there are no trick questions.")
    if interview_type == "mixed":
        return (f"Hello, and welcome to your {role or 'mixed'} mock interview. Here is how it works: a short introduction, {n_core} technical questions, then {n_beh} questions about your experience working with people. "
                "Now and then I may ask a short follow-up. At the end you get a feedback report. Answer in your own words; short, specific answers are fine.")
    topics = ", ".join(domains[:4]) + (" and more" if len(domains) > 4 else "")
    parts = [f"Hello, and welcome to your {role or 'technical'} mock interview.",
             f"Here is how it works: a short introduction, then {n_core} technical questions" + (f" across {topics}" if topics else "") + (", and one practical exercise" if has_practical else "") + ".",
             "Now and then I may ask a short follow-up. At the end you get a feedback report with your answers and what to practise next.",
             "Answer in your own words; short, specific answers are fine."]
    return " ".join(parts)


def wrapup_text(answered: int, asked: int, ended_early: bool = False) -> str:
    if ended_early:
        return ("We will stop here. Thank you for your time. I have saved what you answered, and you can review your answers and the feedback now. "
                "The similarity numbers are optional technical details, not a grade.")
    return ("That is everything I had planned, so we will wrap up here. Thank you for your time and for your answers. "
            "Your feedback is ready: the questions I asked, what you answered, the topics we covered and what to practise next. "
            "Similarity numbers are available as optional technical details; they are not a grade.")


_CORE_LEADS = ("Next, a question on {t}.", "Now a question about {t}.", "Let us turn to {t}.", "The next question is about {t}.", "Let us look at {t} now.")


def topic_phrase(topic: str) -> str:
    """A bank topic label ('Core language', 'NLP fundamentals') as a noun phrase inside a sentence: the first word is lower-cased unless it is an acronym or a proper name."""
    t = " ".join(str(topic or "").split()).strip(" .:")
    if not t:
        return "the next area"
    first = t.split(" ")[0]
    keep = len(first) > 1 and (first.isupper() or any(ch.isupper() for ch in first[1:]))
    return t if keep else t[0].lower() + t[1:]


def lead_in(q: Dict[str, Any], index: int, first_core: bool = False) -> str:
    """The transition sentence shown before an item. It names the topic from the bank; it never comments on the candidate's previous answer."""
    st = stage_of(q)
    if st == INTRO:
        return ""
    if st == FOLLOW_UP:
        return "Thanks. One follow-up on that."
    if st == PRACTICAL:
        return "Now for a practical exercise. Take your time."
    if st == BEHAVIOURAL:
        return q.get("lead") or ""
    t = topic_phrase(q.get("topic") or q.get("domain") or "")
    if first_core:
        return f"Thanks, that is helpful context. Now the technical part, starting with {t}."
    return _CORE_LEADS[index % len(_CORE_LEADS)].format(t=t)


# ------------------------------------------------------------------------------------------------ follow-ups
_FU_TEMPLATES = ('Could you say more about "{c}" and how it applies here?', 'How would "{c}" come into play in what you described?', 'Where does "{c}" fit into your answer?')


_EXPAND_VARIANTS = ("Could you expand on that a little? A concrete example would help.", "Could you say a bit more about that? Even a short example would help.",
                    "I would like to hear a little more. What would that look like in practice?")


def followup_item(parent_n: int, parent: Dict[str, Any], record: Optional[Dict[str, Any]], answer: str, *, used: int, limit: int = MAX_FOLLOWUPS) -> Optional[Dict[str, Any]]:
    """A deterministic, bank-backed follow-up for the answer just given, or None (carry on with the next planned question).

    * a very short answer gets the fixed prompt 'could you expand?'  (kind `expand_short`)
    * otherwise the first curated key concept of the question that the answer does not contain becomes the prompt  (kind `curated_key_concept`)
    Both are labelled as deterministic. Neither says the answer was wrong; a missing term is only a prompt to go deeper."""
    if used >= limit or stage_of(parent) != CORE or not parent.get("question_id") or not (answer or "").strip():
        return None
    base = {"question_id": parent["question_id"], "domain": parent["domain"], "difficulty": parent["difficulty"], "topic": parent["topic"], "question_type": "",
            "stage": FOLLOW_UP, "origin": "follow_up", "parent_n": parent_n, "scored": False, "scorable": None, "code_spec": None}
    if word_count(answer) < SHORT_ANSWER_WORDS:
        return {**base, "question": _EXPAND_VARIANTS[parent_n % len(_EXPAND_VARIANTS)], "followup_kind": "expand_short",
                "provenance": {"record_id": parent["question_id"], "source": "fixed prompt", "method": "deterministic: the answer had fewer than "
                               f"{SHORT_ANSWER_WORDS} words", "llm": False}}
    concepts = [str(c) for c in ((record or {}).get("key_concepts") or [])]
    # Conservative (final polish): a concept the answer already discusses in other words is not "missing", and an answer that covers most of the question's ideas gets no follow-up.
    # When relevance is uncertain the interview moves to the next planned question.
    wc = word_count(answer)
    if concepts and wc >= 25:
        share = sum(concept_covered_loosely(c, answer) for c in concepts) / len(concepts)
        if share >= (0.34 if wc >= 40 else 0.6):                    # a long answer that already touches a third of the ideas has said enough; word matching cannot see paraphrase
            return None
    missing = [c for c in term_check(record, answer)["missing"] if 1 <= len(_toks(c)) <= 5 and len(c) <= 48 and not concept_covered_loosely(c, answer)]
    if not missing:
        return None
    c = missing[0]
    return {**base, "question": _FU_TEMPLATES[parent_n % len(_FU_TEMPLATES)].format(c=c), "followup_kind": "curated_key_concept", "concept": c,
            "provenance": {"record_id": parent["question_id"], "source": "curated key_concepts field of that question", "method": "deterministic: this curated concept was not found in the answer as written",
                           "llm": False}}


def followup_allowed(items: Sequence[Dict[str, Any]], answers: Sequence[Optional[Dict[str, Any]]], parent_index: int) -> bool:
    """Spacing rule: no follow-up straight after a question that was itself followed up, and none after the practical exercise."""
    if parent_index <= 0 or stage_of(items[parent_index]) != CORE:           # behavioural probes use their own policy (behavioural.probe_for)
        return False
    return not any(stage_of(q) == FOLLOW_UP and q.get("parent_n") == parent_index for q in items) and \
        not any(stage_of(items[k]) == FOLLOW_UP for k in range(max(0, parent_index - 2), parent_index))


# ------------------------------------------------------------------------------------------------ views for the pages
def tracker(items: Sequence[Dict[str, Any]], answers: Sequence[Optional[Dict[str, Any]]], current: int, finished: bool) -> List[Dict[str, Any]]:
    """The interview stages in order with their state (done / current / upcoming), for the progress display."""
    core = [i for i, q in enumerate(items) if stage_of(q) == CORE]
    prac = [i for i, q in enumerate(items) if stage_of(q) == PRACTICAL]
    intro = [i for i, q in enumerate(items) if stage_of(q) == INTRO]
    beh = [i for i, q in enumerate(items) if stage_of(q) == BEHAVIOURAL]

    cur_stage = stage_of(items[current]) if not finished and current < len(items) else WRAP_UP
    cur_group = {INTRO: INTRO, CORE: CORE, FOLLOW_UP: CORE, PRACTICAL: PRACTICAL, BEHAVIOURAL: BEHAVIOURAL, WRAP_UP: WRAP_UP}[cur_stage]
    if cur_stage == FOLLOW_UP and current < len(items) and stage_of(items[max(0, (items[current].get("parent_n") or 1) - 1)]) == BEHAVIOURAL:
        cur_group = BEHAVIOURAL
    out = []
    for key, label, ix in ((INTRO, "Introduction", intro), (CORE, "Technical", core), (PRACTICAL, "Practical", prac), (BEHAVIOURAL, "Behavioural", beh)):
        if not ix:
            continue
        st = "done" if finished or all(i < current for i in ix) else ("current" if cur_group == key else "upcoming")
        out.append({"key": key, "label": label, "state": st, "done": sum(1 for i in ix if i < current or finished), "total": len(ix)})
    out.append({"key": WRAP_UP, "label": "Wrap-up", "state": "done" if finished else ("current" if cur_group == WRAP_UP else "upcoming"), "done": 0, "total": 0})
    return out


def coverage(items: Sequence[Dict[str, Any]], answers: Sequence[Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Topics (domain / topic) that were asked, with how many technical questions were answered, skipped or not reached. Facts only."""
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for q, a in zip(items, answers):
        if not is_question(q):
            continue
        k = (q.get("domain", ""), q.get("topic", ""))
        row = out.setdefault(k, {"domain": k[0], "topic": k[1], "asked": 0, "answered": 0, "skipped": 0, "not_reached": 0})
        row["asked"] += 1
        if a is None:
            row["not_reached"] += 1
        elif a.get("skipped"):
            row["skipped"] += 1
        else:
            row["answered"] += 1
    return list(out.values())


def progress(items: Sequence[Dict[str, Any]], answers: Sequence[Optional[Dict[str, Any]]], finished: bool) -> Dict[str, int]:
    """Progress over the PLANNED items (introduction, technical, practical). Follow-ups are extra turns and do not move the bar, so it never jumps back when one is inserted."""
    planned = [i for i, q in enumerate(items) if stage_of(q) != FOLLOW_UP]
    done = sum(1 for i in planned if answers[i] is not None) if not finished else len(planned)
    return {"done": done, "total": len(planned)}

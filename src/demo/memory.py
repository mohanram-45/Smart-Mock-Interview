"""Stage 10A: structured, evidence-grounded conversation memory for ONE interview.

What is stored: things the CANDIDATE said earlier in the same interview (projects, tools, roles, explanations, achievements, challenges, assumptions, examples) plus which topics were
discussed. Every item keeps the exact source turn and character span, the verbatim quote, who produced it (`rules` or an opt-in `model`) and a confidence with its reason.

What is NOT claimed:
  * Everything is a candidate CLAIM (`status = "candidate_claim"`, `verified = False`). Nothing here is an independently verified fact, and the interviewer must always attribute it
    ("you mentioned ...", never "your project achieved ..."). A model never writes a memory the answer's own words cannot back: a quote that is not found verbatim in the answer is dropped.
  * Mentions of a tool, project or number that the candidate did not write are never inferred.
  * Sentences that look like instructions to the interviewer are never stored.

Lifecycle: memory lives inside the session record (`session["memory"]`), so it is persisted with the session, survives a restart, is isolated per session and is deleted with the session.
Items also carry an `expires_at` (session start + retention) and expired items are ignored. There is no separate vector database: sessions hold a few dozen items, so retrieval is a small
TF-IDF cosine (or Sentence-BERT embeddings when an embedder is supplied) computed on demand.
"""
from __future__ import annotations

import math
import re
import threading
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import interview as I
from ..mlops.metrics import inc as _inc

SCHEMA_VERSION = 1
KINDS = ("project", "tool", "technology", "role", "experience", "explanation", "assumption", "example", "achievement", "challenge", "claim")
MAX_ITEMS = 60
MAX_QUOTE = 300
DEFAULT_TTL_DAYS = 14.0
BM25_MIN = 6.0                      # raw BM25 score floor for a retrieval-derived topic link (heuristic)
SEMANTIC_MIN = 0.45                 # cosine floor when Sentence-BERT is the retriever (heuristic, to be calibrated on Windows)

# ------------------------------------------------------------------------------------------------ vocabulary and patterns
TOOLS = ("PyTorch", "TensorFlow", "Keras", "scikit-learn", "sklearn", "Pandas", "NumPy", "SciPy", "Matplotlib", "Seaborn", "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Spark",
         "PySpark", "Hadoop", "Airflow", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Flask", "FastAPI", "Django", "XGBoost", "LightGBM", "CatBoost", "Tableau", "Power BI", "Excel", "Git",
         "GitHub", "Jupyter", "Hugging Face", "BERT", "GPT", "LangChain", "OpenCV", "MLflow", "DVC", "Kafka", "Terraform", "Linux", "Python", "Java", "JavaScript", "TypeScript", "React",
         "C++", "Rust", "Go", "R", "MATLAB", "NLTK", "spaCy", "FAISS", "Ollama", "Streamlit", "Pytest", "CUDA")
_TOOL_RX = [(t, re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9+#])", re.I if len(t) > 3 else 0)) for t in TOOLS]
_BUILD = r"developed|ran|conducted|performed|built|created|designed|implemented|trained|deployed|launched|wrote|made|shipped|set up|researched|analy[sz]ed|worked on|maintained|migrated|automated|optimi[sz]ed|handled|operated|supported|maintain|develop|build|design|implement|deploy|handle|operate"
_LEAD = r"led|managed|mentored|supervised|coordinated|organi[sz]ed|owned"
_PROJECT_RX = re.compile(r"\b(?:I|we)\s+(?:have\s+|had\s+|recently\s+|also\s+|previously\s+|once\s+)*(?P<verb>" + _BUILD + r")\s+(?P<obj>(?:an?\s+|the\s+|our\s+|my\s+|some\s+)?[^.,;:!?]{3,110}?)(?=\s+(?:using|with|in|for|at|to|during|which|that|because|so|and then)\b|[.,;:!?]|$)", re.I)
_PRONOUN_OBJ = frozenset("it this that them these those something things stuff everything anything one ones".split())
_USED_TO_RX = re.compile(r"\b(?:I|we)\s+(?:have\s+|had\s+|also\s+)*used\s+[A-Za-z][A-Za-z0-9+#. -]{1,30}?\s+to\s+(?P<verb>train|build|create|develop|detect|predict|classify|analy[sz]e|forecast|segment|deploy|automate|design|implement)\s+(?P<obj>(?:an?\s+|the\s+|our\s+|my\s+|some\s+)?[^.,;:!?]{3,110}?)(?=\s+(?:in|for|at|to|during|which|that|because|so|and then)\b|[.,;:!?]|$)", re.I)
_LEAD_RX = re.compile(r"\b(?:I|we)\s+(?:have\s+|had\s+|also\s+)*(?P<verb>" + _LEAD + r")\s+(?P<obj>(?:an?\s+|the\s+|our\s+|my\s+)?[^.,;:!?]{3,90}?)(?=\s+(?:using|with|in|for|at|to|during|which|that)\b|[.,;:!?]|$)", re.I)
_ROLE_RX = re.compile(r"\bI\s+(?:am|was|work(?:ed)?\s+as|have been|currently work as|used to be)\s+(?:an?\s+|the\s+)?(?P<role>[A-Za-z][A-Za-z /-]{3,60}?)(?=\s+(?:at|for|with|in|and|who)\b|[.,;:!?]|$)", re.I)
_YEARS_RX = re.compile(r"\b(?P<n>\d{1,2}(?:\.\d)?|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:\+\s*)?years?(?:\s+of)?\s+(?:experience|working|in|as)\b", re.I)
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_METRIC_RX = re.compile(r"\b(?:achieved|reached|got|obtained|improved\s+\w+\s+(?:to|by)|reduced\s+\w+\s+(?:to|by)|increased\s+\w+\s+(?:to|by)|scored|had|with|of)?\s*(?P<v>\d{1,3}(?:\.\d+)?)\s*(?P<u>%|percent|x)?\s*(?P<m>accuracy|f1|auc|roc|precision|recall|latency|throughput|error|cost|revenue|users|speed-?up)?", re.I)
_METRIC_NAMES = ("accuracy", "f1", "auc", "roc", "precision", "recall", "latency", "throughput", "error", "cost", "revenue", "users", "speedup", "speed-up")
_ACHIEVE_CUE = re.compile(r"\b(achiev|improv|reduc|increas|won|award|top|best|record|deliver|saved|boost|outperform|launched|promot)\w*|strong (?:test )?performance|good results?|\b\d{1,3}(?:\.\d+)?\s*%", re.I)
_CHALLENGE_CUE = re.compile(r"\b(challeng|struggl|hardest|toughest|obstacle|setback|went wrong|stuck|bottleneck)\w*|the (?:main |biggest |hardest )?(?:problem|issue|difficulty) (?:was|is)", re.I)
_NARRATIVE_CHALLENGE = re.compile(r"\bthe\s+(?:hardest|biggest|main|toughest|key)\s+(?:challenge|problem|issue|difficulty)\b", re.I)
_ASSUME_CUE = re.compile(r"\b(assum(?:e|ing|ed|ption)|suppose|let'?s say|given that|provided that|i would expect)\b", re.I)
_EXAMPLE_CUE = re.compile(r"\b(for example|for instance|e\.g\.|such as|in one case|one time|once,)\b", re.I)
_NEG_TOOL_RX = re.compile(r"\bI\s+(?:have\s+)?(?:never|not)\s+(?:really\s+)?(?:used|worked with|touched|tried)\s+(?P<t>[^.,;!?]{2,40})|\bI\s+(?:haven'?t|have not|hadn'?t)\s+(?:really\s+)?(?:used|worked with|touched|tried)\s+(?P<t2>[^.,;!?]{2,40})", re.I)
_FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|my|mine|we|we've|our|ours|me)\b", re.I)
_UNCERTAIN = re.compile(r"\b(i(?:'m| am) not (?:sure|certain)|i don'?t (?:know|remember|recall)|no idea|i guess|maybe|probably|not really sure|i think so|can'?t remember|not familiar)\b", re.I)
_REFUSAL = re.compile(r"^\s*(?:i\s+(?:would|'d)\s+rather\s+not|i\s+(?:do not|don'?t)\s+want\s+to\s+(?:answer|say|talk)|i\s+(?:will|'ll)\s+pass|pass\b|skip\b|no comment|i\s+refuse|i(?:'m| am)\s+not\s+comfortable\s+(?:answering|sharing|discussing))", re.I)
_STOP = frozenset("the a an and or of to in on for with at by from this that it is was are were be been i my me we our you your as but if so not no do did does have has had can could would should will just very really also about into over than then them they their there here what which who how when where why".split())


def _tokens(text: str) -> List[str]:
    toks = [t for t in re.findall(r"[a-z0-9][a-z0-9+#.-]*", (text or "").lower()) if t not in _STOP and len(t) > 1]
    out = []
    for t in toks:                                                      # light stemming: classification/classifier -> classif ; models -> model
        t = t.strip(".-")
        for suf in ("ations", "ation", "ings", "ing", "ers", "er", "ies", "es", "s", "ed"):
            if len(t) > len(suf) + 3 and t.endswith(suf):
                t = t[: -len(suf)]
                break
        out.append(t)
    return out


def looks_like_instruction(text: str) -> bool:
    return any(p.search(text or "") for p in I._INJECTION)


def uncertainty_cues(answer: str) -> List[str]:
    return [m.group(0).lower() for m in _UNCERTAIN.finditer(answer or "")][:3]


def is_refusal(answer: str) -> bool:
    return bool(_REFUSAL.search(answer or "")) and I.word_count(answer) <= 25


# ------------------------------------------------------------------------------------------------ the memory object (a plain dict, persisted inside the session)
def new_memory() -> Dict[str, Any]:
    return {"version": SCHEMA_VERSION, "items": [], "contradictions": [], "topics": [], "refs": [], "counter": 0}


def ensure(session: Dict[str, Any]) -> Dict[str, Any]:
    mem = session.get("memory")
    if not isinstance(mem, dict) or mem.get("version") != SCHEMA_VERSION:
        mem = session["memory"] = new_memory()
    return mem


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sentences(text: str) -> List[Tuple[int, int, str]]:
    out = []
    for m in re.finditer(r"[^.!?\n]+[.!?]?", text or ""):
        s, e = m.start(), m.end()
        raw = text[s:e]
        lead = len(raw) - len(raw.lstrip())
        trail = len(raw.rstrip())
        if trail - lead >= 3:
            out.append((s + lead, s + trail, text[s + lead:s + trail]))
    return out


def _confidence(sentence: str, kind: str, source: str) -> Tuple[str, str]:
    solo = re.search(r"\b(I|I've|I'd|I'm|my)\b", sentence) is not None
    plural = re.search(r"\b(we|we've|our)\b", sentence, re.I) is not None
    if source == "model":
        return "medium", "proposed by a local model; the quote was found verbatim in the answer"
    if kind in ("explanation",):
        return "medium", "the candidate's own technical explanation, summarised by position (first sentence), not by interpretation"
    if solo and not plural:
        return "high", "explicit first-person statement matching a fixed pattern"
    if plural:
        return "medium", "'we' statement: the candidate's own share of the work is not stated"
    if kind in ("challenge", "example", "assumption"):
        return "medium", "stated in the candidate's own answer without an explicit first-person subject"
    return "low", "no explicit first-person subject"


def _make(mem: Dict[str, Any], *, kind: str, text: str, quote: str, start: int, end: int, turn: int, q: Dict[str, Any], source: str = "rules", slot: Optional[str] = None,
          value: Any = None, subject: Optional[str] = None, ttl_days: float = DEFAULT_TTL_DAYS) -> Dict[str, Any]:
    conf, why = _confidence(quote, kind, source)
    mem["counter"] += 1
    created = _now()
    return {"id": f"m{mem['counter']}", "kind": kind, "text": re.sub(r"\s+", " ", text).strip()[:160], "subject": (subject or "").strip()[:100] or None, "quote": quote[:MAX_QUOTE], "turn": turn, "start": start,
            "end": end, "question_id": q.get("question_id"), "stage": I.stage_of(q), "source": source, "status": "candidate_claim", "verified": False, "confidence": conf, "confidence_reason": why,
            "slot": slot, "value": value, "mentions": [turn], "referenced": 0, "last_ref_turn": None, "conflicts_with": [], "created": created.isoformat(), "expires_at": (created + timedelta(days=ttl_days)).isoformat()}


# ------------------------------------------------------------------------------------------------ extraction (rules): evidence-grounded, deterministic
def _on_topic(answer: str, q: Dict[str, Any], record: Optional[Dict[str, Any]]) -> bool:
    """An answer is stored as an 'explanation' of the topic only if it shares at least two content words with the question, topic or curated key concepts. This is a guard against recording an
    off-topic answer as if it explained the topic; it says nothing about whether the explanation is correct."""
    base = set(_tokens(" ".join([q.get("question") or "", q.get("topic") or ""] + [str(c) for c in ((record or {}).get("key_concepts") or [])])))
    return len(set(_tokens(answer)) & base) >= 2


def extract(answer: str, *, turn: int, q: Dict[str, Any], mem: Dict[str, Any], record: Optional[Dict[str, Any]] = None, ttl_days: float = DEFAULT_TTL_DAYS) -> List[Dict[str, Any]]:
    """Candidate memory items found in ONE answer. Pure: nothing is stored. Each item's quote is `answer[start:end]` exactly."""
    out: List[Dict[str, Any]] = []
    if not answer or is_refusal(answer):
        return out
    stage = I.stage_of(q)
    for s, e, sent in _sentences(answer):
        if sent.endswith("?") or looks_like_instruction(sent):
            continue
        fp = bool(_FIRST_PERSON.search(sent))
        low = sent.lower()
        if fp:
            m = _PROJECT_RX.search(sent) or _USED_TO_RX.search(sent)
            if m and (m.group("obj").split() or [""])[0].lower() in _PRONOUN_OBJ:
                m = None                                                                    # "I worked on it with two classmates" names nothing worth remembering
            if m and len(_tokens(m.group("obj"))) >= 1:
                obj = m.group("obj").strip()
                kind = "experience" if m.group("verb").lower() in ("worked on", "maintained") and len(obj.split()) < 2 else "project"
                out.append(_make(mem, kind=kind, text=f"{m.group('verb').lower()} {obj}", subject=re.sub(r"^(?:an?|the|our|my|some)\s+", "", obj, flags=re.I), quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
            else:
                m = _LEAD_RX.search(sent)
                if m:
                    out.append(_make(mem, kind="role", text=f"{m.group('verb').lower()} {m.group('obj').strip()}", subject=m.group("obj").strip(), quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
            m = _ROLE_RX.search(sent)
            if m and 1 <= len(m.group("role").split()) <= 5 and not _UNCERTAIN.search(sent) and m.group("role").lower().split()[0] not in ("not", "very", "also", "really", "now", "still", "sure", "going", "able", "looking", "trying", "hoping", "planning", "learning", "studying", "applying", "seeking", "keen", "eager", "thinking", "wondering", "aiming", "happy", "interested", "comfortable", "good", "new"):
                out.append(_make(mem, kind="role", text=f"works/worked as {m.group('role').strip()}", subject=m.group("role").strip(), quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
            m = _YEARS_RX.search(sent)
            if m:
                n = m.group("n").lower()
                val = _NUM_WORDS.get(n) if n in _NUM_WORDS else float(n)
                out.append(_make(mem, kind="experience", text=f"{n} years of experience", quote=sent, start=s, end=e, turn=turn, q=q, slot="years_experience", value=val, ttl_days=ttl_days))
            for mt in _NEG_TOOL_RX.finditer(sent):
                tool = (mt.group("t") or mt.group("t2") or "").strip().lower()
                canon = next((t for t, rx in _TOOL_RX if rx.search(tool)), None)
                if canon:
                    out.append(_make(mem, kind="claim", text=f"has not used {canon}", subject=canon, quote=sent, start=s, end=e, turn=turn, q=q, slot=f"tool:{canon.lower()}", value=False, ttl_days=ttl_days))
            neg_tools = {t.lower() for t in [(mt.group("t") or mt.group("t2") or "").strip() for mt in _NEG_TOOL_RX.finditer(sent)]}
            for tool, rx in _TOOL_RX:
                if rx.search(sent) and not any(rx.search(n) for n in neg_tools):
                    kind = "tool" if tool in ("Git", "GitHub", "Docker", "Kubernetes", "Excel", "Jupyter", "Linux", "Tableau", "Power BI", "Terraform", "MLflow", "DVC") else "technology"
                    out.append(_make(mem, kind=kind, text=f"used {tool}", subject=tool, quote=sent, start=s, end=e, turn=turn, q=q, slot=f"tool:{tool.lower()}", value=True, ttl_days=ttl_days))
            if _ACHIEVE_CUE.search(sent):
                nums = [mm for mm in _METRIC_RX.finditer(sent) if mm.group("v") and (mm.group("u") or mm.group("m"))]
                if nums:
                    mm = nums[0]
                    metric = (mm.group("m") or "result").lower()
                    out.append(_make(mem, kind="achievement", text=f"reported {mm.group('v')}{'%' if mm.group('u') in ('%', 'percent') else ''} {metric}", quote=sent, start=s, end=e, turn=turn, q=q,
                                     ttl_days=ttl_days))                          # no slot: the same metric name can describe different projects, so metrics are never auto-flagged as contradictions
                else:
                    out.append(_make(mem, kind="achievement", text=sent[:110], quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
        if _CHALLENGE_CUE.search(sent) and I.word_count(sent) >= 4 and (fp or _NARRATIVE_CHALLENGE.search(sent)):
            out.append(_make(mem, kind="challenge", text=sent[:110], quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
        if _ASSUME_CUE.search(sent) and fp and stage in (I.CORE, I.PRACTICAL, I.FOLLOW_UP):
            out.append(_make(mem, kind="assumption", text=sent[:110], quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
        if _EXAMPLE_CUE.search(sent) and I.word_count(sent) >= 6 and fp:
            out.append(_make(mem, kind="example", text=sent[:110], quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
    if stage in (I.CORE, I.PRACTICAL) and I.word_count(answer) >= 12 and _on_topic(answer, q, record):   # the candidate's technical explanation (first substantive sentence, by position)
        sents = [x for x in _sentences(answer) if not x[2].endswith("?") and not looks_like_instruction(x[2]) and I.word_count(x[2]) >= 5]
        if sents:
            s, e, sent = sents[0]
            out.append(_make(mem, kind="explanation", text=f"{q.get('topic') or 'topic'}: {sent[:120]}", subject=q.get("topic") or None, quote=sent, start=s, end=e, turn=turn, q=q, ttl_days=ttl_days))
    seen, uniq = set(), []
    for it in out:                                                                           # one item per (kind, text) within the same answer
        k = (it["kind"], it["text"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    return uniq


# ------------------------------------------------------------------------------------------------ verification, dedupe, contradictions
def verify_item(item: Dict[str, Any], answer: str) -> bool:
    """The evidence rule: the stored span must reproduce the stored quote exactly, and the quote must be short enough to be a quote."""
    try:
        return item["kind"] in KINDS and 0 <= item["start"] < item["end"] <= len(answer) and answer[item["start"]:item["end"]] == item["quote"] and len(item["quote"]) <= MAX_QUOTE \
            and item["status"] == "candidate_claim" and item["verified"] is False
    except (KeyError, TypeError):
        return False


def _item_keys(it: Dict[str, Any]) -> set:
    return set(_tokens(" ".join(filter(None, [it.get("subject"), it["text"]]))))


def _jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _numbers_conflict(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a != b
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) > max(0.5, 0.12 * max(abs(a), abs(b)))


def add(mem: Dict[str, Any], item: Dict[str, Any]) -> str:
    """Add one item: 'added' | 'merged' (same claim restated: the original quote is kept and the turn is recorded) | 'conflict' (added, and linked to the item it conflicts with)."""
    live = mem["items"]
    for ex in live:
        if ex["kind"] != item["kind"]:
            continue
        same_slot = item.get("slot") and ex.get("slot") == item["slot"]
        if same_slot and not _numbers_conflict(ex.get("value"), item.get("value")):
            ex["mentions"] = sorted(set(ex["mentions"]) | {item["turn"]})
            return "merged"
        if not item.get("slot") and (_jacc(_item_keys(ex), _item_keys(item)) >= 0.75 or (ex.get("subject") and item.get("subject") and ex["subject"].lower() == item["subject"].lower())):
            ex["mentions"] = sorted(set(ex["mentions"]) | {item["turn"]})
            return "merged"
    status = "added"
    for ex in live:
        if item.get("slot") and ex.get("slot") == item["slot"] and _numbers_conflict(ex.get("value"), item.get("value")):
            c = {"id": f"c{len(mem['contradictions']) + 1}", "slot": item["slot"], "a": ex["id"], "b": item["id"], "kind": "negation" if isinstance(item.get("value"), bool) or isinstance(ex.get("value"), bool) else "numeric",
                 "turn": item["turn"], "resolved": False, "clarified_turn": None}
            mem["contradictions"].append(c)
            ex["conflicts_with"].append(item["id"])
            item["conflicts_with"].append(ex["id"])
            status = "conflict"
    live.append(item)
    if len(live) > MAX_ITEMS:                                                               # keep the most useful: conflicts, high confidence, recent
        live.sort(key=lambda x: (bool(x["conflicts_with"]), x["confidence"] == "high", x["turn"]), reverse=True)
        del live[MAX_ITEMS:]
        live.sort(key=lambda x: int(x["id"][1:]))
    return status


def record_topic(mem: Dict[str, Any], *, turn: int, q: Dict[str, Any], record: Optional[Dict[str, Any]], answer: str, skipped: bool = False) -> None:
    """Which topic was discussed, what the candidate wrote about it (exact-word key concepts found) and what is unresolved. 'Found' means written, not mastered."""
    if not q.get("topic") or I.stage_of(q) not in (I.CORE, I.PRACTICAL):
        return
    tc = I.term_check(record, answer) if (record and answer) else {"found": [], "missing": []}
    unresolved = []
    if skipped:
        unresolved.append("skipped")
    if uncertainty_cues(answer):
        unresolved.append("candidate expressed uncertainty")
    if answer and I.word_count(answer) < I.SHORT_ANSWER_WORDS:
        unresolved.append("very short answer")
    mem["topics"].append({"turn": turn, "domain": q.get("domain"), "topic": q.get("topic"), "question_id": q.get("question_id"), "demonstrated_terms": tc["found"][:8], "terms_not_found": tc["missing"][:8],
                          "unresolved": unresolved})


def update(session: Dict[str, Any], *, n: int, answer: str, q: Dict[str, Any], record: Optional[Dict[str, Any]] = None, extra_items: Sequence[Dict[str, Any]] = (), skipped: bool = False) -> Dict[str, Any]:
    """Update the session's memory after answer n. Returns {'added': k, 'merged': k, 'conflicts': k, 'rejected': k}. Never raises into the interview."""
    stats = {"added": 0, "merged": 0, "conflicts": 0, "rejected": 0}
    try:
        mem = ensure(session)
        ttl = float((session.get("plan") or {}).get("memory_ttl_days", DEFAULT_TTL_DAYS))
        if not skipped:
            for it in list(extract(answer, turn=n, q=q, mem=mem, record=record, ttl_days=ttl)) + list(extra_items):
                if not verify_item(it, answer):
                    stats["rejected"] += 1
                    continue
                r = add(mem, it)
                stats["added" if r == "added" else "merged" if r == "merged" else "conflicts"] += 1
        record_topic(mem, turn=n, q=q, record=record, answer=answer, skipped=skipped)
    except Exception:                                                                       # memory is an aid: a bug here must never block an interview turn
        stats["error"] = 1
    return stats


# ------------------------------------------------------------------------------------------------ retrieval + selection
class LexicalEmbedder:
    """Small TF-IDF cosine over the session's own memory texts. No model, no download. Deterministic."""
    name = "tfidf-cosine"

    def rank(self, query: str, docs: Sequence[str]) -> List[float]:
        qt = Counter(_tokens(query))
        dt = [Counter(_tokens(d)) for d in docs]
        n = len(dt) + 1
        df: Counter = Counter()
        for c in dt + [qt]:
            df.update(c.keys())
        idf = {t: math.log(1 + n / df[t]) for t in df}

        def vec(c):
            return {t: (1 + math.log(v)) * idf[t] for t, v in c.items()}
        q = vec(qt)
        qn = math.sqrt(sum(v * v for v in q.values())) or 1.0
        out = []
        for c in dt:
            d = vec(c)
            dn = math.sqrt(sum(v * v for v in d.values())) or 1.0
            out.append(sum(q.get(t, 0.0) * v for t, v in d.items()) / (qn * dn))
        return out


# ---- process-local Sentence-BERT cache (10F). Before this, every memory lookup built a NEW SbertEmbedder, i.e. re-loaded the model from disk (the repeated "Loading weights" lines on Windows were
# real reloads, not progress-bar duplication). The cache holds ONLY the read-only model: no text, no embeddings, no session data, so it cannot leak between interviews.
SBERT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_MODEL_LOCK = threading.Lock()
_MODELS: Dict[str, Any] = {}                      # model name -> loaded SentenceTransformer, or the Exception from the one failed attempt
MODEL_STATS: Dict[str, int] = {"loads": 0, "cache_hits": 0, "load_failures": 0}


def shared_sbert(model_name: str = SBERT_MODEL):
    """The process-wide SentenceTransformer for `model_name`: loaded once (under a lock), then reused. A failed load is remembered, so a missing package or uncached model is not retried on every call."""
    import os
    with _MODEL_LOCK:
        hit = _MODELS.get(model_name)
        if hit is not None:
            if isinstance(hit, BaseException):
                raise hit
            MODEL_STATS["cache_hits"] += 1
            _inc("smart_embedding_model_loads_total", component="memory", outcome="cache_hit")
            return hit
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        try:
            from sentence_transformers import SentenceTransformer                      # noqa: PLC0415
            model = SentenceTransformer(model_name)
        except Exception as e:                                                         # noqa: BLE001 - not installed, not cached, out of memory ...
            _MODELS[model_name] = e
            MODEL_STATS["load_failures"] += 1
            _inc("smart_embedding_model_loads_total", component="memory", outcome="failed")
            raise
        _MODELS[model_name] = model
        MODEL_STATS["loads"] += 1
        _inc("smart_embedding_model_loads_total", component="memory", outcome="loaded")
        return model


def reset_model_cache() -> None:
    """Tests only."""
    with _MODEL_LOCK:
        _MODELS.clear()
        for k in MODEL_STATS:
            MODEL_STATS[k] = 0


class SbertEmbedder:
    """Sentence-BERT cosine, only when the model is already cached locally (never downloads). Falls back to TF-IDF on any problem. The model itself is shared process-wide (`shared_sbert`)."""
    name = "sentence-bert"

    def __init__(self, model_name: str = SBERT_MODEL):
        self._m = shared_sbert(model_name)
        self._fallback = LexicalEmbedder()

    def rank(self, query: str, docs: Sequence[str]) -> List[float]:
        try:
            import numpy as np
            v = self._m.encode([query] + list(docs), normalize_embeddings=True, show_progress_bar=False)
            return [float(x) for x in np.dot(v[1:], v[0])]
        except Exception:
            return self._fallback.rank(query, docs)


def default_embedder():
    import os
    if os.environ.get("SMART_DEMO_MEMORY_SBERT", "").strip() in ("1", "true", "yes"):
        try:
            return SbertEmbedder()
        except Exception:
            pass
    return LexicalEmbedder()


_GENERIC_MEM = frozenset("model models data system systems project projects work team teams python learning machine analysis analytics application app code software tool tools algorithm algorithms feature features "
                         "thing things way ways problem problems result results use uses user users time process processes method methods approach technique techniques idea experience role job company "
                         "fundamentals fundamental basics basic introduction intro overview concepts concept principles principle general advanced topics topic theory practice practical applications application".split())


def specific_overlap(item: Dict[str, Any], query_tokens: set) -> set:
    """Distinctive words (not generic ones such as 'model' or 'data') that the stored statement and the query share. Prefix-matched on 6 letters so classifier/classification still meet."""
    # an explanation is about its TOPIC (its sentences carry too many ordinary words); anything else is matched on the extracted phrase AND the candidate's exact claim (10J: the extracted
    # "money transfers" lost "billing database ... concurrent transactions", the part that makes the statement relevant to a question on transactions)
    basis = [item.get("subject")] if item.get("kind") == "explanation" else [item.get("subject"), item["text"], item.get("quote")]
    mine = {t for t in _tokens(" ".join(filter(None, basis))) if t not in _GENERIC_MEM and len(t) > 3}
    qs = {t for t in query_tokens if t not in _GENERIC_MEM and len(t) > 3}
    hit = mine & qs
    for a in mine - hit:
        if len(a) >= 6 and any(len(b) >= 6 and a[:6] == b[:6] for b in qs):
            hit.add(a)
    return hit


_KIND_WEIGHT = {"project": 1.0, "achievement": 0.95, "challenge": 0.9, "explanation": 0.85, "role": 0.7, "experience": 0.7, "assumption": 0.75, "example": 0.7, "claim": 0.6, "technology": 0.7, "tool": 0.6}


def active_items(mem: Dict[str, Any], now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    now = now or _now()
    out = []
    for it in mem.get("items", []):
        try:
            if datetime.fromisoformat(it["expires_at"]) > now:
                out.append(it)
        except (KeyError, ValueError):
            continue
    return out


def link_topics(items: Sequence[Dict[str, Any]], search_fn: Optional[Callable[[str, str], Dict[str, Any]]], record_fn: Callable[[str], Optional[Dict[str, Any]]], domains: Sequence[str], top: int = 3) -> int:
    """Attach `topics` [[domain, topic], ...] to project/technology/achievement/challenge items by running the item's own words through the EXISTING question-bank retrieval (Sentence-BERT/FAISS when
    installed, BM25 otherwise). This is a retrieval-derived pointer ("this statement is about the kind of thing these bank topics cover"); it does not say the candidate knows those topics."""
    done = 0
    for it in items:
        if it.get("topics") is not None or it["kind"] not in ("project", "technology", "tool", "achievement", "challenge", "explanation", "role"):
            continue
        topics: List[List[str]] = []
        if it["kind"] == "explanation" and it.get("subject"):
            topics.append(["", it["subject"]])
        found: List[Tuple[float, str, str]] = []
        if search_fn is not None:
            q = " ".join(filter(None, [it.get("subject"), it["text"]]))[:200]
            for d in domains:
                try:
                    res = search_fn(q, d) or {}
                except Exception:
                    continue
                floor = SEMANTIC_MIN if res.get("mode") == "semantic" else BM25_MIN                 # heuristic floors (see docs/STAGE10_MODEL_AND_POLICY.md); a retrieval result always has a top-k
                for h in res.get("results") or []:
                    if isinstance(h.get("score"), (int, float)) and h["score"] >= floor:
                        rec = record_fn(h["question_id"])
                        if rec:
                            found.append((float(h["score"]), rec["domain"], rec["topic"]))
        for _, d_, t_ in sorted(found, reverse=True):
            if [d_, t_] not in topics:
                topics.append([d_, t_])
        it["topics"] = topics[:top + (1 if it["kind"] == "explanation" else 0)]
        it["topics_source"] = "retrieval-derived (not verified)"
        done += 1
    return done


def topic_match(item: Dict[str, Any], domain: Optional[str], topic: Optional[str]) -> bool:
    return any(t[1] == topic and (not t[0] or t[0] == domain) for t in (item.get("topics") or []))


def select(session: Dict[str, Any], query: Any, *, turn_now: int, k: int = 1, min_score: float = 0.2, kinds: Optional[Sequence[str]] = None, exclude_turns: Sequence[int] = (),
           embedder=None, now: Optional[datetime] = None, respect_restraint: bool = True, max_total_refs: int = 4, min_gap_turns: int = 2, target_topic: Optional[Tuple[str, str]] = None,
           diag: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """The few memory items worth mentioning NOW: relevant to `query` (the next question's text/topic), restrained (never two references in a row, a hard cap per interview, fewer re-uses of the
    same item) and never from the turn being answered. Returns [{'item', 'score', 'why'}] best first; [] is the normal, natural outcome."""
    mem = ensure(session)
    if respect_restraint:
        refs = mem.get("refs", [])
        if len(refs) >= max_total_refs or (refs and turn_now - refs[-1]["turn"] < min_gap_turns):
            if diag is not None:
                diag.append({"stage": "restraint", "blocked": "max_refs" if len(refs) >= max_total_refs else "min_gap"})
            return []
    items = [it for it in active_items(mem, now) if it["turn"] not in exclude_turns and (kinds is None or it["kind"] in kinds) and it["confidence"] != "low"]
    queries = [x for x in ([query] if isinstance(query, str) else list(query)) if (x or "").strip()]
    if not items or not queries:
        return []
    emb = embedder or default_embedder()
    docs = [" ".join(filter(None, [it.get("subject"), it["text"], it["quote"]])) for it in items]
    per_q = [emb.rank(qq, docs) for qq in queries]
    sims = [max(col) for col in zip(*per_q)]
    qtok = set(_tokens(" ".join(queries)))
    scored = []
    for it, sim in zip(items, sims):
        raw = sim                                                                  # the embedder's own similarity, before any boost: the only number that is evidence of SEMANTIC relatedness
        linked = bool(target_topic and topic_match(it, target_topic[0], target_topic[1]))
        if linked:
            sim = max(sim, 0.5)
        if specific_overlap(it, qtok):                                             # a distinctive shared word is evidence of relevance that a cosine over a long query dilutes
            sim = max(sim, 0.45)
        sc = sim * _KIND_WEIGHT.get(it["kind"], 0.6) * (0.5 ** it.get("referenced", 0)) * (1.0 if it["confidence"] == "high" else 0.9)
        if diag is not None:
            diag.append({"stage": "select", "id": it["id"], "kind": it["kind"], "turn": it["turn"], "confidence": it["confidence"], "sim_raw": round(float(raw), 3), "embedder": emb.name, "linked": linked,
                         "overlap": bool(specific_overlap(it, qtok)), "score": round(sc, 3), "min_score": min_score, "passed_min_score": sc >= min_score})
        if sc >= min_score:
            scored.append({"item": it, "score": round(sc, 3), "linked": linked, "sim_raw": round(float(raw), 3), "embedder": emb.name,
                           "why": f"{'topic-linked' if linked else 'text-similar'} to the next question ({emb.name}); {it['kind']} stated in turn {it['turn']}"})
    scored.sort(key=lambda r: (-r["score"], -r["item"]["turn"]))
    return scored[:k]


def mark_referenced(session: Dict[str, Any], item_ids: Sequence[str], turn: int) -> None:
    mem = ensure(session)
    for it in mem["items"]:
        if it["id"] in item_ids:
            it["referenced"] = it.get("referenced", 0) + 1
            it["last_ref_turn"] = turn
    mem["refs"].append({"turn": turn, "items": list(item_ids)})


def get(mem: Dict[str, Any], item_id: str) -> Optional[Dict[str, Any]]:
    return next((it for it in mem.get("items", []) if it["id"] == item_id), None)


def open_contradictions(mem: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in mem.get("contradictions", []) if not c.get("resolved") and c.get("clarified_turn") is None]


def attribution(item: Dict[str, Any]) -> str:
    """How the interviewer may phrase a memory: always as the candidate's own statement."""
    return f"you mentioned {item['subject'] or item['text']}" if item["kind"] in ("project", "role", "technology", "tool") and item.get("subject") else "you said"


def public_view(mem: Dict[str, Any]) -> Dict[str, Any]:
    """Memory for export/debug WITHOUT the candidate's quotes (counts and kinds only)."""
    items = mem.get("items", [])
    return {"version": mem.get("version"), "items": len(items), "by_kind": dict(Counter(i["kind"] for i in items)), "contradictions": len(mem.get("contradictions", [])),
            "references_used": len(mem.get("refs", [])), "topics": len(mem.get("topics", [])), "all_candidate_claims_unverified": all(not i["verified"] for i in items)}


# ------------------------------------------------------------------------------------------------ 10J: a natural, exact, attributed lead-in built ONLY from the stored claim
_LEAD_END_STOP = frozenset("a an the in of for with and to on at by or but as from into that which who".split())
_TO_SECOND_PERSON = ((r"\bI['’]m\b", "you're"), (r"\bI['’]ve\b", "you've"), (r"\bI['’]d\b", "you'd"), (r"\bI['’]ll\b", "you'll"), (r"\bmyself\b", "yourself"), (r"\bmine\b", "yours"),
                 (r"\bmy\b", "your"), (r"\bme\b", "you"), (r"\bI\b", "you"), (r"\bour\b", "your team's"), (r"\bwe\b", "your team"), (r"\bus\b", "your team"))
_CHAL_LEAD2 = re.compile(r"^(?:the|my|our)\s+(?:hardest|biggest|main|toughest|major|greatest|key|first)\s+(?:challenge|problem|issue|difficulty|obstacle)\s*(?:was|is|were)?\s*(?:that\s+)?", re.I)


def _claim_clause(quote: str, max_words: int = 16) -> str:
    first = re.split(r"(?<=[.!?])\s+", (quote or "").strip())[0].rstrip(" .!?;:,")
    words = first.split()
    if len(words) > max_words:
        words = words[:max_words]
        while words and (words[-1].lower().strip(",;:") in _LEAD_END_STOP or len(words[-1].strip(",;:")) <= 2):          # a cut must not end on 'and', 'no', 'in the' ...
            words.pop()
    return " ".join(words).rstrip(" ,;:")


def recall_lead(item: Dict[str, Any]) -> Optional[str]:
    """The sentence an interviewer can say before a question that builds on ONE stored statement: 'Earlier you said you built a search feature for a library catalogue in Python.'
    It is cut from the candidate's exact claim (never from a model), always attributed to them, and None when no safe, grammatical sentence can be made (the caller then asks a plain question).
    The words 'verified' or 'correct' never appear: a stored statement is a candidate claim."""
    quote, kind = item.get("quote") or "", item.get("kind")
    if not quote.strip() or looks_like_instruction(quote):
        return None
    if kind == "challenge":
        core = _claim_clause(_CHAL_LEAD2.sub("", _claim_clause(item.get("text") or quote, 24)).strip() or _claim_clause(quote), 16)
        return f"Earlier you described a challenge: {core}." if core else None
    if kind == "explanation":
        # 10M (M05): `subject` is the TOPIC LABEL of the bank question the explanation answered, not the candidate's words ("Linear and logistic regression" for an answer about logistic regression
        # only). "Earlier you explained <label>" is faithful only when every distinctive word of the label occurs in what the candidate actually wrote; otherwise the lead quotes their own words.
        subj = (item.get("subject") or "").strip()
        qt = {t for t in _tokens(quote)}
        st = [t for t in _tokens(subj) if t not in _GENERIC_MEM and len(t) > 3]
        if subj and st and all(any(a[:5] == b[:5] for b in qt) for a in st):
            return f"Earlier you explained {subj}."
        clause = _claim_clause(quote, 14)
        if clause and len(clause.split()) >= 4:
            return f"Earlier you said \u201c{clause}\u201d."
        return None
    clause = _claim_clause(quote)
    if not clause or len(clause.split()) < 3:
        return None
    m = re.match(r"^(I|We|My|Our)\b\s*(.*)$", clause)
    if not m:
        return None
    head, rest = m.group(1), m.group(2)
    if not rest:
        return None
    if head == "I":                                                            # agreement: "I am" -> "you are", "I was" -> "you were", "I'm" -> "you're", "I've" -> "you've"
        rest = re.sub(r"^(?:am\b)", "are", rest)
        rest = re.sub(r"^(?:was\b)", "were", rest)
        rest = re.sub(r"^['’]m\b", "are", rest)
        rest = re.sub(r"^['’]ve\b", "have", rest)
        rest = re.sub(r"^['’]ll\b", "will", rest)
        if re.match(r"^['’]d\b", rest):
            return None                                                        # "I'd" is "I would" or "I had": ambiguous, so no lead-in is made
    for pat, rep in _TO_SECOND_PERSON:
        rest = re.sub(pat, rep, rest, flags=re.I if rep != "you" else 0)
    if head in ("I",):
        return f"Earlier you said you {rest}."
    if head == "We":
        return f"Earlier you said your team {rest}."
    return f"Earlier you said your {rest}."

"""Stage 12: an evidence-checked CONTRADICTION pass over a candidate answer (not frozen; the Stage 3C-2 verifier modules are untouched).

Why it exists: the concept verifier judges one curated requirement at a time, so a false statement that is not itself one of the requirements ("an autoencoder always
needs labelled training data") is never judged at all, and an answer can satisfy every requirement while asserting something wrong. This pass asks the SAME local model,
once, a single narrow question: which of the answer's own claims does the reference material contradict?

What the code accepts (everything else is dropped, and the reason is recorded):
  * the claim id must be one of the answer's claims (the model never quotes the candidate; the code shows the claim it named);
  * `reference_quote` must occur, word for word (case and spacing ignored), in the reference prose, be at least four and at most 30 words long and stay inside ONE
    sentence (a quote that is the whole reference proves nothing about one claim);
  * the claim and the quote must share at least one content word, so the quote is about the same thing;
  * an explanation of at most 30 words that does not merely say the reference is silent ("the reference does not mention ..."): absence is not contradiction;
  * a SECOND, independent model call that sees only the claim and the quoted sentence and must answer "contradicts" (Stage 12 live evaluation: 22 Oct 2026, the first
    pass called two correct statements about a bottleneck and "no labels" contradictions because the reference did not mention them);
  * at most three findings.
An error in the second call is never read as "nothing found": the pass then reports status "error".
The reference is AI-written and fallible. A finding is "the reference says otherwise", never a verified fact; the result says so.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence

VERSION = "12.c2"
MAX_ITEMS = 3
MIN_QUOTE_WORDS = 4
MAX_WHY_WORDS = 30
MAX_REF_CHARS = 4000
MAX_QUOTE_WORDS = 30

SYSTEM = """You check a candidate's interview answer for statements that are technically WRONG according to a reference answer.
You get the QUESTION, a REFERENCE (AI-written, fallible) and the answer split into numbered CLAIMS.
Report a claim ONLY if the reference clearly says the opposite or states a fact that makes the claim false. Do not report claims that are merely incomplete, vague,
worded differently, or about something the reference does not mention. Missing information is NOT a contradiction.
For each contradiction give: claim_id, reference_quote = an EXACT quote (copied word for word) from the REFERENCE that the claim contradicts, why = at most 20 words.
If nothing is contradicted, return an empty list. Output JSON only: {"contradictions": [{"claim_id": "c1", "reference_quote": "...", "why": "..."}]}"""

CONFIRM_SYSTEM = """You compare ONE statement made by a candidate with ONE sentence from a reference answer and decide whether they cannot both be true.
Answer "contradicts" ONLY if the reference sentence directly says the opposite of the statement, or states a fact that makes the statement false.
Answer "consistent" if both can be true: the statement is worded differently, adds detail, is more specific, or is about something the sentence does not address.
Answer "unrelated" if the sentence is about something else. Sharing a word is not a contradiction. Output JSON only: {"verdict": "contradicts" | "consistent" | "unrelated"}"""
CONFIRM_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdict"], "properties": {"verdict": {"type": "string", "enum": ["contradicts", "consistent", "unrelated"]}}}
_ABSENCE = re.compile(r"\b(?:does\s*n[o']t|do\s*n[o']t|did\s*n[o']t|doesn't|don't|never|nowhere|fails?\s+to)\s+(?:explicitly\s+|directly\s+)?(?:mention|state|say|specify|include|describe|cover|contain|discuss|refer|address|list|define|name)\w*"
                      r"|\bnot\s+(?:explicitly\s+)?(?:mentioned|stated|specified|described|covered|included|discussed|addressed|defined)\b|\bno\s+(?:mention|reference)\b|\bsilent\b|\bnot\s+(?:in|part\s+of)\s+the\s+reference", re.I)
_SENTENCE_BREAK = re.compile(r"[.!?]\s+[A-Z]")

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["contradictions"],
          "properties": {"contradictions": {"type": "array", "maxItems": 5, "items": {"type": "object", "additionalProperties": False, "required": ["claim_id", "reference_quote", "why"],
                                                                                    "properties": {"claim_id": {"type": "string"}, "reference_quote": {"type": "string"}, "why": {"type": "string"}}}}}}

_CODE = re.compile(r"```.*?```", re.S)
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset("""a an the and or but of to in on at for with by from as is are was were be been being it its this that these those there their they them then than so
such can could would should may might must will do does did not no yes into over under about between through during before after if when while which who whom whose what how why
where also only just very more most less each any all some other another same own both either neither one two""".split())


def reference_prose(text: str) -> str:
    """The reference without code samples and URLs (a URL in a snippet is not the reference saying anything)."""
    return re.sub(r"\s+", " ", _URL.sub(" ", _CODE.sub(" ", text or ""))).strip()


def _norm(text: str) -> str:
    return " ".join(_WORD.findall((text or "").lower()))


def _content(text: str) -> set:
    return {w[:6] for w in _WORD.findall((text or "").lower()) if len(w) > 2 and w not in _STOP}


def build_prompt(question: str, reference: str, claims: Sequence[Dict[str, Any]]) -> str:
    lines = [f"QUESTION: {question.strip()}", "", "REFERENCE (AI-written, fallible):", reference_prose(reference)[:MAX_REF_CHARS], "", "CLAIMS:"]
    lines += [f"{c['id']}: {str(c['text']).strip()}" for c in claims]
    lines += ["", "JSON:"]
    return "\n".join(lines)


def verify(raw: Any, reference: str, claims: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply the acceptance rules above to a parsed model reply. Pure; used by `check` and by the tests."""
    by_id = {str(c["id"]): str(c["text"]) for c in claims}
    ref_norm = _norm(reference_prose(reference))
    items: List[Dict[str, Any]] = []
    rejected: List[Dict[str, str]] = []
    entries = raw.get("contradictions") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return {"status": "invalid_response", "items": [], "rejected": [{"reason": "no_contradictions_list"}]}
    for e in entries:
        if not isinstance(e, dict):
            rejected.append({"reason": "not_an_object"})
            continue
        cid, quote, why = str(e.get("claim_id") or "").strip(), str(e.get("reference_quote") or "").strip(), " ".join(str(e.get("why") or "").split())
        if cid not in by_id:
            rejected.append({"claim_id": cid, "reason": "unknown_claim"})
            continue
        qn = _norm(quote)
        if len(qn.split()) < MIN_QUOTE_WORDS or qn not in ref_norm:
            rejected.append({"claim_id": cid, "reason": "quote_not_in_reference"})
            continue
        if len(qn.split()) > MAX_QUOTE_WORDS or _SENTENCE_BREAK.search(quote):
            rejected.append({"claim_id": cid, "reason": "quote_too_broad"})
            continue
        if not (_content(by_id[cid]) & _content(quote)):
            rejected.append({"claim_id": cid, "reason": "quote_unrelated_to_claim"})
            continue
        if not why or len(why.split()) > MAX_WHY_WORDS:
            rejected.append({"claim_id": cid, "reason": "missing_or_long_explanation"})
            continue
        if _ABSENCE.search(why):
            rejected.append({"claim_id": cid, "reason": "absence_is_not_contradiction"})
            continue
        if any(i["claim_id"] == cid for i in items):
            continue
        items.append({"claim_id": cid, "claim": by_id[cid], "reference_quote": quote, "why": why})
        if len(items) >= MAX_ITEMS:
            break
    return {"status": "checked", "items": items, "rejected": rejected}


def _ask(provider: Any, system: str, prompt: str, schema: Dict[str, Any]) -> Any:
    old = getattr(provider, "response_schema", None)
    if hasattr(provider, "response_schema"):
        provider.response_schema = schema
    try:
        resp = provider.generate(system, prompt)
    finally:
        if hasattr(provider, "response_schema"):
            provider.response_schema = old
    text = getattr(resp, "text", resp)
    return json.loads(text) if isinstance(text, str) else text


def confirm(provider: Any, question: str, item: Dict[str, Any]) -> str:
    """The independent second opinion on one accepted finding: 'contradicts', 'consistent' or 'unrelated'. Raises on any failure or an unusable reply (never defaults)."""
    raw = _ask(provider, CONFIRM_SYSTEM, f"QUESTION: {question.strip()}\n\nCANDIDATE STATEMENT: {item['claim']}\n\nREFERENCE SENTENCE: {item['reference_quote']}\n\nJSON:", CONFIRM_SCHEMA)
    v = raw.get("verdict") if isinstance(raw, dict) else None
    if v not in ("contradicts", "consistent", "unrelated"):
        raise ValueError("unusable_confirmation_reply")
    return v


def check(provider: Any, question: str, reference: str, claims: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Model calls: one to find candidates, then one per accepted candidate to confirm it. Never raises: any failure is returned as status 'error' (the caller must then
    not claim the answer is free of errors)."""
    base = {"version": VERSION, "model": getattr(provider, "model", None), "note": "Contradictions are judged against an AI-written reference; not human-verified."}
    if not claims:
        return {**base, "status": "checked", "items": [], "rejected": []}
    if not reference_prose(reference):
        return {**base, "status": "error", "items": [], "rejected": [], "error": "no_reference"}
    try:
        raw = _ask(provider, SYSTEM, build_prompt(question, reference, claims), SCHEMA)
    except Exception as e:                                                   # timeout, server down, malformed JSON: no finding, and no claim that there is none
        return {**base, "status": "error", "items": [], "rejected": [], "error": f"{type(e).__name__}: {str(e)[:160]}"}
    res = verify(raw, reference, claims)
    if res.get("status") != "checked":
        return {**base, **res}
    kept, rejected = [], list(res["rejected"])
    for item in res["items"]:
        try:
            verdict = confirm(provider, question, item)
        except Exception as e:                                               # an unconfirmed finding is neither a misconception nor a clean bill of health
            return {**base, "status": "error", "items": kept, "rejected": rejected, "error": f"confirmation_failed:{type(e).__name__}: {str(e)[:120]}"}
        if verdict == "contradicts":
            kept.append({**item, "confirmed": True})
        else:
            rejected.append({"claim_id": item["claim_id"], "reason": f"second_check_{verdict}"})
    return {**base, "status": "checked", "items": kept, "rejected": rejected}


def not_checked(reason: str) -> Dict[str, Any]:
    return {"version": VERSION, "status": "not_checked", "items": [], "rejected": [], "reason": reason}

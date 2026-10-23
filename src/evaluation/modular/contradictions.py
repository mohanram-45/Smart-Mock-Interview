"""Stage 12: an evidence-checked CONTRADICTION pass over a candidate answer (not frozen; the Stage 3C-2 verifier modules are untouched).

Why it exists: the concept verifier judges one curated requirement at a time, so a false statement that is not itself one of the requirements ("an autoencoder always
needs labelled training data") is never judged at all, and an answer can satisfy every requirement while asserting something wrong. This pass asks the SAME local model,
once, a single narrow question: which of the answer's own claims does the reference material contradict?

What the code accepts (everything else is dropped, and the reason is recorded):
  * the claim id must be one of the answer's claims (the model never quotes the candidate; the code shows the claim it named);
  * `reference_quote` must occur, word for word (case and spacing ignored), in the reference prose, and be at least four words long;
  * the claim and the quote must share at least one content word, so the quote is about the same thing;
  * an explanation of at most 30 words;
  * at most three findings.
The reference is AI-written and fallible. A finding is "the reference says otherwise", never a verified fact; the result says so.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence

VERSION = "12.c1"
MAX_ITEMS = 3
MIN_QUOTE_WORDS = 4
MAX_WHY_WORDS = 30
MAX_REF_CHARS = 4000

SYSTEM = """You check a candidate's interview answer for statements that are technically WRONG according to a reference answer.
You get the QUESTION, a REFERENCE (AI-written, fallible) and the answer split into numbered CLAIMS.
Report a claim ONLY if the reference clearly says the opposite or states a fact that makes the claim false. Do not report claims that are merely incomplete, vague,
worded differently, or about something the reference does not mention. Missing information is NOT a contradiction.
For each contradiction give: claim_id, reference_quote = an EXACT quote (copied word for word) from the REFERENCE that the claim contradicts, why = at most 20 words.
If nothing is contradicted, return an empty list. Output JSON only: {"contradictions": [{"claim_id": "c1", "reference_quote": "...", "why": "..."}]}"""

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
        if not (_content(by_id[cid]) & _content(quote)):
            rejected.append({"claim_id": cid, "reason": "quote_unrelated_to_claim"})
            continue
        if not why or len(why.split()) > MAX_WHY_WORDS:
            rejected.append({"claim_id": cid, "reason": "missing_or_long_explanation"})
            continue
        if any(i["claim_id"] == cid for i in items):
            continue
        items.append({"claim_id": cid, "claim": by_id[cid], "reference_quote": quote, "why": why})
        if len(items) >= MAX_ITEMS:
            break
    return {"status": "checked", "items": items, "rejected": rejected}


def check(provider: Any, question: str, reference: str, claims: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """One model call. Never raises: any failure is returned as status 'error' (the caller must then not claim the answer is free of errors)."""
    base = {"version": VERSION, "model": getattr(provider, "model", None), "note": "Contradictions are judged against an AI-written reference; not human-verified."}
    if not claims:
        return {**base, "status": "checked", "items": [], "rejected": []}
    if not reference_prose(reference):
        return {**base, "status": "error", "items": [], "rejected": [], "error": "no_reference"}
    try:
        old = getattr(provider, "response_schema", None)
        if hasattr(provider, "response_schema"):
            provider.response_schema = SCHEMA
        try:
            resp = provider.generate(SYSTEM, build_prompt(question, reference, claims))
        finally:
            if hasattr(provider, "response_schema"):
                provider.response_schema = old
        text = getattr(resp, "text", resp)
        raw = json.loads(text) if isinstance(text, str) else text
    except Exception as e:                                                   # timeout, server down, malformed JSON: no finding, and no claim that there is none
        return {**base, "status": "error", "items": [], "rejected": [], "error": f"{type(e).__name__}: {str(e)[:160]}"}
    return {**base, **verify(raw, reference, claims)}


def not_checked(reason: str) -> Dict[str, Any]:
    return {"version": VERSION, "status": "not_checked", "items": [], "rejected": [], "reason": reason}

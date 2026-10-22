"""Stage 2C-final: candidate EMBEDDING-text formats (experiment). Only the text that is embedded changes; the full
record (canonical answer, alternatives, metadata) stays in the corpus and is returned unchanged after retrieval.

Formats (all deterministic, built from existing verified record fields, no LLM):
  qka          topic + question + key concepts + full canonical answer      (the existing Stage 2A/2B default, truncates at 256)
  question     question text only
  qk           topic + question + key concepts                              (identical to the existing ``qk`` mode)
  qk_concise   qk + the leading WHOLE sentences of the canonical answer, packed greedily to fit the model's token budget

Truncation policy for qk_concise: never rely on the encoder's silent truncation. Sentences are added only while the total
stays within ``budget`` tokens. If not even the first answer sentence fits in the remaining space, the sentence is cut at a
word boundary ONLY if >= MIN_ANSWER_TOKENS remain, and the record is flagged ``answer_cut``. If the head itself
(topic+question+concepts) exceeds the budget, the record is flagged ``head_over_budget`` (unavoidable for long scenarios;
reported, not hidden).
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List

FORMATS = ("qka", "question", "qk", "qk_concise")
SPECIAL_TOKENS = 2            # [CLS] and [SEP]
MIN_ANSWER_TOKENS = 12
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`(\"'])|\n+")


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENT.split(text or "") if s and s.strip()]


def head_text(record: Dict[str, Any]) -> str:
    return "\n".join(p for p in (record["topic"], record["question"], "Key concepts: " + "; ".join(record["key_concepts"])) if p)


def build_text(record: Dict[str, Any], fmt: str, count_tokens: Callable[[str], int] | None = None, max_seq_length: int = 256) -> Dict[str, Any]:
    """Return {'text', 'flags': {...}}. ``count_tokens(text)`` must count word-pieces WITHOUT special tokens."""
    if fmt not in FORMATS:
        raise ValueError(f"fmt must be one of {FORMATS}")
    flags = {"answer_cut": False, "head_over_budget": False, "answer_sentences": 0}
    if fmt == "question":
        return {"text": record["question"], "flags": flags}
    if fmt == "qk":
        return {"text": head_text(record), "flags": flags}
    if fmt == "qka":
        return {"text": head_text(record) + "\n" + record["canonical_answer"], "flags": flags}
    # qk_concise
    if count_tokens is None:
        raise ValueError("qk_concise needs a token counter")
    budget = max_seq_length - SPECIAL_TOKENS
    head = head_text(record)
    used = count_tokens(head)
    if used >= budget:
        flags["head_over_budget"] = True
        return {"text": head, "flags": flags}
    kept: List[str] = []
    for sent in split_sentences(record["canonical_answer"]):
        cost = count_tokens("\n" + sent) if not kept else count_tokens(" " + sent)
        if used + cost <= budget:
            kept.append(sent)
            used += cost
            continue
        if not kept and budget - used >= MIN_ANSWER_TOKENS:          # first sentence too long: cut at a word boundary, flagged
            words, cut = sent.split(), []
            for w in words:
                if count_tokens("\n" + " ".join(cut + [w])) + used - 0 > budget:
                    break
                cut.append(w)
            if cut:
                kept.append(" ".join(cut))
                flags["answer_cut"] = True
        break
    # tokenisation of the joined text can differ slightly from the sum of its parts: re-measure and trim whole sentences
    while kept and count_tokens(head + "\n" + " ".join(kept)) > budget:
        kept.pop()
        flags["answer_cut"] = flags["answer_cut"] and bool(kept)
    flags["answer_sentences"] = len(kept)
    return {"text": head + ("\n" + " ".join(kept) if kept else ""), "flags": flags}


def build_all(records: List[Dict[str, Any]], fmt: str, count_tokens=None, max_seq_length: int = 256) -> List[Dict[str, Any]]:
    return [{"doc_id": r["question_id"], **build_text(r, fmt, count_tokens, max_seq_length)} for r in records]

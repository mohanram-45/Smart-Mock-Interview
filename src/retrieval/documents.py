"""Retrieval documents: searchable text kept separate from response metadata.

Design (one index entry per knowledge record, never one per answer variant):

* ``search_text`` is what gets embedded and BM25-indexed. It is built ONLY from
  reference knowledge fields of an approved corpus record: topic, question,
  key concepts and the canonical answer. Alternative answers (concise /
  practical) are NOT embedded: they restate the canonical answer and would
  add duplicate vectors for the same question.
* ``metadata`` is the complete knowledge record returned with a hit (answers,
  alternatives, sources, verification flags, provenance). It is never embedded.
* Candidate (user) answers are not reference knowledge and have no path into
  this module: documents can only be built from corpus records whose
  provenance origin is v5 or an approved batch.

Document modes (``doc_mode``):
  ``q``    topic + question
  ``qk``   topic + question + key concepts
  ``qka``  topic + question + key concepts + canonical answer   (Stage 2A/2B default; MiniLM truncates 67.6% of these at 256 tokens)
  ``qk_concise``  qk + the leading WHOLE sentences of the canonical answer that fit the model's token budget (Stage 2C-final;
                  needs the embedder's tokenizer via ``count_tokens``; see doc_formats.py for the truncation policy)

Default rationale: queries are paraphrased questions or concept descriptions, so
the question and concepts carry the topical signal, while the canonical answer
adds domain vocabulary that makes concept-style queries retrievable. Because
the answers are long (up to ~450 words) and MiniLM truncates at 256 word
pieces, the answer text is placed last so truncation removes the least
informative tail. The ablation in the Stage 2A report measures all three modes;
the default was fixed before looking at benchmark results.
"""
from __future__ import annotations

from typing import Any, Dict, List

DOC_MODES = ("q", "qk", "qka", "qk_concise")
ALLOWED_ORIGINS = {"v5", "batch_01", "batch_02", "batch_03", "batch_04"}


def search_text(record: Dict[str, Any], doc_mode: str = "qka", count_tokens=None, max_seq_length: int = 256) -> str:
    if doc_mode not in DOC_MODES:
        raise ValueError(f"doc_mode must be one of {DOC_MODES}, got {doc_mode!r}")
    if record.get("provenance", {}).get("origin") not in ALLOWED_ORIGINS:
        raise ValueError(f"{record.get('question_id')}: not a reference-corpus record; refusing to index")
    if doc_mode == "qk_concise":
        from .doc_formats import build_text
        return build_text(record, "qk_concise", count_tokens, max_seq_length)["text"]
    parts = [record["topic"], record["question"]]
    if doc_mode in ("qk", "qka"):
        parts.append("Key concepts: " + "; ".join(record["key_concepts"]))
    if doc_mode == "qka":
        parts.append(record["canonical_answer"])
    return "\n".join(p for p in parts if p)


def build_documents(records: List[Dict[str, Any]], doc_mode: str = "qka", count_tokens=None, max_seq_length: int = 256) -> List[Dict[str, Any]]:
    """Return [{'doc_id': question_id, 'text': ..., 'metadata': record}] in record order."""
    docs = [{"doc_id": r["question_id"], "text": search_text(r, doc_mode, count_tokens, max_seq_length), "metadata": r} for r in records]
    if len({d["doc_id"] for d in docs}) != len(docs):
        raise ValueError("duplicate doc ids")
    return docs

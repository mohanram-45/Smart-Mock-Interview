"""General engineering safeguards around the experimental modular evaluator (Stage 8B). A wrapper layer: the frozen pipeline modules are NOT modified.

They exist because probing the evaluator with synthetic answers (no model, no benchmark data) showed three input-handling gaps. None is tuned to any benchmark:

  1. Hidden instructions.  The segmenter's injection detector runs per claim on raw text, so an instruction hidden with invisible characters (soft hyphen), look-alike
     letters (Cyrillic 'о' for 'o') or a line break inside the phrase was not flagged and reached the verifier as ordinary text. The structural defences (quote
     verification, evidence gates) still apply, but a numeric score for such an answer is not trustworthy, so it abstains.
  2. Truncated answers.  Segmentation keeps only the first 20,000 characters and flagged "truncated", yet the pipeline still produced a number from the part it
     read. A score for text that was not fully assessed is withheld.
  3. (separate, in src/demo/experimental.py) repeated provider failures: a circuit breaker so a dead local model server does not hold every queued answer for minutes.

What is NOT claimed: this is not a complete injection defence (letter-by-letter spacing is not detected) and says nothing about grading accuracy.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import Any, Dict, Tuple

from .claims import detect_injection
from .pipeline import ModularResult, ModularStatus

SAFEGUARD_VERSION = "8b.1"
REASON_TRUNCATED = "answer_truncated_not_fully_assessed"
REASON_HIDDEN = "possible_hidden_instruction"

# Latin look-alikes that NFKC does not fold (Cyrillic / Greek). Deliberately small: only letters that occur in the detector's phrases.
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h", "ո": "n", "ᴠ": "v",
    "ο": "o", "ν": "v", "ι": "i", "ρ": "p", "α": "a", "ε": "e", "τ": "t", "κ": "k",
})


def strip_invisible(text: str) -> Tuple[str, int]:
    """Remove zero-width / format characters (Unicode category Cf: zero-width space, soft hyphen, bidi marks, BOM). Newlines, tabs and spaces are kept, so code
    formatting is untouched. Returns (clean_text, characters_removed)."""
    out = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return out, len(text) - len(out)


def sanitise_answer(answer: str) -> Tuple[str, Dict[str, Any]]:
    clean, removed = strip_invisible(answer or "")
    return clean, {"invisible_characters_removed": removed, "safeguard_version": SAFEGUARD_VERSION}


def fold_for_detection(text: str) -> str:
    """A copy used ONLY for injection detection (never shown or graded): NFKC, invisible characters removed, look-alike letters folded, all whitespace collapsed."""
    t = unicodedata.normalize("NFKC", text or "")
    t, _ = strip_invisible(t)
    return re.sub(r"\s+", " ", t.translate(_CONFUSABLES))


def hidden_instruction_hits(answer: str) -> Tuple[str, ...]:
    return tuple(detect_injection(fold_for_detection(answer)))


def apply_safeguards(result: ModularResult, answer: str) -> ModularResult:
    """Return `result` unchanged unless a safeguard applies. A safeguard can only REMOVE a numeric score (SCORED -> ABSTAINED); it never creates or raises one."""
    flags = list(result.flags)
    reasons = list(result.abstain_reasons)
    why = []
    if "truncated" in flags:
        why.append(REASON_TRUNCATED)
    if "injection_detected" not in flags and hidden_instruction_hits(answer):
        flags.append("injection_detected_after_normalisation")
        why.append(REASON_HIDDEN)
    if not why:
        return result
    prov = dict(result.provenance)
    prov["safeguards"] = {"version": SAFEGUARD_VERSION, "applied": why}
    if result.status is ModularStatus.SCORED:
        return replace(result, status=ModularStatus.ABSTAINED, score=None, score_range=None, confidence="low", flags=tuple(flags),
                       abstain_reasons=tuple(reasons + why), provenance=prov)
    return replace(result, flags=tuple(flags), provenance=prov)
